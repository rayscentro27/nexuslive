#!/usr/bin/env python3
"""
OCI Run Command — execute shell commands on Oracle VM via OCI API (no SSH needed).
Uses ~/.oci/config for auth.
"""
import base64
import configparser
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
from email.utils import formatdate

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# Fix SSL for Python 3.14 on macOS
_cert = os.getenv("SSL_CERT_FILE", "/usr/local/lib/python3.14/site-packages/certifi/cacert.pem")
SSL_CTX = ssl.create_default_context(cafile=_cert) if os.path.exists(_cert) else ssl.create_default_context()

# ── Load OCI config ───────────────────────────────────────────────────────────

cfg = configparser.ConfigParser()
cfg.read(os.path.expanduser("~/.oci/config"))
p = cfg["DEFAULT"]

OCI_USER      = p["user"]
OCI_FINGERPRINT = p["fingerprint"]
OCI_TENANCY   = p["tenancy"]
OCI_REGION    = p["region"]
KEY_FILE      = os.path.expanduser(p["key_file"])

with open(KEY_FILE, "rb") as f:
    PRIVATE_KEY = serialization.load_pem_private_key(f.read(), password=None)

# ── OCI request signing ───────────────────────────────────────────────────────

def sign_request(method, url, headers, body=None):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")

    date = formatdate(usegmt=True)
    headers["date"] = date
    headers["host"] = host

    signing_parts = [
        f"(request-target): {method.lower()} {path}",
        f"date: {date}",
        f"host: {host}",
    ]

    if body is not None:
        body_bytes = body.encode() if isinstance(body, str) else body
        body_hash = base64.b64encode(hashlib.sha256(body_bytes).digest()).decode()
        headers["x-content-sha256"] = body_hash
        headers["content-length"] = str(len(body_bytes))
        headers["content-type"] = "application/json"
        signing_parts += [
            f"content-type: application/json",
            f"x-content-sha256: {body_hash}",
            f"content-length: {len(body_bytes)}",
        ]
        signing_headers = "(request-target) date host content-type x-content-sha256 content-length"
    else:
        signing_headers = "(request-target) date host"

    signing_string = "\n".join(signing_parts).encode()
    sig = PRIVATE_KEY.sign(signing_string, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.b64encode(sig).decode()

    headers["authorization"] = (
        f'Signature version="1",keyId="{OCI_TENANCY}/{OCI_USER}/{OCI_FINGERPRINT}",'
        f'algorithm="rsa-sha256",headers="{signing_headers}",signature="{sig_b64}"'
    )
    return headers

def oci_get(path):
    url = f"https://iaas.{OCI_REGION}.oraclecloud.com{path}"
    headers = {"content-type": "application/json"}
    headers = sign_request("GET", url, headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=SSL_CTX) as r:
        return json.loads(r.read())

def oci_post(endpoint_base, path, body_dict):
    url = f"https://{endpoint_base}{path}"
    body = json.dumps(body_dict)
    headers = {"content-type": "application/json"}
    headers = sign_request("POST", url, headers, body)
    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, context=SSL_CTX) as r:
        return json.loads(r.read())

def oci_get_raw(endpoint_base, path):
    url = f"https://{endpoint_base}{path}"
    headers = {"content-type": "application/json"}
    headers = sign_request("GET", url, headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=SSL_CTX) as r:
        return json.loads(r.read())

# ── Find Oracle VM instance ───────────────────────────────────────────────────

def find_instance():
    print(">> Listing compute instances...")
    data = oci_get(f"/20160918/instances?compartmentId={OCI_TENANCY}&lifecycleState=RUNNING")
    if not data:
        print("No running instances found.")
        sys.exit(1)
    for inst in data:
        name = inst.get("displayName", "")
        ocid = inst["id"]
        print(f"   Found: {name} ({ocid[:40]}...)")
    if len(data) == 1:
        return data[0]
    # Return first one (can be made interactive)
    return data[0]

# ── Run command on instance ───────────────────────────────────────────────────

