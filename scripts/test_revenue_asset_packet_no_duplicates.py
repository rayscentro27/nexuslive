"""
test_revenue_asset_packet_no_duplicates.py
Tests: inject_approval_candidates does not create duplicate queue items.
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


print("=== test_revenue_asset_packet_no_duplicates ===\n")

from lib.hermes_revenue_asset_packet import (
    build_revenue_asset_packet, generate_approval_candidates,
    inject_approval_candidates,
)
from lib.hermes_approval_queue import _load_state, _save_state

# ── reset state to empty ──────────────────────────────────────────────────────
_save_state({"created_at": "2026-06-02T10:00:00+00:00", "items": [], "archived": []})

# ── first injection ────────────────────────────────────────────────────────────
print("-- first injection --")
packet = build_revenue_asset_packet()
candidates = generate_approval_candidates(packet)
result1 = inject_approval_candidates(candidates)

total = result1.get("total", 0)
added1 = result1.get("added", 0)
skipped1 = result1.get("skipped", 0)
check("first injection: total > 0", total > 0)
check(f"first injection: added == total ({added1}=={total})", added1 == total)
check("first injection: skipped == 0", skipped1 == 0)

# ── second injection: all skipped ────────────────────────────────────────────
print("\n-- second injection: same candidates → all skipped --")
result2 = inject_approval_candidates(candidates)
added2   = result2.get("added", 0)
skipped2 = result2.get("skipped", 0)
check("second injection: added == 0", added2 == 0)
check(f"second injection: skipped == {total}", skipped2 == total)

# ── state has no duplicate approval_ids ──────────────────────────────────────
print("\n-- state has no duplicate approval_ids --")
state = _load_state()
items = state.get("items") or []
ids = [i["approval_id"] for i in items if i.get("approval_id")]
check("no duplicate approval_ids", len(ids) == len(set(ids)))

# ── third injection from fresh packet build: still no duplicates ──────────────
print("\n-- third injection from fresh packet build: still no duplicates --")
packet2 = build_revenue_asset_packet()
candidates2 = generate_approval_candidates(packet2)
result3 = inject_approval_candidates(candidates2)
added3 = result3.get("added", 0)
check("fresh packet rebuild: same candidates not re-added", added3 == 0)

state2 = _load_state()
items2 = state2.get("items") or []
ids2 = [i["approval_id"] for i in items2 if i.get("approval_id")]
check("still no duplicate approval_ids after third injection",
      len(ids2) == len(set(ids2)))

# ── only revenue_asset_packet items in count ─────────────────────────────────
print("\n-- count revenue_packet items only --")
rap_items = [i for i in items2 if i.get("source") == "revenue_asset_packet"]
check("revenue_packet items == first added count", len(rap_items) == added1)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
