#!/usr/bin/env python3
"""Add Mac Mini SSH public key to Oracle VM authorized_keys via OCI API."""
import base64, configparser, hashlib, json, os, ssl, urllib.request, urllib.error
from email.utils import formatdate
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

cfg = configparser.ConfigParser()
cfg.read(os.path.expanduser("~/.oci/config"))
p = cfg["DEFAULT"]
KEY_FILE = os.path.expanduser(p["key_file"])
with open(KEY_FILE, "rb") as f:
    PRIV = serialization.load_pem_private_key(f.read(), password=None)
_cert = "/usr/local/lib/python3.14/site-packages/certifi/cacert.pem"
SSL_CTX = ssl.create_default_context(cafile=_cert)
OCI_USER=p["user"]; OCI_FP=p["fingerprint"]; OCI_TENANCY=p["tenancy"]; OCI_REGION=p["region"]

PUBKEY = open(os.path.expanduser("~/.ssh/nexus_oracle.pub")).read().strip()
INST_OCID = "ocid1.instance.oc1.phx.anyhqljtgei26sycw4jjzr3hh3fzxogtvh2fwzq4fxiuyhqriqukbvqbxqeq"

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

print("=== Add SSH Key to Oracle VM ===")
print(f"Public key: {PUBKEY[:60]}...")

# GET current instance
url_get = f"https://iaas.{OCI_REGION}.oraclecloud.com/20160918/instances/{INST_OCID}"
hdrs = sign("GET", url_get, {"content-type": "application/json"})
req = urllib.request.Request(url_get, headers=hdrs)
print("Getting instance info...")
with urllib.request.urlopen(req, context=SSL_CTX) as r:
    inst = json.loads(r.read())

print(f"Instance: {inst.get('displayName')} [{inst.get('lifecycleState')}]")
meta = inst.get("metadata", {})
current_keys = meta.get("ssh_authorized_keys", "")
print(f"Current keys: {len(current_keys.splitlines())} key(s)")

if PUBKEY in current_keys:
    print("✓ Key already present — no update needed")
else:
    new_keys = (current_keys.rstrip() + "\n" + PUBKEY).strip()
    meta["ssh_authorized_keys"] = new_keys
    body = json.dumps({"metadata": meta})
    url_put = f"https://iaas.{OCI_REGION}.oraclecloud.com/20160918/instances/{INST_OCID}"
    hdrs2 = sign("PUT", url_put, {"content-type": "application/json"}, body)
    req2 = urllib.request.Request(url_put, data=body.encode(), headers=hdrs2, method="PUT")
    print("Updating metadata...")
    try:
        with urllib.request.urlopen(req2, context=SSL_CTX) as r2:
            result = json.loads(r2.read())
            print(f"✓ Metadata updated — state: {result.get('lifecycleState')}")
    except urllib.error.HTTPError as e:
        print(f"PUT error {e.code}: {e.read().decode()[:400]}")

print("\nNOTE: OCI metadata update only works for cloud-init; run-command-based injection needed.")
print("Trying direct SSH now (may fail if key not yet propagated)...")
