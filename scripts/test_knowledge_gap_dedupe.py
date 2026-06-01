"""
test_knowledge_gap_dedupe.py
Verifies that _run_knowledge_gap_review groups duplicate gaps by normalized message.
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

print("=== test_knowledge_gap_dedupe ===\n")

# Build synthetic gap records to test grouping
from datetime import datetime, timezone

def _make_gap(msg: str, i: int = 0) -> dict:
    return {
        "gap_id": f"gap_test_{i:04d}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_message": msg,
        "normalized_message": " ".join(msg.strip().lower().split()),
        "category": "external_info_question",
        "reason": "unsupported_external_info",
        "status": "open",
        "priority": "medium",
        "suggested_handler": "add_external_provider",
    }

# Simulate 5x "weather" gaps, 3x "news" gaps, 1x "help" gap
gaps = (
    [_make_gap("what is the weather today", i) for i in range(5)]
    + [_make_gap("latest news", i + 10) for i in range(3)]
    + [_make_gap("help", 20)]
)

# Write to a temp JSONL and monkey-patch the loader
import tempfile
from pathlib import Path

tmp_dir = Path(tempfile.mkdtemp())
gap_file = tmp_dir / "hermes_knowledge_gaps.jsonl"
with gap_file.open("w") as f:
    for g in gaps:
        f.write(json.dumps(g) + "\n")

# Monkey-patch load_recent_knowledge_gaps
import lib.hermes_knowledge_gap_logger as gap_logger
original_gap_dir = gap_logger.GAP_JSONL
gap_logger.GAP_JSONL = gap_file

# Now test _run_knowledge_gap_review
from hermes_command_router.router import _run_knowledge_gap_review

print("-- Gap grouping --")
status, evidence, rec = _run_knowledge_gap_review()
full = "\n".join(evidence)

check("status is warning (open gaps present)", status == "warning")
check("evidence is non-empty", len(evidence) > 0)

# Check that counts appear (e.g. "asked 5×" for weather)
check("'asked 5×' for weather group", "5×" in full)
check("'asked 3×' for news group", "3×" in full)

# Check grouping reduced entries (9 raw → 3 unique)
# Count numbered items in evidence
numbered = [e for e in evidence if e and e[0].isdigit() and e[1] == "."]
check("grouped to fewer unique entries than raw total", len(numbered) < len(gaps))

# Check recommendation mentions unique count
check("recommendation mentions unique count", "3" in rec or "unique" in rec.lower())

# Restore
gap_logger.GAP_JSONL = original_gap_dir

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
