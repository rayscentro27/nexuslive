#!/usr/bin/env python3
"""
Create an OCI Instance Console Connection and SSH to it.
Console connections bypass the VM's authorized_keys — uses OCI API signing key instead.
"""
import base64, configparser, hashlib, json, os, ssl, subprocess, sys, urllib.request, urllib.error
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
PUBKEY = open(os.path.expanduser("~/.ssh/oracle_vm.pub")).read().strip()

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

def oci_post(path, body_dict):
    url = f"https://iaas.{OCI_REGION}.oraclecloud.com{path}"
    body = json.dumps(body_dict)
    hdrs = sign("POST", url, {"content-type": "application/json"}, body)
    req = urllib.request.Request(url, data=body.encode(), headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"POST error {e.code}: {e.read().decode()[:400]}")
        return None

def oci_get(path):
    url = f"https://iaas.{OCI_REGION}.oraclecloud.com{path}"
    hdrs = sign("GET", url, {"content-type": "application/json"})
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
        return json.loads(r.read())

def oci_delete(path):
    url = f"https://iaas.{OCI_REGION}.oraclecloud.com{path}"
    hdrs = sign("DELETE", url, {"content-type": "application/json"})
    req = urllib.request.Request(url, headers=hdrs, method="DELETE")
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code

print("=== OCI Instance Console Connection ===\n")

# Check for existing console connections first
print("Checking existing console connections...")
conns = oci_get(f"/20160918/instanceConsoleConnections?compartmentId={OCI_TENANCY}&instanceId={INST_OCID}")
for c in (conns or []):
    if c.get("lifecycleState") == "ACTIVE":
        print(f"Found active connection: {c['id'][:40]}...")
        print(f"SSH command: {c.get('connectionString', '')[:120]}")

# Create new console connection using our nexus_oracle public key
print("\nCreating new console connection with nexus_oracle key...")
result = oci_post("/20160918/instanceConsoleConnections", {
    "instanceId": INST_OCID,
    "publicKey": PUBKEY,
})

if not result:
    print("Failed to create console connection")
    sys.exit(1)

conn_id = result.get("id", "")
conn_str = result.get("connectionString", "")
state = result.get("lifecycleState", "")

print(f"Connection ID: {conn_id[:50]}...")
print(f"State: {state}")
print(f"\nSSH connection command:")
print(conn_str)
print()

if conn_str:
    print("Attempting to connect and run patch script...")
    print("(This opens an interactive serial console — type commands directly)")
    print()

    # The connection string is like:
    # ssh -o ProxyCommand='...' <instance-ocid>@instance-console.<region>.oci.oraclecloud.com
    # We need to use the nexus_oracle key with it

    # Extract and modify to use our key
    import shlex
    parts = shlex.split(conn_str)
    # Add our identity key
    final_cmd = ["ssh", "-i", os.path.expanduser("~/.ssh/oracle_vm"),
                 "-o", "StrictHostKeyChecking=no"] + parts[1:]

    print("Connecting (serial console — you'll see VM boot messages)...")
    print("Once logged in, run:")
    print("  sudo tee -a /home/ubuntu/.ssh/authorized_keys << 'ADDKEY'")
    print(f"  {open(os.path.expanduser('~/.ssh/nexus_oracle.pub')).read().strip()}  # nexus-macmini key")
    print("  ADDKEY")
    print()

    try:
        subprocess.run(final_cmd, timeout=120)
    except subprocess.TimeoutExpired:
        print("Connection timed out")
    except Exception as e:
        print(f"Connection failed: {e}")
        print("\nManual connection command:")
        print(conn_str.replace("ssh ", f"ssh -i ~/.ssh/nexus_oracle "))

print(f"\nTo delete this connection when done:")
print(f"  python3 -c \"import urllib.request; ...\"  # or via OCI console")
