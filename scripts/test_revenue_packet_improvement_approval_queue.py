"""
test_revenue_packet_improvement_approval_queue.py
Tests: improve command injects updated approval candidates;
       no duplicate approval IDs after improvement;
       improved candidates are still pending (not auto-approved).
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


print("=== test_revenue_packet_improvement_approval_queue ===\n")

from lib.hermes_approval_queue import _save_state, _load_state
from lib.hermes_revenue_asset_packet import (
    build_revenue_asset_packet, generate_approval_candidates,
    inject_approval_candidates, apply_internal_packet_improvements,
)
from hermes_command_router.router import run_command

# ── Reset state ───────────────────────────────────────────────────────────────
_save_state({"created_at": "2026-06-02T10:00:00+00:00", "items": [], "archived": []})

# ── Build packet, inject initial candidates ───────────────────────────────────
print("-- build and inject initial candidates --")
packet = build_revenue_asset_packet()
candidates = generate_approval_candidates(packet)
result1 = inject_approval_candidates(candidates)
initial_added = result1.get("added", 0)
check("initial candidates injected (total > 0)", result1.get("total", 0) > 0)

# ── Apply improvements and inject again → no duplicates ──────────────────────
print("\n-- apply improvements and re-inject: no duplicates --")
improved = apply_internal_packet_improvements(packet)
candidates2 = generate_approval_candidates(improved)
result2 = inject_approval_candidates(candidates2)
check("re-inject returns result", isinstance(result2, dict))
check("no duplicates added on re-inject", result2.get("added", 0) == 0)
check("re-inject skipped == initial count", result2.get("skipped", 0) == initial_added)

# ── All injected items are pending (not auto-approved) ────────────────────────
print("\n-- all improved candidates are pending --")
state = _load_state()
items = state.get("items") or []
rap_items = [i for i in items if i.get("source") == "revenue_asset_packet"]
check("revenue_asset_packet items exist in state", len(rap_items) > 0)
for item in rap_items:
    check(f"[{item['title'][:40]}] status == pending",
          item.get("status") == "pending")

# ── improve command via run_command injects candidates ────────────────────────
print("\n-- improve command updates approval queue --")
state_before = _load_state()
count_before = len([i for i in (state_before.get("items") or [])
                    if i.get("source") == "revenue_asset_packet"])

resp = run_command("improve revenue asset packet", source="cli")
check("REVENUE PACKET IMPROVED in response", "REVENUE PACKET IMPROVED" in resp)
check("no ═══ in response", "═══" not in resp)

# After improvement run, queue items should still be >= before (no deletion)
state_after = _load_state()
count_after = len([i for i in (state_after.get("items") or [])
                   if i.get("source") == "revenue_asset_packet"])
check("approval queue items >= before improvement", count_after >= count_before)

# ── No approval_ids are duplicated ────────────────────────────────────────────
print("\n-- no duplicate approval IDs in state --")
all_ids = [i.get("approval_id") for i in (state_after.get("items") or []) if i.get("approval_id")]
check("no duplicate approval IDs", len(all_ids) == len(set(all_ids)))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
