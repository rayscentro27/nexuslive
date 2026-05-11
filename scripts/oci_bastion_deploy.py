#!/usr/bin/env python3
"""
Deploy Oracle VM patch via OCI Bastion Managed SSH Session.
Bastion plugin is ENABLED on instance — this injects a temp key automatically.
"""
import base64, configparser, hashlib, json, os, ssl, subprocess, sys, time, urllib.request, urllib.error
from email.utils import formatdate
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

cfg = configparser.ConfigParser()
cfg.read(os.path.expanduser("~/.oci/config"))
p = cfg["DEFAULT"]
with open(os.path.expanduser(p["key_file"]), "rb") as f:
    PRIV = serialization.load_pem_private_key(f.read(), password=None)
SSL_CTX = ssl.create_default_context(cafile="/usr/local/lib/python3.14/site-packages/certifi/cacert.pem")
OCI_USER=p["user"]; OCI_FP=p["fingerprint"]; OCI_TENANCY=p["tenancy"]; OCI_REGION=p["region"]
INST_OCID = "ocid1.instance.oc1.phx.anyhqljtgei26sycw3q6j2kj3siwqxylieleq3r76eahyc3eeu5thna2hlaq"

def sign(method, url, headers, body=None):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    date = formatdate(usegmt=True)
    headers["date"] = date; headers["host"] = parsed.netloc
    path = parsed.path + ("?" + parsed.query if parsed.query else "")
    parts = [f"(request-target): {method.lower()} {path}", f"date: {date}", f"host: {parsed.netloc}"]
    sh = "(request-target) date host"
    if body is not None:
        bb = body.encode() if isinstance(body, str) else body
        bh = base64.b64encode(hashlib.sha256(bb).digest()).decode()
        headers.update({"x-content-sha256": bh, "content-length": str(len(bb)), "content-type": "application/json"})
        parts += [f"content-type: application/json", f"x-content-sha256: {bh}", f"content-length: {len(bb)}"]
        sh = "(request-target) date host content-type x-content-sha256 content-length"
    ss = "\n".join(parts).encode()
    sig = base64.b64encode(PRIV.sign(ss, padding.PKCS1v15(), hashes.SHA256())).decode()
    headers["authorization"] = f'Signature version="1",keyId="{OCI_TENANCY}/{OCI_USER}/{OCI_FP}",algorithm="rsa-sha256",headers="{sh}",signature="{sig}"'
    return headers

def oci_req(method, url, body_dict=None):
    body = json.dumps(body_dict) if body_dict else None
    hdrs = sign(method, url, {}, body)
    req = urllib.request.Request(url, data=body.encode() if body else None, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:400]}")
        return None

BASE = f"https://bastion.{OCI_REGION}.oci.oraclecloud.com"

print("=== OCI Bastion Deploy ===\n")

# Step 1: Get instance private IP (needed for Managed SSH session)
print("1. Getting instance private IP...")
iaas_base = f"https://iaas.{OCI_REGION}.oraclecloud.com"
vnic_attachments = oci_req("GET", f"{iaas_base}/20160918/vnicAttachments?compartmentId={OCI_TENANCY}&instanceId={INST_OCID}")
private_ip = None
for va in (vnic_attachments or []):
    vnic_id = va.get("vnicId")
    if vnic_id:
        vnic = oci_req("GET", f"{iaas_base}/20160918/vnics/{vnic_id}")
        private_ip = vnic.get("privateIp")
        public_ip = vnic.get("publicIp", "none")
        print(f"   Private IP: {private_ip}, Public IP: {public_ip}")
        break

if not private_ip:
    print("   FAILED: Could not get private IP")
    sys.exit(1)

# Step 2: Check for existing Bastions
print("\n2. Checking for existing Bastions...")
bastions = oci_req("GET", f"{BASE}/20210331/bastions?compartmentId={OCI_TENANCY}")
bastion_id = None
if bastions:
    for b in bastions:
        state = b.get("lifecycleState")
        bname = b.get("name", "")
        bid = b.get("id", "")
        print(f"   Found: {bname} [{state}] {bid[:40]}...")
        if state == "ACTIVE":
            bastion_id = bid
            print(f"   Using ACTIVE bastion: {bname}")
            break

