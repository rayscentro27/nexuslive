"""test_response_improvement_loop.py — Response improvement loop creates proposals."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unittest.mock import patch
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_response_improvement_loop ===\n")
import lib.hermes_knowledge_gap_logger as kgl
from lib.hermes_knowledge_gap_logger import log_knowledge_gap
from lib.hermes_language_pack import CATEGORY_UNKNOWN, CATEGORY_EXTERNAL_INFO, GAP_MISSING_ROUTE, GAP_UNSUPPORTED_EXTERNAL
import lib.hermes_response_improvement_loop as ril

with tempfile.TemporaryDirectory() as tmp:
    gap_dir = Path(tmp) / "gaps"
    gap_jsonl = gap_dir / "hermes_knowledge_gaps.jsonl"
    report_dir = gap_dir
    with patch.object(kgl, "GAP_DIR", gap_dir), patch.object(kgl, "GAP_JSONL", gap_jsonl), \
         patch.object(ril, "REPORT_DIR", report_dir):
        # Seed gaps
        log_knowledge_gap("what is the weather today", CATEGORY_EXTERNAL_INFO, GAP_UNSUPPORTED_EXTERNAL)
        log_knowledge_gap("unknown question", CATEGORY_UNKNOWN, GAP_MISSING_ROUTE)
        log_knowledge_gap("another unknown", CATEGORY_UNKNOWN, GAP_MISSING_ROUTE)
        # Repeated question
        log_knowledge_gap("unknown question", CATEGORY_UNKNOWN, GAP_MISSING_ROUTE)

        gaps = ril.analyze_knowledge_gaps()
        check("analyze returns list", isinstance(gaps, list))
        check("analyze found gaps", len(gaps) > 0)

        lang = ril.propose_language_pack_updates(gaps)
        check("lang proposals list", isinstance(lang, list))

        aliases = ril.propose_new_intent_aliases(gaps)
        check("aliases proposals list", isinstance(aliases, list))

        memory = ril.propose_memory_items(gaps)
        check("memory proposals list", isinstance(memory, list))
        check("repeated unknown found in memory proposals", any(m.get("asked_count", 0) >= 2 for m in memory))

        report_path = ril.create_response_improvement_report()
        check("report path is string", isinstance(report_path, str))
        check("report file created", Path(report_path).exists())
        content = Path(report_path).read_text()
        check("report has gap count", "Open gaps" in content)
        check("report has Next Recommended Step", "Next Recommended Step" in content)
        check("report no OFFLINE in content", "OFFLINE" not in content)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
