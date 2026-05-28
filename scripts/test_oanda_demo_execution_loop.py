"""
OANDA Demo Execution Loop
Reads the latest strategy from Vibe-Trading backtest results, evaluates it,
and optionally places a 1-unit practice order if all guards pass.

Safety: OANDA_DEMO_ENABLED must be true (Ray approval).
        OANDA_ALLOW_LIVE must be false (hardcoded block).
        Max 1 unit. Max 3 orders/day.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[1] / ".env")
    load_dotenv(Path(__file__).parents[1] / "integrations/oanda_demo/.env")
except ImportError:
    pass

from integrations.oanda_demo import OandaDemoAdapter
from integrations.oanda_demo.oanda_demo_adapter import OandaSafetyError
from lib.hermes_ceo_decision_policy import classify_action

DEMO_REPORTS = Path("integrations/oanda_demo/reports")
DEMO_REPORTS.mkdir(parents=True, exist_ok=True)

VIBE_BACKTEST_DIR = Path("integrations/vibe_trading/results")


def _load_latest_strategy() -> dict | None:
    """Read latest vibe-trading backtest result if available."""
    if not VIBE_BACKTEST_DIR.exists():
        return None
    files = sorted(VIBE_BACKTEST_DIR.glob("*.json"))
    if not files:
        return None
    data = json.loads(files[-1].read_text())
    # Expected keys: instrument, signal, win_rate, last_signal_type
    return data


def _evaluate_strategy(strategy: dict) -> dict:
    """
    Simple signal quality gate: only pass if win_rate >= 0.55 and signal is clear.
    Returns: {pass: bool, reason: str, instrument: str, side: str}
    """
    win_rate  = strategy.get("win_rate", 0)
    signal    = strategy.get("last_signal_type", "").lower()
    instrument = strategy.get("instrument", "EUR_USD")

    if win_rate < 0.55:
        return {"pass": False, "reason": f"win_rate={win_rate:.2f} < 0.55 threshold", "instrument": instrument}
    if signal not in ("buy", "sell"):
        return {"pass": False, "reason": f"unclear signal '{signal}'", "instrument": instrument}

    return {"pass": True, "reason": f"win_rate={win_rate:.2f}, signal={signal}", "instrument": instrument, "side": signal}


def _save_execution_packet(strategy: dict, eval_result: dict, order_result: dict | None, ts: str) -> Path:
    packet = {
        "run_id": f"demo_exec_{ts}",
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "strategy": strategy,
        "evaluation": eval_result,
        "order_result": order_result,
    }
    path = DEMO_REPORTS / f"demo_execution_packet_{ts}.json"
    path.write_text(json.dumps(packet, indent=2))
    return path


def main(dry_run: bool = False) -> None:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    print(f"[demo_exec] Starting OANDA demo execution loop — {ts}")

    # Policy check
    decision = classify_action("run_demo_broker_test", "test_oanda_demo_execution_loop.py")
    print(f"[demo_exec] Policy: {decision['decision']} — {decision['rule']}")
    if decision["decision"] == "blocked":
        print("[demo_exec] ⛔ Blocked by policy. Exiting.")
        sys.exit(2)

    # Load strategy
    strategy = _load_latest_strategy()
    if not strategy:
        strategy = {
            "instrument": "EUR_USD",
            "win_rate": 0.57,
            "last_signal_type": "buy",
            "source": "synthetic_test_signal",
        }
        print("[demo_exec] No backtest result found. Using synthetic test signal.")
    else:
        print(f"[demo_exec] Loaded strategy: {strategy.get('instrument')} | win_rate={strategy.get('win_rate')}")

    # Evaluate
    eval_result = _evaluate_strategy(strategy)
    print(f"[demo_exec] Evaluation: pass={eval_result['pass']} | {eval_result['reason']}")

    order_result = None
    if eval_result["pass"] and not dry_run:
        adapter = OandaDemoAdapter()
        try:
            order_result = adapter.place_demo_order(
                instrument=eval_result["instrument"],
                side=eval_result["side"],
                units=1,
                reason=f"demo_exec_loop_{ts}: {eval_result['reason']}",
            )
            status = "✅ PLACED" if order_result["ok"] else f"❌ FAILED: {order_result.get('error')}"
            print(f"[demo_exec] Order: {status}")
        except OandaSafetyError as e:
            print(f"[demo_exec] ⛔ Safety block: {e}")
            order_result = {"ok": False, "error": str(e), "blocked_by": "safety"}
    elif dry_run:
        print("[demo_exec] Dry-run mode — no order placed.")
    else:
        print(f"[demo_exec] Strategy did not pass evaluation gate — no order placed.")

    # Save packet
    packet_path = _save_execution_packet(strategy, eval_result, order_result, ts)
    print(f"[demo_exec] ✅ Execution packet → {packet_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Evaluate strategy but do not place order")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
