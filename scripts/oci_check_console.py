#!/usr/bin/env python3
"""Check console connection status and print correct SSH command."""
import base64, configparser, hashlib, json, os, ssl, urllib.request, urllib.error
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

def oci_get(path):
    url = f"https://iaas.{OCI_REGION}.oraclecloud.com{path}"
    hdrs = sign("GET", url, {})
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
        return json.loads(r.read())

# List console connections
print("=== Console Connection Status ===")
conns = oci_get(f"/20160918/instanceConsoleConnections?compartmentId={OCI_TENANCY}&instanceId={INST_OCID}")
active = None
for c in (conns or []):
    state = c.get("lifecycleState", "")
    cid = c.get("id", "")[:60]
    conn_str = c.get("connectionString", "")
    print(f"  {state}: {cid}...")
    if state == "ACTIVE":
        active = c

if active:
    conn_str = active.get("connectionString", "")
    print(f"\nACTIVE connection string:\n{conn_str}\n")

    # Build the correct SSH command with proper key flags
    # The ProxyCommand needs -i key and StrictHostKeyChecking=no
    # Extract the ProxyCommand part
    import re
    proxy_match = re.search(r"ProxyCommand='([^']+)'", conn_str)
    instance_ocid_match = re.search(r"' (ocid1\.instance\.[^\s]+)", conn_str)

    if proxy_match and instance_ocid_match:
        proxy_inner = proxy_match.group(1)
        inst_arg = instance_ocid_match.group(1)
        # Add key to inner ProxyCommand
        proxy_with_key = proxy_inner.replace("ssh ", "ssh -i ~/.ssh/oracle_vm -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ", 1)

        print("=" * 60)
        print("COPY THIS — run in Terminal.app:")
        print("=" * 60)
        print(f"""ssh -i ~/.ssh/oracle_vm \\
  -o StrictHostKeyChecking=no \\
  -o UserKnownHostsFile=/dev/null \\
  -o "ProxyCommand={proxy_with_key}" \\
  {inst_arg}""")
        print("=" * 60)
        print()
        print("When you see the console, press Enter a few times.")
        print("If you see 'ubuntu login:', type: ubuntu")
        print("If password needed, try Enter (blank) first.")
        print()
        print("Then run these commands:")
        print("  sudo bash -c 'echo \"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIjC7URDXY/16cJkbo5pWlOFI2AVpErLB24tI0/twdiE nexus-macmini\" >> /home/ubuntu/.ssh/authorized_keys'")
        print("  cat /home/ubuntu/.ssh/authorized_keys")
    else:
        print("Could not parse connection string.")
        print("Raw:", conn_str)
else:
    print("\nNo ACTIVE connection found. Creating new one...")
    # Would need to create a new one
    print("Run oci_console_connect.py to create a new connection.")
