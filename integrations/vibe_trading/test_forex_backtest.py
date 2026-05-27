"""
test_forex_backtest.py — Phase 6 first forex strategy backtest.

Runs an education-only EUR/USD RSI(14) mean-reversion backtest via the
Nexus Vibe-Trading adapter and saves the result to reports/.

Usage:
    cd nexus-ai
    source integrations/vibe_trading/.venv/bin/activate
    python integrations/vibe_trading/test_forex_backtest.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # nexus-ai/
sys.path.insert(0, str(ROOT))

from integrations.vibe_trading.vibe_trading_adapter import run_vibe_trading_task

FOREX_PROMPT = (
    "Education-only paper-trading research. "
    "Backtest a simple EUR/USD RSI(14) mean-reversion strategy using free data if available. "
    "Rules: Buy when RSI(14) < 30 on daily bars, exit when RSI(14) > 50 or after 10 bars. "
    "No stop-loss for simplicity. "
    "Report: max drawdown, win rate, Sharpe ratio, total trade count, average trade duration, "
    "net P&L (pip-based or % return), assumptions, data source used, known limitations. "
    "Do not execute any trades. Use only historical/simulated data."
)

REPORT_DIR  = Path(__file__).resolve().parent / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    print("=" * 60)
    print("NEXUS VIBE-TRADING — FOREX RSI(14) BACKTEST")
    print("Mode: Education-Only / Paper-Trading")
    print("=" * 60)
    print()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REPORT_DIR / f"forex_rsi_test_{ts}.json"

    print(f"Prompt: {FOREX_PROMPT[:120]}...")
    print(f"Output: {out_path}")
    print()

    try:
        result = run_vibe_trading_task(
            prompt=FOREX_PROMPT,
            task_type="backtest",
            timeout=300,
        )
    except ValueError as exc:
        print(f"BLOCKED by safety layer: {exc}", file=sys.stderr)
        sys.exit(1)

    # Save with explicit timestamped name
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"Report written: {out_path}")

    rc = result["return_code"]
    print(f"Return code:    {rc}")
    print()

    if rc == 0 and result.get("stdout"):
        print("=== BACKTEST OUTPUT ===")
        print(result["stdout"][:3000])
    elif result.get("stderr"):
        print("=== ERROR / STDERR ===")
        print(result["stderr"][:1000])
        print()
        print("Note: If vibe-trading CLI is not installed, run:")
        print("  source integrations/vibe_trading/.venv/bin/activate")
        print("  pip install -U vibe-trading-ai")
        print("Then re-run this script.")

    print()
    print("=== SAFETY CONFIRMATION ===")
    print(f"  safety_mode : {result.get('safety_mode')}")
    print(f"  cost_mode   : {result.get('cost_mode')}")
    print(f"  task_type   : {result.get('task_type')}")
    print(f"  report_path : {result.get('report_path')}")
    print(result.get("disclaimer", "").strip())