PATCH_SCRIPT = r"""#!/bin/bash
set -euo pipefail

# Find the app directory
if pm2 list 2>/dev/null | grep -q nexus-oracle; then
  APP=$(pm2 list --no-color 2>/dev/null | grep "nexus-oracle" | grep -oE '/[^ ]+ ' | head -1 | tr -d ' ')
  APP=$(dirname "$APP")
else
  APP=/opt/nexus-oracle-api
fi
[ -d "$APP" ] || { echo "ERROR: App dir $APP not found"; exit 1; }
echo "App dir: $APP"
cd "$APP"

# Patch .env
sed -i.bak \
  -e 's|SUPABASE_URL=.*|SUPABASE_URL=https://ygqglfbhxiumqdisauar.supabase.co|' \
  -e 's|SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlncWdsZmJoeGl1bXFkaXNhdWFyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjE2OTE2NywiZXhwIjoyMDkxNzQ1MTY3fQ.EEv_2k8asmSZet-jYfoCzajksl3Di9DOjbQhwachnvM|' .env
grep -q PORTAL_API_KEY .env || echo 'PORTAL_API_KEY=99e1203da27086f5bfa630234a951532b6334cff0a9eeaff2cfe3463c582b66a' >> .env
echo "✓ .env patched"

# Write portal query route
mkdir -p src/routes/portal
cat > src/routes/portal/query.ts << 'TSEOF'
import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { config } from "../../config.js";
import { supabase } from "../../lib/supabase.js";

function checkPortalKey(req: FastifyRequest, reply: FastifyReply): boolean {
  if (!config.portal.enabled) { reply.status(503).send({ ok: false, error: "Portal API not configured" }); return false; }
  const provided = req.headers["x-portal-key"];
  if (!provided || provided !== config.portal.apiKey) { reply.status(401).send({ ok: false, error: "Invalid portal key" }); return false; }
  return true;
}
const INTENT_PATTERNS = [
  { intent: "grant_lookup", patterns: [/grant/i, /funding/i, /apply\s+for/i] },
  { intent: "business_ideas", patterns: [/business\s+idea/i, /opportunity/i, /side\s+hustle/i] },
  { intent: "credit_guidance", patterns: [/credit/i, /dispute/i, /repair\s+my/i] },
  { intent: "general_research", patterns: [/research/i, /explain/i, /how\s+to/i] },
];
function classifyIntent(q: string): string {
  const ql = q.toLowerCase();
  for (const { intent, patterns } of INTENT_PATTERNS) { if (patterns.some((p) => p.test(ql))) return intent; }
  return "general_research";
}
const ESCALATION = [/my\s+account/i, /my\s+credit\s+report/i, /billing/i, /refund/i, /cancel\s+my/i];
function needsEscalation(q: string) { return ESCALATION.some((p) => p.test(q)); }

export async function portalQueryRoutes(app: FastifyInstance): Promise<void> {
  app.post<{ Body: { query?: string; question?: string } }>("/", async (req, reply) => {
    if (!checkPortalKey(req, reply)) return;
    const raw = req.body?.query ?? req.body?.question ?? "";
    if (!raw) return reply.status(400).send({ ok: false, error: "query required" });
    const q = raw.slice(0, 500);
    const intent = classifyIntent(q);
    if (needsEscalation(q)) {
      return reply.send({ ok: true, intent, response_type: "escalation", response: "This relates to your account. A Nexus team member will follow up.", knowledge_used: [], escalated: true, requires_human_review: true });
    }
    let rows: Record<string, unknown>[] = [];
    try {
      if (intent === "grant_lookup") {
        const { data } = await supabase.from("grant_opportunities").select("title,description,funding_amount,deadline").eq("status","new").order("score",{ascending:false}).limit(3);
        rows = data ?? [];
      } else if (intent === "business_ideas") {
        const { data } = await supabase.from("business_opportunities").select("title,description,opportunity_type,niche").eq("status","new").order("score",{ascending:false}).limit(3);
        rows = data ?? [];
      } else {
        const { data } = await supabase.from("research_briefs").select("title,summary,topic").order("created_at",{ascending:false}).limit(5);
        rows = data ?? [];
      }
    } catch { rows = []; }
    if (!rows.length) {
      return reply.send({ ok: true, intent, response_type: "empty", response: "No specific information on this topic yet. Please check back soon or contact our team.", knowledge_used: [], escalated: false, requires_human_review: true });
    }
    const lines = rows.slice(0,3).map(r => r.funding_amount ? String(r.title)+" — "+String(r.funding_amount)+(r.deadline ? " (Deadline: "+String(r.deadline)+")" : "") : r.opportunity_type ? String(r.title)+" ("+String(r.niche ?? r.opportunity_type)+")" : String(r.title ?? r.summary ?? "Item"));
    return reply.send({ ok: true, intent, response_type: "knowledge", response: "Here's what we found:\n\n"+lines.map(l=>"• "+l).join("\n")+"\n\nFor personalized guidance, contact our team.", knowledge_used: rows.map(r=>String(r.title??"item")), escalated: false, requires_human_review: true });
  });
}
TSEOF
echo "✓ query.ts written"

# Patch app.ts if not already patched
if ! grep -q "portalQueryRoutes" src/app.ts; then
  sed -i \
    -e "s|from \"./routes/portal/strategies.js\";|from \"./routes/portal/strategies.js\";\nimport { portalQueryRoutes }    from \"./routes/portal/query.js\";|" \
    src/app.ts
  sed -i \
    '/prefix: "\/api\/portal\/strategies"/{
      n
      a\  });\n  await app.register(portalQueryRoutes, {\n    prefix: "/api/portal/query"
    }' \
    src/app.ts
  echo "✓ app.ts patched"
else
  echo "  app.ts already has portalQueryRoutes"
fi

# Restart PM2
pm2 restart nexus-oracle-api --update-env 2>/dev/null || pm2 restart all --update-env
echo "✓ PM2 restarted"
sleep 3
curl -s http://localhost:3001/healthz || echo "healthz check failed"
echo "DONE"
"""

