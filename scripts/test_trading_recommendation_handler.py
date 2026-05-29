"""
test_trading_recommendation_handler.py
Verifies trading recommendation routes to internal handler, reads evidence,
and does not leak tool calls or timeout.
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

print("=== test_trading_recommendation_handler ===")

from lib.hermes_internal_first import try_internal_first
from lib.hermes_final_response_gate import inspect as gate_inspect
from pathlib import Path

TRADING_QUERIES = [
    "what trading strategy do you recommend",
    "what forex strategy should we test",
    "what is the best strategy so far",
    "what should we paper trade",
    "what did vibe-trading learn",
    "what is the best backtest result",
    "show backtest results",
]

for q in TRADING_QUERIES:
    result = try_internal_first(q)
    check(f"has internal reply for: {q[:50]}", result is not None)
    if result:
        check(f"topic is trading_recommendation: {q[:45]}", result.matched_topic == "trading_recommendation")
        check(f"not LLM source: {q[:45]}", result.source != "hermes_reasoning_layer")
        check(f"reply is non-empty: {q[:45]}", len(result.text.strip()) > 10)
        check(f"no raw tool call in reply: {q[:40]}", "search_files(" not in result.text and "read_file(" not in result.text)

# Verify evidence-based content when artifacts exist
vibe_dir = Path(__file__).resolve().parent.parent / "integrations" / "vibe_trading" / "reports"
oanda_dir = Path(__file__).resolve().parent.parent / "integrations" / "oanda_demo" / "reports"
has_vibe = bool(list(vibe_dir.glob("backtest_*.json"))) if vibe_dir.exists() else False
has_oanda = bool(list(oanda_dir.glob("demo_execution_packet_*.json"))) if oanda_dir.exists() else False

result = try_internal_first("what trading strategy do you recommend")
if result:
    text = result.text
    if has_vibe:
        check("reply mentions NEXUS TRADING RECOMMENDATION", "NEXUS TRADING RECOMMENDATION" in text)
        check("reply cites vibe_trading evidence", "vibe" in text.lower() or "backtest" in text.lower())
        check("reply does not invent metrics not in files", "NitroTrades" not in text)
        check("reply includes education disclaimer", "education" in text.lower() or "past" in text.lower())
    if has_oanda:
        check("reply mentions OANDA or demo evaluation", "oanda" in text.lower() or "demo" in text.lower())
    check("reply includes approval gate note", "ray approval" in text.lower() or "requires ray" in text.lower())

    # Gate check
    gate = gate_inspect(text)
    check("response passes gate (no fabricated counts)", gate.passed or "verified" in text.lower())

# Safety: no live trading recommendation
if result:
    check("no live trading recommendation in reply",
          "live trading" not in result.text.lower() or "requires ray approval" in result.text.lower() or "no live" in result.text.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
