from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def _price_bounds(candles: list[dict[str, Any]]) -> tuple[float, float]:
    lows = [float(c["low"]) for c in candles if c.get("low") is not None]
    highs = [float(c["high"]) for c in candles if c.get("high") is not None]
    return (min(lows), max(highs)) if lows and highs else (0.0, 1.0)


def _y(price: float, low: float, high: float, height: int) -> float:
    if high <= low:
        return height / 2
    return 20 + (height - 40) * (1 - ((price - low) / (high - low)))


def render_candles_svg(
    candles: list[dict[str, Any]],
    *,
    entry_price: float | None = None,
    exit_price: float | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> str:
    if not candles:
        return "<svg width='960' height='360'><text x='16' y='40' fill='#e2e8f0'>No candles available</text></svg>"
    width = 960
    height = 360
    low, high = _price_bounds(candles)
    step = max(6, int((width - 80) / max(len(candles), 1)))
    items: list[str] = [
        f"<rect x='0' y='0' width='{width}' height='{height}' fill='#0f172a' />",
    ]
    for idx, candle in enumerate(candles):
        x = 40 + idx * step
        open_ = float(candle["open"])
        close = float(candle["close"])
        high_ = float(candle["high"])
        low_ = float(candle["low"])
        color = "#22c55e" if close >= open_ else "#ef4444"
        items.append(f"<line x1='{x}' y1='{_y(high_, low, high, height):.1f}' x2='{x}' y2='{_y(low_, low, high, height):.1f}' stroke='{color}' stroke-width='1' />")
        body_top = min(_y(open_, low, high, height), _y(close, low, high, height))
        body_bottom = max(_y(open_, low, high, height), _y(close, low, high, height))
        items.append(f"<rect x='{x-2}' y='{body_top:.1f}' width='4' height='{max(1.0, body_bottom - body_top):.1f}' fill='{color}' />")
    overlays = [
        ("Entry", entry_price, "#38bdf8"),
        ("Exit", exit_price, "#f8fafc"),
        ("Stop", stop_loss, "#f97316"),
        ("Target", take_profit, "#a78bfa"),
    ]
    for label, price, color in overlays:
        if price is None:
            continue
        y = _y(float(price), low, high, height)
        items.append(f"<line x1='20' y1='{y:.1f}' x2='{width-20}' y2='{y:.1f}' stroke='{color}' stroke-dasharray='4 4' />")
        items.append(f"<text x='{width-160}' y='{y-4:.1f}' fill='{color}' font-size='12'>{escape(label)} {price}</text>")
    return f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>{''.join(items)}</svg>"


def render_trade_replay_html(payload: dict[str, Any]) -> str:
    chart = render_candles_svg(
        payload.get("candles") or [],
        entry_price=payload.get("entry_price"),
        exit_price=payload.get("exit_price"),
        stop_loss=payload.get("stop_loss"),
        take_profit=payload.get("take_profit"),
    )
    lines = [
        f"<div>Symbol: {escape(str(payload.get('symbol') or 'unknown'))}</div>",
        f"<div>Strategy: {escape(str(payload.get('strategy_id') or 'unknown'))}</div>",
        f"<div>Strategy family: {escape(str(payload.get('strategy_family') or 'unknown'))}</div>",
        f"<div>Trigger type: {escape(str(payload.get('trigger_type') or 'unknown'))}</div>",
        f"<div>Status: {escape(str(payload.get('status') or 'unknown'))}</div>",
        f"<div>Reason: {escape(str(payload.get('reason') or payload.get('rejection_reason') or 'n/a'))}</div>",
        f"<div>Order/Trade ID: {escape(str(payload.get('trade_or_order_id') or 'n/a'))}</div>",
        f"<div>Session window: {escape(str(payload.get('session_window') or 'n/a'))}</div>",
        f"<div>Data source: {escape(str(payload.get('data_source') or 'unknown'))}</div>",
        f"<div>Data quality: {escape(str(payload.get('data_quality') or 'unknown'))}</div>",
        f"<div>Fallback reason: {escape(str(payload.get('fallback_reason') or 'none'))}</div>",
    ]
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Nexus Trade Replay</title>
  <style>
    body {{ font-family: sans-serif; background: #020617; color: #e2e8f0; padding: 24px; }}
    .meta {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-bottom: 18px; }}
    .chart {{ border: 1px solid #334155; padding: 12px; background: #0f172a; }}
  </style>
</head>
<body>
  <h1>Nexus Trade Replay</h1>
  <div class="meta">{''.join(f'<div>{line}</div>' for line in lines)}</div>
  <div class="chart">{chart}</div>
</body>
</html>"""


def render_dashboard_html(payload: dict[str, Any]) -> str:
    links = payload.get("links") or []
    rows = payload.get("rows") or []
    row_html = "".join(
        "<tr>"
        f"<td>{escape(str(row.get('label') or ''))}</td>"
        f"<td>{escape(str(row.get('value') or ''))}</td>"
        "</tr>"
        for row in rows
    )
    link_html = "".join(
        f"<li><a href='{escape(str(link.get('href') or '#'))}'>{escape(str(link.get('label') or 'link'))}</a></li>"
        for link in links
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="15">
  <title>Nexus Trading Dashboard</title>
  <style>
    body {{ font-family: sans-serif; background: #111827; color: #f3f4f6; padding: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 18px; }}
    td, th {{ border-bottom: 1px solid #374151; padding: 8px; text-align: left; }}
    a {{ color: #93c5fd; }}
  </style>
</head>
<body>
  <h1>Nexus Trading Dashboard</h1>
  <table>{row_html}</table>
  <ul>{link_html}</ul>
</body>
</html>"""
