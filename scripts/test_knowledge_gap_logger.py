"""test_knowledge_gap_logger.py — Full gap logger verification."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unittest.mock import patch
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_knowledge_gap_logger ===\n")
import lib.hermes_knowledge_gap_logger as kgl
from lib.hermes_knowledge_gap_logger import (
    log_knowledge_gap, load_recent_knowledge_gaps, classify_gap_reason,
    format_gap_logged_response, create_gap_research_task, summarize_knowledge_gaps_for_review,
)
from lib.hermes_language_pack import (
    CATEGORY_UNKNOWN, CATEGORY_EXTERNAL_INFO, CATEGORY_SMALL_TALK,
    GAP_MISSING_ROUTE, GAP_UNSUPPORTED_EXTERNAL,
)

# classify_gap_reason
check("classify weather → unsupported_external_info",
      classify_gap_reason("what is the weather today") == GAP_UNSUPPORTED_EXTERNAL)
check("classify unknown question → missing_route",
      classify_gap_reason("this is a random thing") == GAP_MISSING_ROUTE)

# log_knowledge_gap — uses temp dir
with tempfile.TemporaryDirectory() as tmp:
    gap_dir = Path(tmp) / "gaps"
    gap_jsonl = gap_dir / "hermes_knowledge_gaps.jsonl"
    with patch.object(kgl, "GAP_DIR", gap_dir), patch.object(kgl, "GAP_JSONL", gap_jsonl):
        # Log several gaps
        r1 = log_knowledge_gap("what is the weather today", CATEGORY_EXTERNAL_INFO, GAP_UNSUPPORTED_EXTERNAL)
        check("r1 not skipped", not r1.get("skipped"))
        check("r1 has gap_id", "gap_id" in r1)
        check("r1 category correct", r1["category"] == CATEGORY_EXTERNAL_INFO)
        check("r1 requires_external_provider", r1["requires_external_provider"] is True)
        check("r1 safe_to_research False for external", r1["safe_to_research"] is False)
        r2 = log_knowledge_gap("random question", CATEGORY_UNKNOWN, GAP_MISSING_ROUTE)
        check("r2 not skipped", not r2.get("skipped"))
        check("r2 safe_to_research True", r2["safe_to_research"] is True)
        # Small talk skipped
        r3 = log_knowledge_gap("how are you", CATEGORY_SMALL_TALK, GAP_MISSING_ROUTE)
        check("small_talk gap skipped", r3.get("skipped") is True)
        # Load gaps
        gaps = load_recent_knowledge_gaps(limit=10)
        check("loaded 2 gaps (small_talk skipped)", len(gaps) == 2)
        check("gaps have timestamps", all("timestamp" in g for g in gaps))
        # Summarize
        summary = summarize_knowledge_gaps_for_review()
        check("summary is string", isinstance(summary, str))
        check("summary contains gap", "weather" in summary.lower() or "random" in summary.lower())
        # Research task
        gap_id = r2["gap_id"]
        task = create_gap_research_task(gap_id)
        check("task ok", task.get("ok") is True)
        check("task has gap_id", task.get("task", {}).get("gap_id") == gap_id)

# format_gap_logged_response
resp = format_gap_logged_response("what is the weather today", CATEGORY_EXTERNAL_INFO, GAP_UNSUPPORTED_EXTERNAL)
check("external resp no OFFLINE", "OFFLINE" not in resp)
check("external resp mentions provider", "provider" in resp.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
