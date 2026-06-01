"""test_external_info_logs_gap.py — External info questions log a gap and return safe message."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unittest.mock import patch
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_external_info_logs_gap ===\n")
from lib.hermes_conversational_router import classify_conversational_intent, route_conversational_intent
from lib.hermes_language_pack import CATEGORY_EXTERNAL_INFO
import lib.hermes_knowledge_gap_logger as kgl

phrases = [
    "what is the weather today", "latest news", "stock price",
    "what is the current price of bitcoin", "sports score",
]
for phrase in phrases:
    cat = classify_conversational_intent(phrase)
    check(f"'{phrase}' → external_info", cat == CATEGORY_EXTERNAL_INFO)

with tempfile.TemporaryDirectory() as tmp:
    gap_dir = Path(tmp) / "gaps"
    gap_jsonl = gap_dir / "hermes_knowledge_gaps.jsonl"
    with patch.object(kgl, "GAP_DIR", gap_dir), patch.object(kgl, "GAP_JSONL", gap_jsonl):
        resp = route_conversational_intent("what is the weather today")
        check("weather response is string", isinstance(resp, str))
        check("weather no hallucination", "OFFLINE" not in (resp or "") and "Beehiiv" not in (resp or ""))
        check("weather mentions provider", "provider" in (resp or "").lower() or "not" in (resp or "").lower())
        check("weather response mentions gap", "gap" in (resp or "").lower() or "logged" in (resp or "").lower())
        # Check gap was logged
        gaps = kgl.load_recent_knowledge_gaps(limit=5)
        check("gap logged for weather question", len(gaps) > 0)
        if gaps:
            check("gap category is external_info", gaps[0].get("category") == CATEGORY_EXTERNAL_INFO)
            check("gap reason is unsupported_external_info", gaps[0].get("reason") == "unsupported_external_info")
            check("gap requires_external_provider", gaps[0].get("requires_external_provider") is True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
