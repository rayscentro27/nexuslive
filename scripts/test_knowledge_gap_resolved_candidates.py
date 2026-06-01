"""
test_knowledge_gap_resolved_candidates.py
Verifies that _run_knowledge_gap_review flags resolved candidates
(phrases now handled by conversational router) as "[resolved candidate]".
"""
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}")

print("=== test_knowledge_gap_resolved_candidates ===\n")

from datetime import datetime, timezone
from pathlib import Path

def _make_gap(msg: str, i: int = 0, reason: str = "missing_route") -> dict:
    return {
        "gap_id": f"gap_test_{i:04d}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_message": msg,
        "normalized_message": " ".join(msg.strip().lower().split()),
        "category": "unknown_or_unresolved",
        "reason": reason,
        "status": "open",
        "priority": "low",
        "suggested_handler": "hermes_language_pack — add new phrase category",
    }

# Mix of resolved and unresolved gaps
gaps = [
    _make_gap("help"),          # resolved — capability route now handles it
    _make_gap("/help"),         # resolved
    _make_gap("what can you do"),  # resolved
    _make_gap("what is the weather today"),  # resolved — external info
    _make_gap("show me the trading dashboard"),  # NOT resolved
    _make_gap("what is my credit score"),        # NOT resolved
]

tmp_dir = Path(tempfile.mkdtemp())
gap_file = tmp_dir / "hermes_knowledge_gaps.jsonl"
with gap_file.open("w") as f:
    for g in gaps:
        f.write(json.dumps(g) + "\n")

import lib.hermes_knowledge_gap_logger as gap_logger
gap_logger.GAP_JSONL = gap_file

from hermes_command_router.router import _run_knowledge_gap_review

print("-- Resolved candidate flags --")
status, evidence, rec = _run_knowledge_gap_review()
full = "\n".join(evidence)

check("status is warning (open gaps)", status == "warning")
check("resolved candidate flag appears", "resolved candidate" in full)

# Known resolved phrases should be flagged
check("'help' flagged as resolved candidate", "resolved candidate" in full and "help" in full.lower())
check("'weather' flagged as resolved candidate", "resolved candidate" in full and "weather" in full.lower())

# Non-resolved phrases should NOT be flagged
resolved_lines = [e for e in evidence if "resolved candidate" in e]
non_resolved_in_flagged = any(
    p in line
    for line in resolved_lines
    for p in ["trading dashboard", "credit score"]
)
check("non-resolved phrases NOT flagged", not non_resolved_in_flagged)

# Recommendation mentions resolved count
check("recommendation mentions resolved candidates", "resolved" in rec.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
