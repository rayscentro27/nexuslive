from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any

from lib.trading_market_data import resolve_market_data_bundle
from lib.trading_safety_gate import evaluate_trading_safety
from lib.trading_strategy_watchers import evaluate_candidate


ROOT = Path(__file__).resolve().parent.parent
LIVE_WATCH_DIR = ROOT / "logs" / "live_watch"
CHART_DIR = ROOT / "logs" / "charts"
LATEST_JSON = LIVE_WATCH_DIR / "trading_watch_session_latest.json"
LATEST_MD = LIVE_WATCH_DIR / "trading_watch_session_latest.md"
LATEST_HTML = CHART_DIR / "live_watch_dashboard_latest.html"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_candidates(symbols: list[str]) -> list[dict[str, Any]]:
    payload = _load_json(ROOT / "logs" / "hermes_supabase_strategy_candidates_latest.json")
    candidates = payload.get("candidates") or []
    wanted = {symbol.upper().replace("_", "") for symbol in symbols}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        symbol = str(candidate.get("symbol") or "").upper().replace("_", "")
        if wanted and symbol not in wanted:
            continue
        row = dict(candidate)
        key = (str(row.get("strategy_id") or ""), symbol)
        if key in seen:
            continue
        seen.add(key)
        row.setdefault("strategy_family", _infer_family(row))
        row.setdefault("trigger_type", _infer_trigger(row))
        row.setdefault("execution_style", _infer_execution_style(row))
        rows.append(row)
    return rows


def _infer_family(candidate: dict[str, Any]) -> str:
    strategy_id = str(candidate.get("strategy_id") or "").lower()
    if "mean_reversion" in strategy_id:
        return "mean_reversion"
    if "pullback" in strategy_id:
        return "trend_following"
    if "breakout" in strategy_id:
        return "breakout"
    if "momentum" in strategy_id:
        return "technical_indicator"
    return "technical_indicator"


def _infer_trigger(candidate: dict[str, Any]) -> str:
    strategy_id = str(candidate.get("strategy_id") or "").lower()
    if "breakout" in strategy_id:
        return "scheduled_session"
    if "pullback" in strategy_id or "momentum" in strategy_id or "mean_reversion" in strategy_id:
        return "continuous_indicator"
    return "manual_review_only"


def _infer_execution_style(candidate: dict[str, Any]) -> str:
    strategy_id = str(candidate.get("strategy_id") or "").lower()
    if "breakout" in strategy_id:
        return "event_window"
    return "always_on"


