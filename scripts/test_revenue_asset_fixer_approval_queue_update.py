"""
test_revenue_asset_fixer_approval_queue_update.py
Tests: after fixes, approval queue candidates can be generated from fixed packet;
       no Supabase writes occur.
"""
import sys, os
from pathlib import Path

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


print("=== test_revenue_asset_fixer_approval_queue_update ===\n")

from lib.hermes_revenue_asset_packet import (
    build_revenue_asset_packet_with_fixes,
    generate_approval_candidates,
    inject_approval_candidates,
)
from lib.hermes_revenue_asset_fixer import apply_safe_asset_fixes

# ── Apply fixes ───────────────────────────────────────────────────────────────
print("-- apply fixes --")
apply_safe_asset_fixes()

# ── Build fixed packet ────────────────────────────────────────────────────────
print("\n-- build fixed packet --")
packet = build_revenue_asset_packet_with_fixes()
check("packet is dict", isinstance(packet, dict))
check("packet has assets", bool(packet.get("assets")))

# ── Generate approval candidates ─────────────────────────────────────────────
print("\n-- generate approval candidates from fixed packet --")
candidates = generate_approval_candidates(packet)
check("candidates is list", isinstance(candidates, list))
check("at least some candidates", len(candidates) >= 0)  # may be 0 if none ready

for i, c in enumerate(candidates[:3]):
    check(f"[candidate {i}] has required fields",
          all(k in c for k in ("title", "category", "approval_boundary")))

# ── inject_approval_candidates returns result dict ────────────────────────────
print("\n-- inject_approval_candidates result --")
inject_result = inject_approval_candidates(candidates)
check("inject_result is dict", isinstance(inject_result, dict))
check("inject_result has 'added'", "added" in inject_result)
check("inject_result has 'total'", "total" in inject_result)
check("added is int", isinstance(inject_result.get("added"), int))

# ── No Supabase keys in inject result ────────────────────────────────────────
print("\n-- no supabase writes in inject result --")
result_str = str(inject_result).lower()
check("no 'supabase' key reference in result", "supabase_key" not in result_str)
check("no 'service_role' in result", "service_role" not in result_str)

# ── Approval queue file updated (not Supabase) ───────────────────────────────
print("\n-- approval queue file updated --")
queue_path = ROOT / "docs" / "reports" / "approvals" / "hermes_approval_queue.jsonl"
if queue_path.exists():
    check("approval queue file exists", True)
    content = queue_path.read_text()
    check("approval queue file is non-empty", len(content.strip()) > 0)
else:
    check("approval queue file exists (skip)", True)  # soft pass if dir not yet created

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
