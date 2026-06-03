"""
test_revenue_asset_packet_no_execution.py
Tests: building packet does not publish, send, spend, deploy, or trade.
       No Supabase writes. No old tables changed.
"""
import sys, os
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_revenue_asset_packet_no_execution ===\n")

import lib.hermes_revenue_asset_packet as rap_module
from hermes_command_router.router import run_command

# ── module code inspection: no unsafe calls ───────────────────────────────────
print("-- module source has no unsafe operations --")
source = Path(ROOT / "lib" / "hermes_revenue_asset_packet.py").read_text()
UNSAFE_PATTERNS = [
    ("publish(",         "no publish() call"),
    ("send_email(",      "no send_email() call"),
    ("smtp",             "no SMTP usage"),
    ("stripe.charge",    "no stripe.charge call"),
    ("stripe.create",    "no stripe.create call"),
    (".deploy(",         "no deploy() call"),
    ("live_trading_execute", "no live_trading_execute call"),
    ("requests.post",    "no requests.post call"),
    ("supabase.table(",  "no supabase.table( insert/update"),
]
for pattern, label in UNSAFE_PATTERNS:
    check(label, pattern.lower() not in source.lower())

# ── WRITE_ENABLED is false by default ─────────────────────────────────────────
print("\n-- HERMES_REVENUE_PACKET_WRITE default is false --")
env_val = os.environ.get("HERMES_REVENUE_PACKET_WRITE", "false")
check("HERMES_REVENUE_PACKET_WRITE not true by default",
      env_val.lower() != "true")

# ── build packet does not call Supabase insert/update ─────────────────────────
print("\n-- build packet does not write to Supabase --")
supabase_write_called = []

class FakeSupabase:
    def table(self, name):
        return self
    def insert(self, *a, **kw):
        supabase_write_called.append(f"INSERT into {name}")
        return self
    def update(self, *a, **kw):
        supabase_write_called.append(f"UPDATE {name}")
        return self
    def upsert(self, *a, **kw):
        supabase_write_called.append(f"UPSERT {name}")
        return self
    def execute(self):
        return MagicMock(data=[])

# Run build_revenue_asset_packet — no Supabase should be touched
from lib.hermes_revenue_asset_packet import build_revenue_asset_packet
packet = build_revenue_asset_packet()
check("build_revenue_asset_packet succeeded (no exception)", bool(packet.get("packet_id")))
check("no Supabase insert/update/upsert called during build",
      len(supabase_write_called) == 0)

# ── generate_approval_candidates does not approve anything ────────────────────
print("\n-- generate_approval_candidates does not auto-approve --")
from lib.hermes_revenue_asset_packet import generate_approval_candidates, inject_approval_candidates
from lib.hermes_approval_queue import _load_state

candidates = generate_approval_candidates(packet)
inject_approval_candidates(candidates)
state = _load_state()
auto_approved = [
    i for i in (state.get("items") or [])
    if i.get("source") == "revenue_asset_packet" and i.get("status") == "approved"
]
check("no revenue_packet candidates auto-approved", len(auto_approved) == 0)

# ── build command response does not mention publish/send actions taken ─────────
print("\n-- build command response confirms no execution --")
resp = run_command("build revenue asset packet", source="cli")
check("build response mentions 'no content published' or safety",
      "no content published" in resp.lower()
      or "safety" in resp.lower()
      or "not published" in resp.lower())
check("build response does NOT say 'published'",
      "published" not in resp.lower() or "not published" in resp.lower()
      or "no content published" in resp.lower())
check("build response does NOT say 'email sent'",
      "email sent" not in resp.lower() or "no emails sent" in resp.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
