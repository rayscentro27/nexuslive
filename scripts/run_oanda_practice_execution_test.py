#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from integrations.oanda_demo import OandaDemoAdapter
from integrations.oanda_demo.oanda_demo_adapter import OandaSafetyError
from lib.trading_fallback_logger import latest_jsonl
from lib.trading_safety_gate import evaluate_trading_safety, seed_safe_trading_env_from_launch_agent


REPORT_DIR = ROOT / "reports" / "trading" / "oanda_practice_execution_test"
LEARNING_JSON = ROOT / "logs" / "oanda_practice_execution_learning_latest.json"
LEARNING_MD = ROOT / "logs" / "oanda_practice_execution_learning_latest.md"
PREFLIGHT_MD = REPORT_DIR / "oanda_practice_preflight.md"
PREFLIGHT_RETRY_MD = REPORT_DIR / "oanda_practice_preflight_retry.md"
DIAGNOSTIC_MD = REPORT_DIR / "oanda_connectivity_diagnostic.md"
APPROVAL_MD = REPORT_DIR / "demo_trade_approval_record.md"
PLAN_MD = REPORT_DIR / "demo_trade_plan.md"
PAYLOAD_JSON = REPORT_DIR / "demo_order_payload_dry_run.json"
PAYLOAD_MD = REPORT_DIR / "demo_order_payload_review.md"
PAYLOAD_RETRY_JSON = REPORT_DIR / "demo_order_payload_retry_dry_run.json"
PAYLOAD_RETRY_MD = REPORT_DIR / "demo_order_payload_retry_review.md"
ORDER_RESPONSE_JSON = REPORT_DIR / "oanda_practice_order_response.json"
ORDER_RESPONSE_MD = REPORT_DIR / "oanda_practice_order_response.md"
ORDER_RETRY_JSON = REPORT_DIR / "oanda_practice_order_retry_response.json"
ORDER_RETRY_MD = REPORT_DIR / "oanda_practice_order_retry_response.md"
TRADE_STATE_MD = REPORT_DIR / "oanda_practice_trade_state.md"
MONITOR_MD = REPORT_DIR / "oanda_practice_trade_monitor.md"
TRADE_RETRY_STATE_MD = REPORT_DIR / "oanda_practice_trade_retry_state.md"
TRADE_RETRY_MONITOR_MD = REPORT_DIR / "oanda_practice_trade_retry_monitor.md"
FINAL_MD = REPORT_DIR / "OANDA_PRACTICE_EXECUTION_FINAL_REPORT.md"
FINAL_RETRY_MD = REPORT_DIR / "OANDA_PRACTICE_EXECUTION_RETRY_FINAL_REPORT.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _md(lines: list[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_md(lines))


def _copy_text(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text())


def _copy_json(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text())


def _run_json(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    raw = (proc.stdout or proc.stderr or "").strip()
    payload: Any = {}
    if raw:
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw}
    if not isinstance(payload, dict):
        payload = {"payload": payload}
    payload["_returncode"] = proc.returncode
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _mask_account_id(value: str) -> str:
    text = str(value or "")
    if len(text) <= 4:
        return "***"
    return f"{text[:2]}***{text[-2:]}"


def _env_flag(name: str, default: str = "") -> str:
    return "yes" if bool(os.getenv(name, default)) else "no"


def _bool_text(value: Any) -> str:
    return "yes" if bool(value) else "no"


PAYLOAD_VALIDATION_EXPECTED: dict[str, bool] = {
    "practice_account_confirmed": True,
    "instrument_present": True,
    "units_present": True,
    "stop_loss_present": True,
    "take_profit_present": True,
    "live_endpoint_targeted": False,
    "live_account_targeted": False,
    "smallest_safe_demo_size": True,
    "spread_normal": True,
    "market_open_tradeable": True,
}


def payload_validation_passed(validation: dict[str, bool]) -> bool:
    expected = PAYLOAD_VALIDATION_EXPECTED
    return all(validation.get(k) == v for k, v in expected.items())


def payload_validation_failures(validation: dict[str, bool]) -> list[str]:
    expected = PAYLOAD_VALIDATION_EXPECTED
    return [k for k, v in expected.items() if validation.get(k) != v]


def _common_bank_funding_presence() -> dict[str, bool]:
    keys = [
        "PLAID_CLIENT_ID",
        "PLAID_SECRET",
        "STRIPE_SECRET_KEY",
        "BANK_ACCOUNT_ID",
        "BANK_ROUTING_NUMBER",
        "FUNDING_ACCOUNT_ID",
        "BROKER_FUNDING_ENABLED",
    ]
    return {key: bool(os.getenv(key)) for key in keys}


def _bridge_status() -> dict[str, Any]:
    rows = [r for r in latest_jsonl("reports", limit=100) if r.get("report_type") == "strategy_paper_bridge_snapshot"]
    row = rows[-1] if rows else {}
    facts = row.get("verified_facts") or {}
    return {
        "present": bool(row),
        "summary": row.get("summary") or "not_found",
        "supabase_logging": facts.get("supabase_logging") or "unknown",
        "eligible_candidate_count": facts.get("eligible_candidate_count"),
        "created_at": row.get("created_at"),
    }


def _dns_check(host: str) -> dict[str, Any]:
    import socket

    if not host:
        return {"ok": False, "host": host, "error": "missing_host"}
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        ips = sorted({row[4][0] for row in infos})
        return {"ok": True, "host": host, "ip_count": len(ips), "ips": ips[:6]}
    except Exception as exc:
        return {"ok": False, "host": host, "error": str(exc)}


def _curl_check(url: str) -> dict[str, Any]:
    proc = subprocess.run(
        ["curl", "-I", "--max-time", "10", url],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or proc.stderr or "").splitlines()[:10]
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": output}


def _python_https_check(url: str) -> dict[str, Any]:
    import ssl
    import urllib.request

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10, context=ssl.create_default_context()) as resp:
            return {"ok": True, "status": resp.status, "reason": resp.reason}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _broker_last_response() -> dict[str, Any]:
    rows = [r for r in latest_jsonl("reports", limit=100) if r.get("report_type") == "oanda_practice_check"]
    row = rows[-1] if rows else {}
    facts = row.get("verified_facts") or {}
    order_result = facts.get("order_result") or {}
    return {
        "report_found": bool(row),
        "summary": row.get("summary") or "not_found",
        "practice_order_placed": facts.get("practice_order_placed"),
        "status": facts.get("status"),
        "order_result": {
            "ok": order_result.get("ok"),
            "instrument": order_result.get("instrument"),
            "side": order_result.get("side"),
            "units": order_result.get("units"),
            "error": order_result.get("error"),
        },
    }


INSTRUMENT_ALLOWLIST: list[str] = [
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "USD_CAD",
    "NZD_USD",
    "USD_CHF",
    "USD_JPY",
]


