"""test_gap_review_commands.py — Show knowledge gaps and research commands work."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unittest.mock import patch
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_gap_review_commands ===\n")
from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command
import lib.hermes_knowledge_gap_logger as kgl
from lib.hermes_knowledge_gap_logger import log_knowledge_gap
from lib.hermes_language_pack import CATEGORY_UNKNOWN, GAP_MISSING_ROUTE

# Intent classification
for phrase in ["show knowledge gaps", "show unanswered questions",
               "what could you not answer today", "show gaps"]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → knowledge_gap_review", intent == "knowledge_gap_review")
for phrase in ["research unanswered questions", "create better answers for gaps"]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → knowledge_gap_research", intent == "knowledge_gap_research")
for phrase in ["archive resolved gaps"]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → knowledge_gap_archive", intent == "knowledge_gap_archive")

# run_command for gap review
with tempfile.TemporaryDirectory() as tmp:
    gap_dir = Path(tmp) / "gaps"
    gap_jsonl = gap_dir / "hermes_knowledge_gaps.jsonl"
    with patch.object(kgl, "GAP_DIR", gap_dir), patch.object(kgl, "GAP_JSONL", gap_jsonl):
        log_knowledge_gap("what is the weather today", "external_info_question", "unsupported_external_info")
        log_knowledge_gap("random thing", CATEGORY_UNKNOWN, GAP_MISSING_ROUTE)
        resp = run_command("show knowledge gaps", source="telegram")
        check("gap review response is string", isinstance(resp, str))
        check("gap review no OFFLINE", "OFFLINE" not in resp)
        check("gap review no Beehiiv stale", "Beehiiv pending" not in resp)

# Empty gap review
with tempfile.TemporaryDirectory() as tmp:
    gap_dir2 = Path(tmp) / "gaps"
    gap_jsonl2 = gap_dir2 / "hermes_knowledge_gaps.jsonl"
    with patch.object(kgl, "GAP_DIR", gap_dir2), patch.object(kgl, "GAP_JSONL", gap_jsonl2):
        resp2 = run_command("show knowledge gaps", source="telegram")
        check("empty gap review is string", isinstance(resp2, str))
        check("empty gap review says no gaps", "no open" in resp2.lower() or "No open" in resp2)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
