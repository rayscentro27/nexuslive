"""test_unknown_question_logs_gap.py — Unknown questions log a gap, return safe fallback."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unittest.mock import patch
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_unknown_question_logs_gap ===\n")
import lib.hermes_knowledge_gap_logger as kgl
from lib.hermes_knowledge_gap_logger import log_knowledge_gap, format_gap_logged_response
from lib.hermes_language_pack import CATEGORY_UNKNOWN, GAP_MISSING_ROUTE

with tempfile.TemporaryDirectory() as tmp:
    gap_dir = Path(tmp) / "gaps"
    gap_jsonl = gap_dir / "hermes_knowledge_gaps.jsonl"
    with patch.object(kgl, "GAP_DIR", gap_dir), patch.object(kgl, "GAP_JSONL", gap_jsonl):
        q = "what is the meaning of life"
        rec = log_knowledge_gap(q, CATEGORY_UNKNOWN, GAP_MISSING_ROUTE)
        check("gap record has gap_id", "gap_id" in rec)
        check("gap record has category", rec.get("category") == CATEGORY_UNKNOWN)
        check("gap record has reason", rec.get("reason") == GAP_MISSING_ROUTE)
        check("gap record status open", rec.get("status") == "open")
        check("gap created_from telegram", rec.get("created_from") == "telegram")
        gaps = kgl.load_recent_knowledge_gaps(limit=5)
        check("gap persisted to JSONL", len(gaps) > 0)

resp = format_gap_logged_response("random unsupported thing", CATEGORY_UNKNOWN, GAP_MISSING_ROUTE)
check("fallback response is string", isinstance(resp, str))
check("fallback no artifact_inventory", "artifact_inventory" not in resp.lower())
check("fallback no OFFLINE", "OFFLINE" not in resp)
check("fallback no executive memory", "executive memory" not in resp.lower() or "archived" in resp.lower())
check("fallback mentions knowledge gap", "gap" in resp.lower() or "knowledge" in resp.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
