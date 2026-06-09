#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_fallback_logger import latest_jsonl


VIBE_REPORT_DIR = ROOT / "integrations" / "vibe_trading" / "reports"


def _latest_backtest_report() -> dict:
    path = ROOT / "logs" / "backtest_report_20260608.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def main() -> int:
    if "--latest-tournament" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--latest-tournament"]
    VIBE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    score_rows = latest_jsonl("strategy_scores", limit=20)
    trade_rows = latest_jsonl("trades", limit=20)
    backtest = _latest_backtest_report()

    top = score_rows[-1] if score_rows else {}
    recommendations: list[str] = []
    if top:
        if float(top.get("profit_factor", 0.0)) < 1.0:
            recommendations.append("Tighten stop-loss placement or reduce false-positive entries before promoting broader paper activity.")
        if float(top.get("max_drawdown", 0.0)) > 5.0:
            recommendations.append("Reduce drawdown by lowering risk per trade and avoiding low-conviction entries.")
        if float(top.get("win_rate", 0.0)) < 0.55:
            recommendations.append("Improve filter quality; current win rate is too weak for aggressive promotion.")
    if not recommendations:
        recommendations.append("Continue collecting paper evidence and compare session-specific performance before changing parameters.")

    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "provider_status": "offline_local_review",
        "latest_strategy_score": top,
        "latest_backtest_summary": backtest.get("summary") or {},
        "latest_paper_trade": trade_rows[-1] if trade_rows else {},
        "recommendations": recommendations,
        "failure_reasons": [
            "Vibe provider/data preflight is not currently available",
            "Review uses local tournament/backtest/trade artifacts only",
        ],
    }

    json_path = VIBE_REPORT_DIR / f"vibe_strategy_review_{ts}.json"
    md_path = VIBE_REPORT_DIR / f"vibe_strategy_review_{ts}.md"
    json_path.write_text(json.dumps(summary, indent=2, default=str))
    md_path.write_text(
        "\n".join(
            [
                "# Vibe Strategy Review",
                "",
                f"- Provider status: {summary['provider_status']}",
                f"- Latest top strategy: {top.get('strategy_name', top.get('strategy_id', 'none')) if top else 'none'}",
                f"- Latest backtest return: {(backtest.get('summary') or {}).get('return_pct', 'n/a')}",
                f"- Latest paper trade status: {((trade_rows[-1].get('result') or {}).get('status')) if trade_rows else 'none'}",
                "",
                "## Recommendations",
            ]
            + [f"- {item}" for item in recommendations]
        )
    )

    print(json.dumps({"json_report": str(json_path), "markdown_report": str(md_path), "recommendations": recommendations}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
