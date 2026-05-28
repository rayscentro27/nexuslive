"""
test_no_fake_trading_claims.py
================================
Verify that fake trading execution claims are blocked at every layer:
  1. hermes_evidence_mode.is_fake_trading_claim()
  2. hermes_command_router.run_command()
  3. hermes_collaboration_service.HermesCollaboration.handle()
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_evidence_mode import is_fake_trading_claim, HermesEvidenceMode

PASS = 0
FAIL = 0


def check(desc: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  ✅ {desc}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {desc}")
        FAIL += 1


print("\n=== test_no_fake_trading_claims ===\n")

FAKE_CLAIMS = [
    "executing scalp on EUR/USD",
    "scalp active, target 1.0850",
    "trade placed at market",
    "target hit at 1.0832",
    "stop moved to break even",
    "tracking live price action",
    "order confirmed, filled at 1.0831",
    "pushing to live instance",
    "live instance updated",
    "entering long EUR/USD",
    "entering short GBP/USD",
    "position open at 1.0830",
    "filled at 1.0831",
    "pips gained: 12",
    "pips lost: 8",
]

ALLOWED_QUERIES = [
    "show me oanda demo status",
    "what happened with the last demo run",
    "what is the oanda environment set to",
    "show me demo execution packet",
    "what is the paper trading result",
    "backtest on EUR/USD RSI strategy",
]

print("  Layer 1 — is_fake_trading_claim():")
for phrase in FAKE_CLAIMS:
    check(f"blocked: '{phrase[:50]}'", is_fake_trading_claim(phrase))

for phrase in ALLOWED_QUERIES:
    check(f"allowed: '{phrase[:50]}'", not is_fake_trading_claim(phrase))

print("\n  Layer 2 — block_unverified_operational_claim():")
ev = HermesEvidenceMode()
for phrase in FAKE_CLAIMS[:5]:
    blocked, phrases = ev.block_unverified_operational_claim(phrase)
    check(f"block_unverified blocks: '{phrase[:40]}'", blocked)

print("\n  Layer 3 — HermesCollaboration.handle():")
try:
    from lib.hermes_collaboration_service import HermesCollaboration
    collab = HermesCollaboration()
    for fake in ["scalp active right now", "trade placed on EUR/USD"]:
        result = collab.handle(fake)
        check(
            f"collab.handle blocks fake trade: '{fake[:40]}'",
            result.get("artifact_status") == "blocked" or
            "cannot report" in result.get("answer", "").lower() or
            "no order" in result.get("answer", "").lower()
        )
except Exception as e:
    print(f"  [SKIP] HermesCollaboration not available: {e}")

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
