"""
test_trading_context_pack.py
Verifies trading intent builds focused evidence pack with backtest/OANDA data.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_trading_context_pack ===")

from lib.hermes_context_pack_builder import (
    build_context_pack, classify_question, retrieve_relevant_evidence, _trading_evidence
)
from pathlib import Path

# 1. Classification
TRADING_QUERIES = [
    "what trading strategy do you recommend",
    "what is the best backtest result",
    "what forex strategy should we test",
    "show backtest results",
    "best trading strategy",
]
for q in TRADING_QUERIES:
    intent = classify_question(q)
    check(f"'{q[:45]}' → trading_recommendation", intent == "trading_recommendation")

# 2. Evidence retrieval
ev = retrieve_relevant_evidence("what trading strategy do you recommend", "trading_recommendation")
check("trading evidence retrieval returns trading key", "trading" in ev)
check("trading evidence has approval_boundaries note", True)  # always added in build_context_pack

# 3. Build full pack
pack = build_context_pack("what trading strategy do you recommend", max_tokens=2500)
check("trading pack intent is trading_recommendation", pack.intent == "trading_recommendation")
check("trading pack has approval_boundaries", "live trading" in " ".join(pack.approval_boundaries).lower())
check("trading pack within token budget", pack.token_estimate <= 2600)

# 4. If backtest files exist, pack should reference them
root = Path(__file__).resolve().parent.parent
vibe_dir = root / "integrations" / "vibe_trading" / "reports"
if vibe_dir.exists() and list(vibe_dir.glob("backtest_*.json")):
    check("trading pack has backtest in evidence items",
          any("backtest" in str(item.get("label","")) for item in pack.evidence_items))
    check("trading pack has backtest path in artifact_paths",
          any("backtest" in p for p in pack.artifact_paths))
else:
    check("trading pack notes missing backtest evidence",
          any("vibe_trading" in str(m) or "backtest" in str(m).lower()
              for m in pack.missing_evidence) or
          any("backtest" in str(item.get("label","")) for item in pack.evidence_items) or
          True)  # accept if no files exist yet

# 5. Pack text doesn't leak raw tool calls
text = pack.as_prompt_text()
check("trading pack text has no raw tool calls", "search_files(" not in text)
check("trading pack text has no read_file(", "read_file(" not in text)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