# Step 3: Create Bastion if none exists
if not bastion_id:
    print("\n3. Creating new Bastion...")
    # Need a subnet OCID — get it from the VNIC attachment
    subnet_id = None
    for va in (vnic_attachments or []):
        # The VNIC attachment has subnet info indirectly via vnic
        pass

    # Get subnet from vnic
    vnic_data = oci_req("GET", f"{iaas_base}/20160918/vnics/{vnic_attachments[0]['vnicId']}")
    subnet_id = vnic_data.get("subnetId") if vnic_data else None

    if not subnet_id:
        print("   FAILED: Could not get subnet ID")
        sys.exit(1)

    print(f"   Subnet: {subnet_id[:50]}...")
    new_bastion = oci_req("POST", f"{BASE}/20210331/bastions", {
        "compartmentId": OCI_TENANCY,
        "bastionType": "STANDARD",
        "name": "nexus-bastion",
        "targetSubnetId": subnet_id,
        "clientCidrBlockAllowList": ["0.0.0.0/0"],
    })
    if not new_bastion:
        print("   FAILED: Could not create bastion")
        sys.exit(1)
    bastion_id = new_bastion.get("id")
    print(f"   Bastion creating: {bastion_id[:50]}...")
    print("   Waiting for ACTIVE state (this takes ~5 minutes)...")
    for _ in range(30):
        time.sleep(15)
        b = oci_req("GET", f"{BASE}/20210331/bastions/{bastion_id}")
        state = b.get("lifecycleState") if b else "UNKNOWN"
        print(f"   State: {state}")
        if state == "ACTIVE":
            break
    else:
        print("   Timed out waiting for Bastion")
        sys.exit(1)
else:
    print("   Found existing active Bastion")

# Step 4: Create Managed SSH Session
print("\n4. Creating Managed SSH Session...")
pub_key = open(os.path.expanduser("~/.ssh/nexus_oracle.pub")).read().strip()
print(f"   Using key: {pub_key[:60]}...")

session_result = oci_req("POST", f"{BASE}/20210331/sessions", {
    "bastionId": bastion_id,
    "displayName": "nexus-deploy",
    "sessionTtlInSeconds": 3600,
    "targetResourceDetails": {
        "sessionType": "MANAGED_SSH",
        "targetResourceId": INST_OCID,
        "targetResourceOperatingSystemUserName": "ubuntu",
        "targetResourcePort": 22,
        "targetResourcePrivateIpAddress": private_ip,
    },
    "keyDetails": {
        "publicKeyContent": pub_key
    }
})

if not session_result:
    print("   FAILED to create session")
    sys.exit(1)

session_id = session_result.get("id", "")
print(f"   Session ID: {session_id[:50]}...")
print(f"   State: {session_result.get('lifecycleState')}")

# Step 5: Wait for session to become ACTIVE
print("\n5. Waiting for session to become ACTIVE...")
for i in range(20):
    time.sleep(10)
    sess = oci_req("GET", f"{BASE}/20210331/sessions/{session_id}")
    state = sess.get("lifecycleState") if sess else "UNKNOWN"
    print(f"   [{i+1}] State: {state}")
    if state == "ACTIVE":
        ssh_cmd = sess.get("sshMetadata", {}).get("command", "") or sess.get("bastionPublicHostKeyFingerprint", "")
        # Try to get the SSH connection details
        conn_details = sess.get("sshMetadata") or {}
        print(f"\n   SSH metadata: {json.dumps(conn_details, indent=4)}")
        print(f"\n   Full session: {json.dumps(sess, indent=2)}")
        break
    elif state in ["FAILED", "DELETED"]:
        print(f"   Session {state}")
        sys.exit(1)
else:
    print("   Timed out waiting for session")
    sys.exit(1)