AGENT_HOST = lambda region: f"iaas.{region}.oraclecloud.com"

def run_command_on_instance(instance_ocid, compartment_id, script):
    print(f">> Submitting run command to instance {instance_ocid[:40]}...")
    # instanceId is NOT in the create body — the agent polls per-compartment
    script_b64 = base64.b64encode(script.encode()).decode()
    body = {
        "compartmentId": compartment_id,
        "displayName": "nexus-oracle-patch",
        "executionTimeOutInSeconds": 300,
        "content": {
            "source": {
                "sourceType": "TEXT",
                "text": script_b64,
            },
            "output": {
                "outputType": "TEXT",
            },
        },
    }
    try:
        result = oci_post(
            AGENT_HOST(OCI_REGION),
            "/20180530/instanceAgentCommands",
            body,
        )
        return result
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        print(f"ERROR {e.code}: {body_err}")
        raise

def poll_command(command_ocid, instance_ocid, max_wait=240):
    print(">> Polling for completion (up to 4 min)...")
    # Execution is scoped per-instance
    path = f"/20180530/instanceAgentCommandExecutions/{command_ocid}?instanceId={instance_ocid}"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            result = oci_get_raw(AGENT_HOST(OCI_REGION), path)
            state = result.get("lifecycleState", "UNKNOWN")
            print(f"   State: {state}")
            if state in ("SUCCEEDED", "FAILED", "TIMED_OUT"):
                exec_output = result.get("content", {}).get("output", {})
                text = exec_output.get("text", "")
                if text:
                    print("\n── Command output ──────────────────────────────")
                    print(text)
                    print("────────────────────────────────────────────────\n")
                return result
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("   (waiting for agent to pick up command...)")
            else:
                print(f"   Poll error {e.code}: {e.read().decode()[:200]}")
        except Exception as e:
            print(f"   Poll error: {e}")
        time.sleep(12)
    print("Timed out waiting for command.")
    return None

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== OCI Run Command — Nexus Oracle VM Patch ===\n")
    inst = find_instance()
    inst_id = inst["id"]
    compartment_id = inst["compartmentId"]
    print(f"Target: {inst.get('displayName')} in compartment {compartment_id[:40]}...\n")

    cmd = run_command_on_instance(inst_id, compartment_id, PATCH_SCRIPT)
    cmd_id = cmd["id"]
    print(f"Command ID: {cmd_id}\n")

    result = poll_command(cmd_id, inst_id)
    if result and result.get("lifecycleState") == "SUCCEEDED":
        print("✅ Oracle VM patched successfully.")
    else:
        print("⚠️  Command did not succeed — check output above.")
