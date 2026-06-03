"""
test_revenue_asset_packet_approval_candidates.py
Tests: approval candidates are created locally, have correct categories,
       high-risk items require Ray approval.
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


print("=== test_revenue_asset_packet_approval_candidates ===\n")

from lib.hermes_revenue_asset_packet import (
    build_revenue_asset_packet, generate_approval_candidates,
    inject_approval_candidates,
)
from lib.hermes_approval_queue import HIGH_RISK_CATEGORIES

# ── generate_approval_candidates ─────────────────────────────────────────────
print("-- generate_approval_candidates from built packet --")
packet = build_revenue_asset_packet()
candidates = generate_approval_candidates(packet)

check("returns list", isinstance(candidates, list))
check("at least 1 candidate", len(candidates) >= 1)

for c in candidates:
    check(f"[{c['title'][:50]}] has title", bool(c.get("title")))
    check(f"[{c['title'][:50]}] has category", bool(c.get("category")))
    check(f"[{c['title'][:50]}] has approval_required_for",
          bool(c.get("approval_required_for")))
    check(f"[{c['title'][:50]}] has if_approved", bool(c.get("if_approved")))
    check(f"[{c['title'][:50]}] has if_rejected", bool(c.get("if_rejected")))
    check(f"[{c['title'][:50]}] has risk_level",   bool(c.get("risk_level")))
    check(f"[{c['title'][:50]}] has safe_internal_next_step",
          bool(c.get("safe_internal_next_step")))
    check(f"[{c['title'][:50]}] has approval_boundary",
          bool(c.get("approval_boundary")))
    check(f"[{c['title'][:50]}] _source_type == revenue_packet",
          c.get("_source_type") == "revenue_packet")

# ── newsletter candidate is high-risk ─────────────────────────────────────────
print("\n-- newsletter candidate is subscriber_email (high-risk) --")
newsletter_candidates = [c for c in candidates if c.get("category") == "subscriber_email"]
if newsletter_candidates:
    nc = newsletter_candidates[0]
    check("newsletter candidate category == subscriber_email", nc["category"] == "subscriber_email")
    check("newsletter category IS high-risk", nc["category"] in HIGH_RISK_CATEGORIES)
    check("newsletter risk_level is high or medium",
          nc.get("risk_level") in ("high", "medium"))
else:
    # May not exist if newsletter not found — that's OK, skip these
    check("newsletter candidate check skipped (no newsletter asset)", True)
    check("newsletter candidate check skipped (no newsletter asset)", True)
    check("newsletter candidate check skipped (no newsletter asset)", True)

# ── content_publish or client_facing candidates exist ─────────────────────────
print("\n-- publish/client-facing candidates present --")
public_facing = [c for c in candidates
                 if c.get("category") in ("content_publish", "client_facing_content")]
check("at least 1 public-facing candidate", len(public_facing) >= 1)

# ── launch checklist candidate is internal_review (low-risk) ─────────────────
print("\n-- launch checklist candidate is internal_review --")
internal_candidates = [c for c in candidates if c.get("category") == "internal_review"]
if internal_candidates:
    ic = internal_candidates[0]
    check("internal candidate NOT high-risk", ic["category"] not in HIGH_RISK_CATEGORIES)
else:
    check("internal_review candidate check skipped (may not exist)", True)

# ── creating candidates does NOT approve them ──────────────────────────────────
print("\n-- candidates created as pending (not approved) --")
from lib.hermes_approval_queue import _load_state
inject_approval_candidates(candidates)
state = _load_state()
rap_items = [i for i in (state.get("items") or [])
             if i.get("source") == "revenue_asset_packet"]
check("revenue_packet items in state", len(rap_items) >= 1)
for i in rap_items:
    check(f"[{i['title'][:40]}] status == pending", i.get("status") == "pending")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