def _render_dashboard(state: dict[str, Any]) -> str:
    rows = state.get("strategy_checks") or []
    cards: list[str] = []
    for row in rows[:10]:
        cards.append(
            "<tr>"
            f"<td>{row.get('symbol')}</td>"
            f"<td>{row.get('strategy_id')}</td>"
            f"<td>{'yes' if row.get('setup_detected') else 'no'}</td>"
            f"<td>{row.get('direction') or '-'}</td>"
            f"<td>{row.get('reason') or row.get('rejection_reason') or '-'}</td>"
            f"<td>{row.get('data_quality') or '-'}</td>"
            "</tr>"
        )
    table = "\n".join(cards) or "<tr><td colspan='6'>No strategy checks yet.</td></tr>"
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="10">
  <title>Nexus Live Watch</title>
  <style>
    body {{ font-family: sans-serif; background: #0f172a; color: #e2e8f0; padding: 24px; }}
    .meta {{ margin-bottom: 18px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ border-bottom: 1px solid #334155; padding: 8px; text-align: left; }}
    .ok {{ color: #4ade80; }}
    .no {{ color: #f59e0b; }}
  </style>
</head>
<body>
  <h1>Nexus Live Watch Dashboard</h1>
  <div class="meta">
    <div>Session: {state.get('session_name')}</div>
    <div>Mode: {state.get('mode')}</div>
    <div>Execution mode: {state.get('execution_mode')}</div>
    <div>Updated: {state.get('updated_at')}</div>
    <div>Safety: {'safe' if (state.get('safety') or {}).get('safe') else 'blocked'}</div>
  </div>
  <table>
    <thead>
      <tr><th>Symbol</th><th>Strategy</th><th>Setup</th><th>Dir</th><th>Reason</th><th>Data</th></tr>
    </thead>
    <tbody>{table}</tbody>
  </table>
</body>
</html>"""


def run_watch_session(
    *,
    session_name: str,
    symbols: list[str],
    mode: str = "paper",
    execute: bool = False,
    dry_run: bool = True,
    timeframe: str = "M15",
    candle_count: int = 96,
    data_source: str = "auto",
    refresh_seconds: int = 0,
    duration_minutes: int = 0,
) -> dict[str, Any]:
    LIVE_WATCH_DIR.mkdir(parents=True, exist_ok=True)
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    safety = evaluate_trading_safety(broker_mode="oanda_practice")
    candidates = _load_candidates(symbols)
    started_at = _now()

    def _run_iteration() -> dict[str, Any]:
        strategy_checks: list[dict[str, Any]] = []
        bundles: dict[str, dict[str, Any]] = {}
        for symbol in symbols:
            bundle = resolve_market_data_bundle(
                symbol,
                timeframe=timeframe,
                lookback=candle_count,
                preferred_source=data_source,
                allow_fallback=True,
            )
            candles = bundle.get("candles") or []
            bundles[symbol] = {
                "data_source": bundle.get("source"),
                "requested_source": data_source,
                "data_quality": bundle.get("data_quality"),
                "candle_count": bundle.get("candle_count", len(candles)),
                "latest_candle_time": candles[-1].get("time") if candles else None,
                "date_range": bundle.get("date_range"),
                "fallback_reason": bundle.get("fallback_reason"),
            }
            for candidate in candidates:
                if str(candidate.get("symbol") or "").upper().replace("_", "") != symbol.upper().replace("_", ""):
                    continue
                signal = evaluate_candidate(
                    candidate,
                    bundle,
                    execute=execute and not dry_run and safety.get("safe", False),
                    session_name=session_name,
                )
                signal["requested_data_source"] = data_source
                signal["latest_candle_time"] = bundles[symbol]["latest_candle_time"]
                strategy_checks.append(signal)
        state = {
            "updated_at": _now(),
            "session_name": session_name,
            "start_time": started_at,
            "end_time": None,
            "symbols": symbols,
            "mode": mode,
            "dry_run": dry_run,
            "execution_mode": "dry_run" if dry_run or not execute else "paper_execute",
            "requested_data_source": data_source,
            "active_strategies": [c.get("strategy_id") for c in candidates],
            "market_data": bundles,
            "strategy_checks": strategy_checks,
            "setup_detected": any(bool(row.get("setup_detected")) for row in strategy_checks),
            "trade_submitted": False,
            "chart_path": str(LATEST_HTML),
            "safety": safety,
        }
        return state

    loops = 1
    if refresh_seconds > 0 and duration_minutes > 0:
        loops = max(1, int((duration_minutes * 60) / refresh_seconds))

    state: dict[str, Any] = {}
    for idx in range(loops):
        state = _run_iteration()
        if idx == loops - 1:
            state["end_time"] = _now()
        LATEST_JSON.write_text(json.dumps(state, indent=2))
        lines = [
            "# Nexus Live Watch",
            "",
            f"- Session: `{session_name}`",
            f"- Mode: `{mode}`",
            f"- Execution mode: `{state['execution_mode']}`",
            f"- Requested data source: `{data_source}`",
            f"- Safety safe: `{'yes' if safety.get('safe') else 'no'}`",
            f"- Symbols: `{', '.join(symbols)}`",
            f"- Setup detected: `{'yes' if state['setup_detected'] else 'no'}`",
            "",
            "## Market Data",
        ]
        for symbol, meta in (state.get("market_data") or {}).items():
            lines.append(
                f"- `{symbol}` source=`{meta.get('data_source')}` quality=`{meta.get('data_quality')}` "
                f"candles=`{meta.get('candle_count')}` latest=`{meta.get('latest_candle_time')}` "
                f"fallback_reason=`{meta.get('fallback_reason')}`"
            )
        lines.append("")
        lines.append("## Strategy Checks")
        for row in (state.get("strategy_checks") or [])[:12]:
            lines.append(
                f"- `{row.get('symbol')}` `{row.get('strategy_id')}` "
                f"setup=`{'yes' if row.get('setup_detected') else 'no'}` "
                f"direction=`{row.get('direction')}` reason=`{row.get('reason') or row.get('rejection_reason')}` "
                f"data_quality=`{row.get('data_quality')}` latest_candle=`{row.get('latest_candle_time')}`"
            )
        LATEST_MD.write_text("\n".join(lines) + "\n")
        LATEST_HTML.write_text(_render_dashboard(state))
        if idx < loops - 1:
            time.sleep(refresh_seconds)
    return state