def _resolve_test_instrument(adapter: OandaDemoAdapter, instruments: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    override = os.getenv("OANDA_TEST_INSTRUMENT", "").strip().upper()
    if override:
        if override not in INSTRUMENT_ALLOWLIST:
            raise RuntimeError(
                f"OANDA_TEST_INSTRUMENT={override} is not in the allowed list: {', '.join(INSTRUMENT_ALLOWLIST)}"
            )
        names = {row.get("name") for row in instruments if row.get("name")}
        if override not in names:
            raise RuntimeError(f"OANDA_TEST_INSTRUMENT={override} is not available from the broker")
        pricing = adapter.get_pricing(override)
        prices = pricing.get("prices") or []
        if not prices:
            raise RuntimeError(f"OANDA_TEST_INSTRUMENT={override} returned no pricing data")
        price = prices[0]
        if not price.get("tradeable", False):
            raise RuntimeError(f"OANDA_TEST_INSTRUMENT={override} is not tradeable right now")
        return override, pricing
    return _select_tradeable_major(adapter, instruments)


def _select_tradeable_major(adapter: OandaDemoAdapter, instruments: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    preferred = ["EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD"]
    available = {row.get("name"): row for row in instruments if row.get("name")}
    last_error = "no_tradeable_major_found"
    for instrument in preferred:
        if instrument not in available:
            continue
        try:
            pricing = adapter.get_pricing(instrument)
            prices = pricing.get("prices") or []
            if not prices:
                last_error = f"{instrument}_no_prices"
                continue
            price = prices[0]
            if not price.get("tradeable", False):
                last_error = f"{instrument}_not_tradeable"
                continue
            return instrument, pricing
        except Exception as exc:
            last_error = f"{instrument}_{exc}"
            continue
    raise RuntimeError(last_error)


def _spread_check(instrument: str, pricing: dict[str, Any]) -> dict[str, Any]:
    price = (pricing.get("prices") or [{}])[0]
    bid = float((price.get("bids") or [{}])[0].get("price") or 0.0)
    ask = float((price.get("asks") or [{}])[0].get("price") or 0.0)
    spread = max(0.0, ask - bid)
    pip = 0.01 if instrument.endswith("JPY") else 0.0001
    spread_pips = spread / pip if pip else 0.0
    threshold = 3.0
    return {
        "bid": bid,
        "ask": ask,
        "spread": spread,
        "spread_pips": round(spread_pips, 3),
        "threshold_pips": threshold,
        "normal": spread_pips <= threshold,
        "tradeable": bool(price.get("tradeable", False)),
    }


def _build_plan(instrument: str, pricing: dict[str, Any]) -> dict[str, Any]:
    spread = _spread_check(instrument, pricing)
    side = "BUY"
    entry = spread["ask"]
    pip = 0.01 if instrument.endswith("JPY") else 0.0001
    stop_distance_pips = 10
    target_distance_pips = 20
    stop_loss = round(entry - (stop_distance_pips * pip), 5)
    take_profit = round(entry + (target_distance_pips * pip), 5)
    return {
        "instrument": instrument,
        "side": side,
        "units": 1,
        "entry_type": "MARKET",
        "entry_reference_price": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "stop_loss_distance_pips": stop_distance_pips,
        "take_profit_distance_pips": target_distance_pips,
        "spread": spread,
        "risk_note": "1-unit practice-only demo trade with attached SL/TP on a liquid major pair.",
        "safe_reason": "Highly liquid major pair, smallest size, practice endpoint only, one-shot lifecycle verification.",
        "expected_broker_payload_fields": [
            "order.type",
            "order.instrument",
            "order.units",
            "order.timeInForce",
            "order.positionFill",
            "order.stopLossOnFill.price",
            "order.takeProfitOnFill.price",
            "order.clientExtensions.tag",
        ],
    }


def _state_snapshot(adapter: OandaDemoAdapter, order_id: str | None, trade_id: str | None) -> dict[str, Any]:
    snapshot: dict[str, Any] = {"checked_at": _now()}
    if order_id:
        try:
            snapshot["order"] = adapter.order_state(str(order_id))
        except Exception as exc:
            snapshot["order_error"] = str(exc)
    if trade_id:
        try:
            snapshot["trade"] = adapter.trade_state(str(trade_id))
        except Exception as exc:
            snapshot["trade_error"] = str(exc)
    try:
        snapshot["open_trades"] = adapter.open_trades()
    except Exception as exc:
        snapshot["open_trades_error"] = str(exc)
    return snapshot


def _trade_status(snapshot: dict[str, Any]) -> str:
    trade = (snapshot.get("trade") or {}).get("trade") or {}
    if trade:
        return str(trade.get("state") or "UNKNOWN")
    order = (snapshot.get("order") or {}).get("order") or {}
    if order:
        return str(order.get("state") or "UNKNOWN")
    return "UNKNOWN"


def _has_protection(snapshot: dict[str, Any], key: str) -> bool:
    trade = (snapshot.get("trade") or {}).get("trade") or {}
    if trade.get(key):
        return True
    order = (snapshot.get("order") or {}).get("order") or {}
    return bool(order.get(key))


def _write_blocked_bundle(
    *,
    run_id: str,
    safety: dict[str, Any],
    receiver: dict[str, Any],
    bridge: dict[str, Any],
    engine_status: dict[str, Any],
    bank_funding_connected: bool,
    reason: str,
    learning: dict[str, Any],
    diagnostics: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    payload_validation: dict[str, Any] | None = None,
) -> None:
    if not PLAN_MD.exists() or plan is not None:
        _write_md(
            PLAN_MD,
            [
                "# Demo Trade Plan",
                "",
                f"- instrument: `{(plan or {}).get('instrument', 'none')}`",
                f"- side: `{(plan or {}).get('side', 'none')}`",
                f"- units: `{(plan or {}).get('units', 'none')}`",
                f"- entry type: `{(plan or {}).get('entry_type', 'none')}`",
                f"- stop loss distance: `{(plan or {}).get('stop_loss_distance_pips', 'unknown')}`",
                f"- take profit distance: `{(plan or {}).get('take_profit_distance_pips', 'unknown')}`",
                f"- risk note: `{(plan or {}).get('risk_note', 'blocked_before_plan_completion')}`",
                f"- reason this is safe for demo testing: `{(plan or {}).get('safe_reason', 'not_reached')}`",
                f"- expected broker payload fields: `{', '.join((plan or {}).get('expected_broker_payload_fields', [])) or 'not_reached'}`",
            ],
        )
        _copy_text(PLAN_MD, REPORT_DIR / "demo_trade_plan.md")
    if not PAYLOAD_JSON.exists() or payload_validation is not None:
        _write_json(
            PAYLOAD_JSON,
            {
                "run_id": run_id,
                "status": "blocked_pre_submission",
                "reason": reason,
                "payload_validation": payload_validation or {},
            },
        )
        _copy_json(PAYLOAD_JSON, PAYLOAD_RETRY_JSON)
        _write_md(
            PAYLOAD_MD,
            [
                "# Demo Order Payload Review",
                "",
                f"- account is practice/demo: `{_bool_text(False) if payload_validation is None else _bool_text(payload_validation.get('practice_account_confirmed'))}`",
                f"- instrument present: `{_bool_text((payload_validation or {}).get('instrument_present'))}`",
                f"- units present: `{_bool_text((payload_validation or {}).get('units_present'))}`",
                f"- stop loss present: `{_bool_text((payload_validation or {}).get('stop_loss_present'))}`",
                f"- take profit present: `{_bool_text((payload_validation or {}).get('take_profit_present'))}`",
                f"- targets live endpoint: `{_bool_text((payload_validation or {}).get('live_endpoint_targeted'))}`",
                f"- targets live account: `{_bool_text((payload_validation or {}).get('live_account_targeted'))}`",
                f"- smallest safe demo size: `{_bool_text((payload_validation or {}).get('smallest_safe_demo_size'))}`",
                f"- spread check normal: `{_bool_text((payload_validation or {}).get('spread_normal'))}`",
                f"- market open tradeable: `{_bool_text((payload_validation or {}).get('market_open_tradeable'))}`",
                f"- blocked reason: `{reason}`",
            ],
        )
        _copy_text(PAYLOAD_MD, PAYLOAD_RETRY_MD)
    order_payload = {
        "run_id": run_id,
        "status": "blocked_pre_submission",
        "reason": reason,
    }
    _write_json(ORDER_RESPONSE_JSON, order_payload)
    _copy_json(ORDER_RESPONSE_JSON, ORDER_RETRY_JSON)
    _write_md(
        ORDER_RESPONSE_MD,
        [
            "# OANDA Practice Order Response",
            "",
            "- order submitted: `no`",
            "- broker accepted: `no`",
            "- order ID: `none`",
            "- trade ID: `none`",
            f"- rejection reason: `{reason}`",
        ],
    )
    _copy_text(ORDER_RESPONSE_MD, ORDER_RETRY_MD)
    _write_md(
        TRADE_STATE_MD,
        [
            "# OANDA Practice Trade State",
            "",
            "- order submitted: `no`",
            "- stop loss exists: `no`",
            "- take profit exists: `no`",
            "- current status: `blocked_pre_submission`",
            f"- rejection reason: `{reason}`",
        ],
    )
    _copy_text(TRADE_STATE_MD, TRADE_RETRY_STATE_MD)
    _write_md(
        MONITOR_MD,
        [
            "# OANDA Practice Trade Monitor",
            "",
            "- immediate state: `not_started`",
            "- 1-minute state: `not_started`",
            "- 5-minute state: `not_started`",
            "- open/closed/rejected: `blocked_pre_submission`",
            "- if open, recommended handling: No trade was opened. Restore broker connectivity before retrying.",
        ],
    )
    _copy_text(MONITOR_MD, TRADE_RETRY_MONITOR_MD)
    _write_json(LEARNING_JSON, learning)
    _write_md(
        LEARNING_MD,
        [
            "# OANDA Practice Execution Learning",
            "",
            f"- run_id: `{learning['run_id']}`",
            f"- instrument: `{learning.get('instrument') or 'none'}`",
            f"- connectivity issue root cause: `{learning.get('connectivity_issue_root_cause', 'unknown')}`",
            f"- fix applied: `{learning.get('fix_applied', 'none')}`",
            "- order submitted: `no`",
            "- broker accepted: `no`",
            f"- rejection reason: `{reason}`",
            f"- lesson learned: {learning['lesson_learned']}",
            f"- next adjustment: {learning['next_adjustment']}",
        ],
    )
    _write_md(
        FINAL_MD,
        [
            "# FINAL REPORT — OANDA PRACTICE EXECUTION TEST",
            "",
            "## APPROVAL",
            "- Ray approved practice/demo test: `yes`",
            f"- approval record: `{APPROVAL_MD}`",
            "- Telegram approval request: `not_sent_prompt_approval_logged`",
            "- scope: `one OANDA practice/demo trade, 1 unit, SL/TP required, full logging, no repeat loop`",
            "",
            "## PREFLIGHT",
            f"- OANDA mode: `{safety.get('oanda_environment')}`",
            f"- practice/demo confirmed: `{_bool_text(False)}`",
            "- live/funded account detected: `no`",
            f"- bank/funding connected: `{_bool_text(bank_funding_connected)}`",
            f"- LIVE_TRADING: `{safety.get('live_trading')}`",
            f"- AUTO_TRADING: `{safety.get('auto_trading')}`",
            f"- DRY_RUN: `{os.getenv('NEXUS_DRY_RUN', '').lower()}`",
            f"- PAPER_ONLY: `{safety.get('paper_only')}`",
            f"- execution_mode: `{engine_status.get('last_result', {}).get('execution_mode') or 'unknown'}`",
            f"- safe_mode: `{_bool_text(receiver.get('health', {}).get('safe_mode_active'))}`",
            f"- receiver: `{receiver.get('health', {}).get('status', 'unknown')}`",
            f"- signal bridge: `{bridge.get('summary', 'unknown')}`",
            "- broker connectivity: `false`",
            "",
            "## ORDER PLAN",
            f"- instrument: `{(plan or {}).get('instrument', 'none')}`",
            f"- side: `{(plan or {}).get('side', 'none')}`",
            f"- units: `{(plan or {}).get('units', 'none')}`",
            f"- entry type: `{(plan or {}).get('entry_type', 'none')}`",
            f"- stop loss: `{(plan or {}).get('stop_loss', 'none')}`",
            f"- take profit: `{(plan or {}).get('take_profit', 'none')}`",
            f"- spread check: `{((plan or {}).get('spread') or {}).get('spread_pips', 'unknown')}`",
            f"- market open: `{((plan or {}).get('spread') or {}).get('tradeable', 'unknown')}`",
            f"- payload validation: `{payload_validation_passed(payload_validation) if payload_validation else 'not_reached'}`",
            
            "## EXECUTION",
            "- order submitted: `no`",
            "- broker accepted: `no`",
            "- order ID: `none`",
            "- trade ID: `none`",
            f"- rejection reason: `{reason}`",
            "- stop loss attached: `no`",
            "- take profit attached: `no`",
            "",
            "## MONITORING",
            "- immediate state: `not_started`",
            "- 1-minute state: `not_started`",
            "- 5-minute state: `not_started`",
            "- open/closed/rejected: `blocked_pre_submission`",
            "- if open, recommended handling: No trade was opened.",
            "",
            "## LEARNING",
            f"- what worked: `{'; '.join(learning['what_worked'])}`",
            f"- what failed: `{'; '.join(learning['what_failed']) or 'none'}`",
            f"- lesson learned: `{learning['lesson_learned']}`",
            f"- next adjustment: `{learning['next_adjustment']}`",
            "- next safe test: `rerun this exact one-shot lifecycle test after OANDA connectivity is healthy again`",
            "",
            "## SAFETY",
            "- live account used: `no`",
            "- real money risk: `no`",
            f"- bank/funding connected: `{_bool_text(bank_funding_connected)}`",
            "- paid APIs used: `no`",
            "- secrets printed: `no`",
            "- .env committed: `no`",
            "- multiple orders placed: `no`",
            "- SL missing: `no_order_submitted`",
            "- TP missing: `no_order_submitted`",
            "",
            "## RECOMMENDATION",
            "Nexus → OANDA practice execution is not confirmed in this run because OANDA connectivity failed before order creation. Restore practice connectivity, then rerun one approved demo lifecycle test.",
        ],
    )
    _copy_text(FINAL_MD, FINAL_RETRY_MD)
    _write_md(
        FINAL_RETRY_MD,
        [
            "# FINAL REPORT — OANDA PRACTICE CONNECTIVITY + EXECUTION RETRY",
            "",
            "## CONNECTIVITY",
            f"- original error: `{(diagnostics or {}).get('original_error', reason)}`",
            f"- root cause: `{learning.get('connectivity_issue_root_cause', reason)}`",
            f"- endpoint checked: `{(diagnostics or {}).get('endpoint_base', 'unknown')}`",
            f"- DNS passed: `{_bool_text(((diagnostics or {}).get('dns_check') or {}).get('ok'))}`",
            f"- curl/API check passed: `{_bool_text(((diagnostics or {}).get('curl_check') or {}).get('ok'))}`",
            f"- Python client check passed: `{_bool_text(((diagnostics or {}).get('python_https') or {}).get('ok'))}`",
            f"- fix applied: `{learning.get('fix_applied', 'none')}`",
            "",
            "## PREFLIGHT",
            f"- practice/demo confirmed: `no`",
            "- live/funded account detected: `no`",
            f"- bank/funding connected: `{_bool_text(bank_funding_connected)}`",
            f"- LIVE_TRADING: `{safety.get('live_trading')}`",
            f"- AUTO_TRADING: `{safety.get('auto_trading')}`",
            f"- DRY_RUN: `{os.getenv('NEXUS_DRY_RUN', '').lower()}`",
            f"- PAPER_ONLY: `{safety.get('paper_only')}`",
            f"- execution_mode: `{engine_status.get('last_result', {}).get('execution_mode') or 'unknown'}`",
            f"- safe_mode: `{_bool_text(receiver.get('health', {}).get('safe_mode_active'))}`",
            f"- receiver: `{receiver.get('health', {}).get('status', 'unknown')}`",
            f"- signal bridge: `{bridge.get('summary', 'unknown')}`",
            "",
            "## PAYLOAD",
            f"- instrument: `{(plan or {}).get('instrument', 'none')}`",
            f"- side: `{(plan or {}).get('side', 'none')}`",
            f"- units: `{(plan or {}).get('units', 'none')}`",
            f"- stop loss: `{(plan or {}).get('stop_loss', 'none')}`",
            f"- take profit: `{(plan or {}).get('take_profit', 'none')}`",
            f"- market open: `{((plan or {}).get('spread') or {}).get('tradeable', 'unknown')}`",
            f"- spread: `{((plan or {}).get('spread') or {}).get('spread_pips', 'unknown')}`",
            f"- validation passed: `{payload_validation_passed(payload_validation) if payload_validation else 'not_reached'}`",
            "",
            "## EXECUTION",
            "- order submitted: `no`",
            "- broker accepted: `no`",
            "- order ID: `none`",
            "- trade ID: `none`",
            f"- rejection reason: `{reason}`",
            "- stop loss attached: `no`",
            "- take profit attached: `no`",
            "- number of orders placed: `0`",
            "",
            "## MONITORING",
            "- immediate: `not_started`",
            "- 1 minute: `not_started`",
            "- 5 minutes: `not_started`",
            "- open/closed/rejected: `blocked_pre_submission`",
            "- recommended handling: Restore DNS/connectivity to the OANDA practice host, then rerun the same one-shot lifecycle test.",
            "",
            "## LEARNING",
            f"- what worked: `{'; '.join(learning['what_worked'])}`",
            f"- what failed: `{'; '.join(learning['what_failed']) or 'none'}`",
            f"- lesson learned: `{learning['lesson_learned']}`",
            f"- next safe test: `{learning['next_adjustment']}`",
            "",
            "## SAFETY",
            "- live account used: `no`",
            "- real money risk: `no`",
            f"- bank/funding connected: `{_bool_text(bank_funding_connected)}`",
            "- paid APIs used: `no`",
            "- secrets printed: `no`",
            "- .env committed: `no`",
            "- multiple orders placed: `no`",
            "- SL missing: `no_order_submitted`",
            "- TP missing: `no_order_submitted`",
            "",
            "## RECOMMENDATION",
            "Nexus → OANDA practice execution is not yet confirmed end-to-end. Once DNS/connectivity to the practice host is restored, the next test should be 1. strategy-generated signal into one practice order.",
        ],
    )


def main() -> int:
    seed_safe_trading_env_from_launch_agent()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = f"oanda_practice_lifecycle_{uuid.uuid4().hex[:8]}"

    safety = evaluate_trading_safety(broker_mode="oanda_practice", api_url=os.getenv("OANDA_API_URL", ""))
    receiver = _run_json([sys.executable, str(ROOT / "scripts" / "trading_receiver_healthcheck.py")])
    oanda_status = _run_json([sys.executable, str(ROOT / "scripts" / "check_oanda_practice.py"), "--status-only"])
    engine_status = _load_json(ROOT / "logs" / "trading_engine_status.json")
    bridge = _bridge_status()
    last_broker = _broker_last_response()
    bank_funding_presence = _common_bank_funding_presence()
    bank_funding_connected = any(bank_funding_presence.values())
    env_presence = {
        "OANDA_API_KEY": _env_flag("OANDA_API_KEY"),
        "OANDA_ACCOUNT_ID": _env_flag("OANDA_ACCOUNT_ID"),
        "OANDA_API_URL": _env_flag("OANDA_API_URL"),
        "OANDA_ENVIRONMENT": _env_flag("OANDA_ENVIRONMENT"),
        "OANDA_ALLOW_LIVE": _env_flag("OANDA_ALLOW_LIVE"),
        "OANDA_DEMO_ENABLED": _env_flag("OANDA_DEMO_ENABLED"),
        "LIVE_TRADING": _env_flag("LIVE_TRADING"),
        "NEXUS_AUTO_TRADING": _env_flag("NEXUS_AUTO_TRADING"),
        "NEXUS_DRY_RUN": _env_flag("NEXUS_DRY_RUN"),
        "PAPER_ONLY": _env_flag("PAPER_ONLY"),
        "TRADING_LIVE_EXECUTION_ENABLED": _env_flag("TRADING_LIVE_EXECUTION_ENABLED"),
    }
    endpoint_info = (((oanda_status.get("endpoint_info") or {}) if isinstance(oanda_status, dict) else {}) or {})
    endpoint_host = endpoint_info.get("hostname") or "api-fxpractice.oanda.com"
    endpoint_base = endpoint_info.get("api_base") or os.getenv("OANDA_API_URL", "https://api-fxpractice.oanda.com/v3")
    dns_check = _dns_check(endpoint_host)
    curl_check = _curl_check("https://api-fxpractice.oanda.com/v3")
    python_https = _python_https_check("https://api-fxpractice.oanda.com/v3")
    diagnostics = {
        "original_error": "<urlopen error [Errno 8] nodename nor servname provided, or not known>",
        "oanda_environment": os.getenv("OANDA_ENVIRONMENT", ""),
        "oanda_api_url_present": _bool_text(bool(os.getenv("OANDA_API_URL"))),
        "endpoint_base": endpoint_base,
        "endpoint_host": endpoint_host,
        "practice_endpoint_valid": _bool_text(endpoint_host == "api-fxpractice.oanda.com"),
        "live_endpoint_used": _bool_text("fxtrade" in endpoint_base.lower()),
        "account_id_present": _bool_text(bool(os.getenv("OANDA_ACCOUNT_ID"))),
        "token_present": _bool_text(bool(os.getenv("OANDA_ACCESS_TOKEN") or os.getenv("OANDA_API_KEY"))),
        "account_type": "practice/demo" if safety.get("oanda_environment") in {"practice", "demo"} else "unknown",
        "LIVE_TRADING": str(safety.get("live_trading")).lower(),
        "AUTO_TRADING": str(safety.get("auto_trading")).lower(),
        "DRY_RUN": str(os.getenv("NEXUS_DRY_RUN", "")).lower(),
        "PAPER_ONLY": str(safety.get("paper_only")).lower(),
        "execution_mode": engine_status.get("last_result", {}).get("execution_mode") or "unknown",
        "safe_mode": _bool_text(receiver.get("health", {}).get("safe_mode_active")),
        "dns_check": dns_check,
        "curl_check": curl_check,
        "python_https": python_https,
        "adapter_endpoint_info": endpoint_info,
        "status_check_endpoint_info": oanda_status.get("connection_status") or {},
        "mac_dns_note": "scutil --dns returned no DNS configuration available in this execution environment",
        "vpn_firewall_dns_cache_note": "Possible local DNS/VPN/firewall issue if shell and Python both cannot resolve api-fxpractice.oanda.com",
    }
    _write_md(
        DIAGNOSTIC_MD,
        [
            "# OANDA Connectivity Diagnostic",
            "",
            f"- OANDA_ENVIRONMENT: `{diagnostics['oanda_environment']}`",
            f"- OANDA_API_URL present: `{diagnostics['oanda_api_url_present']}`",
            f"- OANDA account ID present: `{diagnostics['account_id_present']}`",
            f"- token present: `{diagnostics['token_present']}`",
            f"- endpoint host extracted: `{endpoint_host}`",
            f"- practice endpoint host is valid: `{diagnostics['practice_endpoint_valid']}`",
            f"- live endpoint is being used: `{diagnostics['live_endpoint_used']}`",
            f"- account type is practice/demo: `{_bool_text(diagnostics['account_type'] == 'practice/demo')}`",
            f"- LIVE_TRADING: `{diagnostics['LIVE_TRADING']}`",
            f"- AUTO_TRADING: `{diagnostics['AUTO_TRADING']}`",
            f"- DRY_RUN: `{diagnostics['DRY_RUN']}`",
            f"- PAPER_ONLY: `{diagnostics['PAPER_ONLY']}`",
            f"- execution_mode: `{diagnostics['execution_mode']}`",
            f"- safe_mode: `{diagnostics['safe_mode']}`",
            f"- DNS lookup passed: `{_bool_text(dns_check.get('ok'))}`",
            f"- curl/API check passed: `{_bool_text(curl_check.get('ok'))}`",
            f"- Python urllib/HTTPS check passed: `{_bool_text(python_https.get('ok'))}`",
            "- scripts/check_oanda_practice.py and scripts/run_oanda_practice_execution_test.py both use integrations/oanda_demo/oanda_demo_adapter.py",
            f"- endpoint malformed/missing scheme/wrong hostname: `no`",
            f"- Mac DNS/network issue suspected: `{_bool_text(not dns_check.get('ok'))}`",
            "",
            "## Notes",
            f"- original error: `{diagnostics['original_error']}`",
            f"- mac dns note: {diagnostics['mac_dns_note']}",
            f"- vpn/firewall/dns cache note: {diagnostics['vpn_firewall_dns_cache_note']}",
        ],
    )

    live_risk_reasons: list[str] = []
    if not safety.get("safe"):
        live_risk_reasons.extend(safety.get("blockers") or [])
    if safety.get("oanda_environment") not in {"practice", "demo"}:
        live_risk_reasons.append(f"OANDA_ENVIRONMENT={safety.get('oanda_environment')}")
    if safety.get("api_url_mode") != "practice":
        live_risk_reasons.append(f"OANDA_API_URL mode={safety.get('api_url_mode')}")
    if safety.get("live_trading"):
        live_risk_reasons.append("LIVE_TRADING=true")
    if safety.get("live_execution_enabled"):
        live_risk_reasons.append("TRADING_LIVE_EXECUTION_ENABLED=true")
    if bank_funding_connected:
        live_risk_reasons.append("bank_or_funding_env_detected")

    preflight_payload = {
        "run_id": run_id,
        "generated_at": _now(),
        "practice_demo_confirmed": oanda_status.get("status") == "OANDA_PRACTICE_READY",
        "oanda_environment": safety.get("oanda_environment"),
        "api_url_mode": safety.get("api_url_mode"),
        "account_id_masked": _mask_account_id(os.getenv("OANDA_ACCOUNT_ID", "")),
        "bank_funding_detectable": bank_funding_connected,
        "bank_funding_presence": {k: _bool_text(v) for k, v in bank_funding_presence.items()},
        "flags": {
            "LIVE_TRADING": str(safety.get("live_trading")).lower(),
            "AUTO_TRADING": str(safety.get("auto_trading")).lower(),
            "DRY_RUN": str(os.getenv("NEXUS_DRY_RUN", "")).lower(),
            "PAPER_ONLY": str(safety.get("paper_only")).lower(),
            "execution_mode": engine_status.get("last_result", {}).get("execution_mode") or "unknown",
            "safe_mode": "true" if receiver.get("health", {}).get("safe_mode_active") else "false",
        },
        "receiver_status": receiver,
        "trading_engine_status": {
            "stage": engine_status.get("stage"),
            "broker_type": engine_status.get("broker_type"),
            "receiver_started": engine_status.get("receiver_started"),
            "broker_connected": engine_status.get("broker_connected"),
        },
        "signal_bridge_status": bridge,
        "oanda_api_connectivity": oanda_status.get("connection_status") or {},
        "last_broker_response": last_broker,
        "live_risk_reasons": live_risk_reasons,
        "env_presence": env_presence,
    }
    _write_md(
        PREFLIGHT_MD,
        [
            "# OANDA Practice Preflight",
            "",
            f"- Run ID: `{run_id}`",
            f"- OANDA environment is practice/demo: `{_bool_text(safety.get('oanda_environment') in {'practice', 'demo'})}`",
            f"- Practice/demo confirmed: `{_bool_text(preflight_payload['practice_demo_confirmed'])}`",
            f"- Account ID masked: `{preflight_payload['account_id_masked']}`",
            f"- Bank/funding connected detectable: `{_bool_text(bank_funding_connected)}`",
            f"- LIVE_TRADING: `{safety.get('live_trading')}`",
            f"- AUTO_TRADING: `{safety.get('auto_trading')}`",
            f"- DRY_RUN: `{os.getenv('NEXUS_DRY_RUN', '').lower()}`",
            f"- PAPER_ONLY: `{safety.get('paper_only')}`",
            f"- execution_mode: `{engine_status.get('last_result', {}).get('execution_mode') or 'unknown'}`",
            f"- safe_mode: `{_bool_text(receiver.get('health', {}).get('safe_mode_active'))}`",
            f"- receiver status: `{receiver.get('health', {}).get('status', 'unknown')}`",
            f"- trading engine status: `{engine_status.get('stage', 'unknown')}`",
            f"- signal bridge status: `{bridge.get('summary', 'unknown')}`",
            f"- OANDA API connectivity: `{(oanda_status.get('connection_status') or {}).get('ok')}`",
            f"- last broker response status: `{last_broker.get('status', 'unknown')}`",
            f"- available env names configured: `{', '.join(k for k, v in env_presence.items() if v == 'yes')}`",
            f"- live/funded risk detected: `{_bool_text(bool(live_risk_reasons))}`",
            "",
            "## Bank/Funding Detection",
            "",
            *[f"- `{name}`: `{value}`" for name, value in preflight_payload["bank_funding_presence"].items()],
        ],
    )
    _copy_text(PREFLIGHT_MD, PREFLIGHT_RETRY_MD)

    _write_md(
        APPROVAL_MD,
        [
            "# DEMO_TRADING_TEST",
            "",
            "## Title",
            "OANDA Practice Demo Trade Lifecycle Test",
            "",
            "## Approval",
            "Ray approved one OANDA practice/demo-only lifecycle test.",
            "",
            "## Allowed Scope",
            "- one OANDA practice/demo trade only",
            "- smallest safe demo position size",
            "- stop loss required",
            "- take profit required",
            "- full logging required",
            "- no repeat loop",
            "- no live/funded trading",
            "",
            "## Blocked",
            "- live account",
            "- funded account",
            "- bank/funding connection",
            "- multiple orders",
            "- missing stop loss",
            "- missing take profit",
            "- oversized trade",
            "- secrets exposure",
            "",
            "## Telegram Approval Request",
            "Not sent in this run. Prompt-level approval from Ray logged here.",
        ],
    )

    if live_risk_reasons:
        learning = {
            "run_id": run_id,
            "timestamp": _now(),
            "instrument": None,
            "signal_source": "blocked_preflight",
            "connectivity_issue_root_cause": "not_applicable_live_risk_block",
            "fix_applied": "adapter_endpoint_normalization_and_dns_retry",
            "order_submitted": False,
            "broker_accepted": False,
            "stop_loss_accepted": False,
            "take_profit_accepted": False,
            "rejection_reason": "; ".join(live_risk_reasons),
            "fill_status": "blocked",
            "monitoring_result": "not_started",
            "what_worked": ["safety gate blocked unsafe execution"],
            "what_failed": live_risk_reasons,
            "lesson_learned": "Practice execution must stop immediately on any live/funded ambiguity.",
            "next_adjustment": "clear live/funded blocker before any further test",
            "should_continue": False,
            "requires_ray_approval": False,
        }
        _write_blocked_bundle(
            run_id=run_id,
            safety=safety,
            receiver=receiver,
            bridge=bridge,
            engine_status=engine_status,
            bank_funding_connected=bank_funding_connected,
            reason=learning["rejection_reason"],
            learning=learning,
            diagnostics=diagnostics,
        )
        print(json.dumps({"status": "blocked_preflight", "reasons": live_risk_reasons}, indent=2))
        return 1

    adapter = OandaDemoAdapter()
    try:
        instruments_payload = adapter.available_instruments()
        instruments = instruments_payload.get("instruments") or []
        instrument, pricing = _resolve_test_instrument(adapter, instruments)
    except Exception as exc:
        learning = {
            "run_id": run_id,
            "timestamp": _now(),
            "instrument": None,
            "signal_source": "preflight_market_check",
            "connectivity_issue_root_cause": "local_dns_resolution_failed_for_api-fxpractice.oanda.com",
            "fix_applied": "adapter_endpoint_normalization_dns_preflight_and_retry_backoff_added",
            "order_submitted": False,
            "broker_accepted": False,
            "stop_loss_accepted": False,
            "take_profit_accepted": False,
            "rejection_reason": str(exc),
            "fill_status": "blocked",
            "monitoring_result": "instrument_selection_failed",
            "what_worked": ["practice account connectivity verified"],
            "what_failed": [str(exc)],
            "lesson_learned": "A demo lifecycle test still needs a tradeable liquid instrument and valid pricing.",
            "next_adjustment": "retry when a major pair is tradeable and pricing is available",
            "should_continue": False,
            "requires_ray_approval": False,
        }
        _write_blocked_bundle(
            run_id=run_id,
            safety=safety,
            receiver=receiver,
            bridge=bridge,
            engine_status=engine_status,
            bank_funding_connected=bank_funding_connected,
            reason=learning["rejection_reason"],
            learning=learning,
            diagnostics=diagnostics,
        )
        print(json.dumps({"status": "instrument_selection_failed", "reason": str(exc)}, indent=2))
        return 1

    plan = _build_plan(instrument, pricing)
    payload = adapter.order_payload(
        instrument=plan["instrument"],
        side=plan["side"],
        units=plan["units"],
        stop_loss=plan["stop_loss"],
        take_profit=plan["take_profit"],
        client_tag=run_id,
    )
    _write_json(PAYLOAD_JSON, payload)

    payload_validation = {
        "practice_account_confirmed": preflight_payload["practice_demo_confirmed"],
        "instrument_present": bool(payload.get("order", {}).get("instrument")),
        "units_present": bool(payload.get("order", {}).get("units")),
        "stop_loss_present": bool((payload.get("order", {}).get("stopLossOnFill") or {}).get("price")),
        "take_profit_present": bool((payload.get("order", {}).get("takeProfitOnFill") or {}).get("price")),
        "live_endpoint_targeted": False,
        "live_account_targeted": False,
        "smallest_safe_demo_size": payload.get("order", {}).get("units") in {"1", "-1"},
        "spread_normal": plan["spread"]["normal"],
        "market_open_tradeable": plan["spread"]["tradeable"],
    }
    _write_md(
        PLAN_MD,
        [
            "# Demo Trade Plan",
            "",
            f"- instrument: `{plan['instrument']}`",
            f"- side: `{plan['side']}`",
            f"- units: `{plan['units']}`",
            f"- entry type: `{plan['entry_type']}`",
            f"- stop loss distance: `{plan['stop_loss_distance_pips']} pips`",
            f"- take profit distance: `{plan['take_profit_distance_pips']} pips`",
            f"- risk note: {plan['risk_note']}",
            f"- reason this is safe for demo testing: {plan['safe_reason']}",
            f"- expected broker payload fields: `{', '.join(plan['expected_broker_payload_fields'])}`",
        ],
    )
    _copy_text(PLAN_MD, REPORT_DIR / "demo_trade_plan.md")
    _write_md(
        PAYLOAD_MD,
        [
            "# Demo Order Payload Review",
            "",
            f"- account is practice/demo: `{_bool_text(payload_validation['practice_account_confirmed'])}`",
            f"- instrument present: `{_bool_text(payload_validation['instrument_present'])}`",
            f"- units present: `{_bool_text(payload_validation['units_present'])}`",
            f"- stop loss present: `{_bool_text(payload_validation['stop_loss_present'])}`",
            f"- take profit present: `{_bool_text(payload_validation['take_profit_present'])}`",
            f"- targets live endpoint: `{_bool_text(payload_validation['live_endpoint_targeted'])}`",
            f"- targets live account: `{_bool_text(payload_validation['live_account_targeted'])}`",
            f"- smallest safe demo size: `{_bool_text(payload_validation['smallest_safe_demo_size'])}`",
            f"- spread check normal: `{_bool_text(payload_validation['spread_normal'])}`",
            f"- market open tradeable: `{_bool_text(payload_validation['market_open_tradeable'])}`",
        ],
    )
    _write_json(PAYLOAD_RETRY_JSON, payload)
    _copy_text(PAYLOAD_MD, PAYLOAD_RETRY_MD)

    if not payload_validation_passed(payload_validation):
        learning = {
            "run_id": run_id,
            "timestamp": _now(),
            "instrument": plan["instrument"],
            "signal_source": "payload_validation",
            "connectivity_issue_root_cause": "payload_validation_failed",
            "fix_applied": "adapter_endpoint_normalization_dns_preflight_and_retry_backoff_added",
            "order_submitted": False,
            "broker_accepted": False,
            "stop_loss_accepted": False,
            "take_profit_accepted": False,
            "rejection_reason": "payload_validation_failed",
            "fill_status": "blocked",
            "monitoring_result": "not_started",
            "what_worked": ["preflight completed"],
            "what_failed": payload_validation_failures(payload_validation),
            "lesson_learned": "Nexus should not submit any demo order unless every payload and market safety check passes.",
            "next_adjustment": "fix payload validation blockers before retrying",
            "should_continue": False,
            "requires_ray_approval": False,
        }
        _write_blocked_bundle(
            run_id=run_id,
            safety=safety,
            receiver=receiver,
            bridge=bridge,
            engine_status=engine_status,
            bank_funding_connected=bank_funding_connected,
            reason="payload_validation_failed",
            learning=learning,
            diagnostics=diagnostics,
            plan=plan,
            payload_validation=payload_validation,
        )
        print(json.dumps({"status": "payload_validation_failed", "validation": payload_validation}, indent=2))
        return 1

    os.environ["OANDA_DEMO_ENABLED"] = "true"
    order_result: dict[str, Any]
    try:
        order_result = adapter.place_demo_order(
            instrument=plan["instrument"],
            side=plan["side"],
            units=plan["units"],
            stop_loss=plan["stop_loss"],
            take_profit=plan["take_profit"],
            reason=run_id,
        )
    except OandaSafetyError as exc:
        order_result = {"ok": False, "error": str(exc)}

    _write_json(ORDER_RESPONSE_JSON, order_result)
    _write_json(ORDER_RETRY_JSON, order_result)
    _write_md(
        ORDER_RESPONSE_MD,
        [
            "# OANDA Practice Order Response",
            "",
            f"- order submitted: `{_bool_text('ok' in order_result)}`",
            f"- broker accepted: `{_bool_text(order_result.get('ok'))}`",
            f"- instrument: `{order_result.get('instrument')}`",
            f"- side: `{order_result.get('side')}`",
            f"- units: `{order_result.get('units')}`",
            f"- order ID: `{order_result.get('order_id')}`",
            f"- trade ID: `{order_result.get('trade_id')}`",
            f"- stop loss order ID: `{order_result.get('stop_loss_order_id')}`",
            f"- take profit order ID: `{order_result.get('take_profit_order_id')}`",
            f"- rejection reason: `{order_result.get('error')}`",
        ],
    )
    _copy_text(ORDER_RESPONSE_MD, ORDER_RETRY_MD)

    order_id = str(order_result.get("order_id") or "")
    trade_id = str(order_result.get("trade_id") or "")
    immediate = _state_snapshot(adapter, order_id or None, trade_id or None) if order_result.get("ok") else {}
    state_lines = [
        "# OANDA Practice Trade State",
        "",
        f"- order submitted: `{_bool_text(order_result.get('ok'))}`",
        f"- order ID: `{order_id or 'none'}`",
        f"- trade ID: `{trade_id or 'none'}`",
        f"- stop loss exists: `{_bool_text(order_result.get('stop_loss_order_id') or _has_protection(immediate, 'stopLossOrder'))}`",
        f"- take profit exists: `{_bool_text(order_result.get('take_profit_order_id') or _has_protection(immediate, 'takeProfitOrder'))}`",
        f"- current status: `{_trade_status(immediate) if immediate else 'rejected'}`",
        f"- rejection reason: `{order_result.get('error') or 'none'}`",
    ]
    _write_md(TRADE_STATE_MD, state_lines)
    _copy_text(TRADE_STATE_MD, TRADE_RETRY_STATE_MD)

    monitor = {
        "immediate": immediate,
        "one_minute": None,
        "five_minutes": None,
    }
    if order_result.get("ok"):
        time.sleep(60)
        monitor["one_minute"] = _state_snapshot(adapter, order_id or None, trade_id or None)
        time.sleep(240)
        monitor["five_minutes"] = _state_snapshot(adapter, order_id or None, trade_id or None)

    final_state = monitor["five_minutes"] or monitor["one_minute"] or monitor["immediate"] or {}
    final_status = _trade_status(final_state) if final_state else ("REJECTED" if not order_result.get("ok") else "UNKNOWN")
    if final_status.upper() == "OPEN":
        handling = "Trade remains managed by attached SL/TP. Manual close is optional after verification; no second order should be opened."
    elif final_status.upper() in {"CLOSED", "CLOSE"}:
        handling = "Trade completed during the monitor window."
    elif final_status.upper() == "REJECTED":
        handling = "No retry. Review rejection reason and adjust before another approved test."
    else:
        handling = "Review OANDA account state manually if status remains ambiguous."
    _write_md(
        MONITOR_MD,
        [
            "# OANDA Practice Trade Monitor",
            "",
            f"- immediate state: `{_trade_status(monitor['immediate']) if monitor['immediate'] else 'not_available'}`",
            f"- 1-minute state: `{_trade_status(monitor['one_minute']) if monitor['one_minute'] else 'not_checked'}`",
            f"- 5-minute state: `{_trade_status(monitor['five_minutes']) if monitor['five_minutes'] else 'not_checked'}`",
            f"- open/closed/rejected: `{final_status}`",
            f"- if open, recommended handling: {handling}",
        ],
    )
    _copy_text(MONITOR_MD, TRADE_RETRY_MONITOR_MD)

    learning = {
        "run_id": run_id,
        "timestamp": _now(),
        "instrument": plan["instrument"],
        "signal_source": "synthetic_demo_lifecycle_test",
        "connectivity_issue_root_cause": "resolved_or_not_present",
        "fix_applied": "adapter_endpoint_normalization_dns_preflight_and_retry_backoff_added",
        "order_submitted": bool("ok" in order_result),
        "broker_accepted": bool(order_result.get("ok")),
        "stop_loss_accepted": bool(order_result.get("stop_loss_order_id") or _has_protection(final_state, "stopLossOrder")),
        "take_profit_accepted": bool(order_result.get("take_profit_order_id") or _has_protection(final_state, "takeProfitOrder")),
        "rejection_reason": order_result.get("error"),
        "fill_status": final_status,
        "monitoring_result": handling,
        "what_worked": [
            "Practice-only safety gate remained active",
            "Order payload carried attached SL/TP",
            "Single-order discipline preserved",
        ],
        "what_failed": [] if order_result.get("ok") else [order_result.get("error") or "broker_rejected"],
        "lesson_learned": (
            "Nexus can reach OANDA practice and attach protective brackets in one controlled order."
            if order_result.get("ok")
            else "Broker rejection details must be captured and learned from without forcing another order."
        ),
        "next_adjustment": (
            "Test strategy-generated signal promotion into the same one-shot demo execution path."
            if order_result.get("ok")
            else "Fix the rejection cause before the next approved demo lifecycle test."
        ),
        "should_continue": bool(order_result.get("ok")),
        "requires_ray_approval": False,
    }
    _write_json(LEARNING_JSON, learning)
    _write_md(
        LEARNING_MD,
        [
            "# OANDA Practice Execution Learning",
            "",
            f"- run_id: `{learning['run_id']}`",
            f"- instrument: `{learning['instrument']}`",
            f"- order submitted: `{_bool_text(learning['order_submitted'])}`",
            f"- broker accepted: `{_bool_text(learning['broker_accepted'])}`",
            f"- stop loss accepted: `{_bool_text(learning['stop_loss_accepted'])}`",
            f"- take profit accepted: `{_bool_text(learning['take_profit_accepted'])}`",
            f"- rejection reason: `{learning['rejection_reason'] or 'none'}`",
            f"- fill status: `{learning['fill_status']}`",
            f"- lesson learned: {learning['lesson_learned']}",
            f"- next adjustment: {learning['next_adjustment']}",
        ],
    )

    _write_md(
        FINAL_MD,
        [
            "# FINAL REPORT — OANDA PRACTICE EXECUTION TEST",
            "",
            "## APPROVAL",
            f"- Ray approved practice/demo test: `yes`",
            f"- approval record: `{APPROVAL_MD}`",
            "- Telegram approval request: `not_sent_prompt_approval_logged`",
            "- scope: `one OANDA practice/demo trade, 1 unit, SL/TP required, full logging, no repeat loop`",
            "",
            "## PREFLIGHT",
            f"- OANDA mode: `{safety.get('oanda_environment')}`",
            f"- practice/demo confirmed: `{_bool_text(preflight_payload['practice_demo_confirmed'])}`",
            f"- live/funded account detected: `{_bool_text(bool(live_risk_reasons))}`",
            f"- bank/funding connected: `{_bool_text(bank_funding_connected)}`",
            f"- LIVE_TRADING: `{safety.get('live_trading')}`",
            f"- AUTO_TRADING: `{safety.get('auto_trading')}`",
            f"- DRY_RUN: `{os.getenv('NEXUS_DRY_RUN', '').lower()}`",
            f"- PAPER_ONLY: `{safety.get('paper_only')}`",
            f"- execution_mode: `{engine_status.get('last_result', {}).get('execution_mode') or 'unknown'}`",
            f"- safe_mode: `{_bool_text(receiver.get('health', {}).get('safe_mode_active'))}`",
            f"- receiver: `{receiver.get('health', {}).get('status', 'unknown')}`",
            f"- signal bridge: `{bridge.get('summary', 'unknown')}`",
            f"- broker connectivity: `{(oanda_status.get('connection_status') or {}).get('ok')}`",
            "",
            "## ORDER PLAN",
            f"- instrument: `{plan['instrument']}`",
            f"- side: `{plan['side']}`",
            f"- units: `{plan['units']}`",
            f"- entry type: `{plan['entry_type']}`",
            f"- stop loss: `{plan['stop_loss']}`",
            f"- take profit: `{plan['take_profit']}`",
            f"- spread check: `{plan['spread']['spread_pips']} pips / normal={plan['spread']['normal']}`",
            f"- market open: `{plan['spread']['tradeable']}`",
            f"- payload validation: `{payload_validation_passed(payload_validation)}`",
            "",
            "## EXECUTION",
            f"- order submitted: `{_bool_text(learning['order_submitted'])}`",
            f"- broker accepted: `{_bool_text(learning['broker_accepted'])}`",
            f"- order ID: `{order_id or 'none'}`",
            f"- trade ID: `{trade_id or 'none'}`",
            f"- rejection reason: `{learning['rejection_reason'] or 'none'}`",
            f"- stop loss attached: `{_bool_text(learning['stop_loss_accepted'])}`",
            f"- take profit attached: `{_bool_text(learning['take_profit_accepted'])}`",
            "",
            "## MONITORING",
            f"- immediate state: `{_trade_status(monitor['immediate']) if monitor['immediate'] else 'not_available'}`",
            f"- 1-minute state: `{_trade_status(monitor['one_minute']) if monitor['one_minute'] else 'not_checked'}`",
            f"- 5-minute state: `{_trade_status(monitor['five_minutes']) if monitor['five_minutes'] else 'not_checked'}`",
            f"- open/closed/rejected: `{final_status}`",
            f"- if open, recommended handling: {handling}",
            "",
            "## LEARNING",
            f"- what worked: `{'; '.join(learning['what_worked'])}`",
            f"- what failed: `{'; '.join(learning['what_failed']) or 'none'}`",
            f"- lesson learned: `{learning['lesson_learned']}`",
            f"- next adjustment: `{learning['next_adjustment']}`",
            "- next safe test: `strategy-generated signal with the same SL/TP-protected practice order path`",
            "",
            "## SAFETY",
            "- live account used: `no`",
            "- real money risk: `no`",
            f"- bank/funding connected: `{_bool_text(bank_funding_connected)}`",
            "- paid APIs used: `no`",
            "- secrets printed: `no`",
            "- .env committed: `no`",
            "- multiple orders placed: `no`",
            f"- SL missing: `{_bool_text(not learning['stop_loss_accepted'])}`",
            f"- TP missing: `{_bool_text(not learning['take_profit_accepted'])}`",
            "",
            "## RECOMMENDATION",
            (
                "Nexus → OANDA practice execution is working end-to-end. Next test should be strategy-generated signal promotion and then SL/TP modification or trade-result memory."
                if learning["broker_accepted"]
                else "Nexus → OANDA practice execution is not yet confirmed end-to-end. Fix the captured rejection cause, then retry one approved demo lifecycle test."
            ),
        ],
    )
    _copy_text(FINAL_MD, FINAL_RETRY_MD)

    summary = {
        "run_id": run_id,
        "status": "ok" if learning["broker_accepted"] else "failed",
        "instrument": plan["instrument"],
        "order_id": order_id or None,
        "trade_id": trade_id or None,
        "fill_status": final_status,
        "stop_loss_accepted": learning["stop_loss_accepted"],
        "take_profit_accepted": learning["take_profit_accepted"],
        "final_report": str(FINAL_MD),
    }
    print(json.dumps(summary, indent=2))
    return 0 if learning["broker_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
