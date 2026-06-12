#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import plistlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCH_AGENT = Path.home() / "Library" / "LaunchAgents" / "com.nexus.trading-engine.plist"
OUTPUT_JSON = ROOT / "logs" / "oanda_practice_status_latest.json"
sys.path.insert(0, str(ROOT))

from integrations.oanda_demo import OandaDemoAdapter
from integrations.oanda_demo.oanda_demo_adapter import OandaSafetyError
from lib.trading_fallback_logger import append_jsonl
from lib.trading_safety_gate import evaluate_trading_safety


REQUIRED_ENV_NAMES = [
    "OANDA_API_KEY",
    "OANDA_ACCOUNT_ID",
    "OANDA_API_URL",
    "OANDA_ENVIRONMENT",
    "OANDA_ALLOW_LIVE",
    "OANDA_DEMO_ENABLED",
    "LIVE_TRADING",
    "PAPER_ONLY",
    "NEXUS_DRY_RUN",
    "TRADING_LIVE_EXECUTION_ENABLED",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _demo_brackets(adapter: OandaDemoAdapter, instrument: str, side: str) -> tuple[float, float]:
    pricing = adapter.get_pricing(instrument)
    prices = pricing.get("prices") or []
    price = prices[0] if prices else {}
    bid = float((price.get("bids") or [{}])[0].get("price") or 0.0)
    ask = float((price.get("asks") or [{}])[0].get("price") or 0.0)
    entry = ask if side.lower() == "buy" else bid
    pip = 0.0001 if instrument != "USD_JPY" else 0.01
    if side.lower() == "buy":
        return round(entry - (10 * pip), 5), round(entry + (20 * pip), 5)
    return round(entry + (10 * pip), 5), round(entry - (20 * pip), 5)


def env_presence() -> dict[str, bool]:
    return {name: bool(os.getenv(name)) for name in REQUIRED_ENV_NAMES}


def seed_env_from_launch_agent() -> None:
    if not LAUNCH_AGENT.exists():
        return
    try:
        payload = plistlib.loads(LAUNCH_AGENT.read_bytes())
        env = (payload.get("EnvironmentVariables") or {}) if isinstance(payload, dict) else {}
        for name in REQUIRED_ENV_NAMES:
            if not os.getenv(name) and env.get(name):
                os.environ[name] = str(env[name])
    except Exception:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status-only", action="store_true", help="Check practice connectivity and safety without placing any order.")
    parser.add_argument("--place-test-order", action="store_true", help="Place a 1-unit practice test order after checks pass.")
    args = parser.parse_args()
    if args.status_only and args.place_test_order:
        parser.error("--status-only and --place-test-order are mutually exclusive")

    seed_env_from_launch_agent()
    safety = evaluate_trading_safety(broker_mode="oanda_practice", api_url=os.getenv("OANDA_API_URL", ""))
    presence = env_presence()
    place_test_order = bool(args.place_test_order)
    report: dict[str, object] = {
        "checked_at": _now(),
        "status": "OANDA_PRACTICE_BLOCKED",
        "mode": "place_test_order" if place_test_order else "status_only",
        "env_presence": presence,
        "safety_gate": safety,
        "practice_endpoint_configured": "fxpractice" in (os.getenv("OANDA_API_URL", "").lower()),
        "practice_connection_verified": False,
        "practice_order_placed": False,
        "fallback_mode": "local_paper",
        "blocker": None,
    }

    if not all(presence.values()):
        report["blocker"] = "Missing required OANDA env names"
        OUTPUT_JSON.write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        append_jsonl("reports", {
            "created_at": _now(),
            "report_type": "oanda_practice_check",
            "mode": "paper",
            "receiver_status": "n/a",
            "broker_status": "blocked",
            "live_trading_enabled": False,
            "paper_trading_enabled": True,
            "summary": report["status"],
            "blockers": [report["blocker"]],
            "verified_facts": report,
        })
        return 2

    if not safety["safe"]:
        report["blocker"] = "; ".join(safety["blockers"])
        OUTPUT_JSON.write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        append_jsonl("reports", {
            "created_at": _now(),
            "report_type": "oanda_practice_check",
            "mode": "paper",
            "receiver_status": "n/a",
            "broker_status": "blocked",
            "live_trading_enabled": False,
            "paper_trading_enabled": True,
            "summary": report["status"],
            "blockers": safety["blockers"],
            "verified_facts": report,
        })
        return 2

    try:
        adapter = OandaDemoAdapter()
        report["endpoint_info"] = adapter.practice_endpoint_info()
        status = adapter.connection_status()
        report["connection_status"] = {
            "ok": bool(status.get("ok")),
            "environment": status.get("environment"),
            "api_base": status.get("api_base"),
            "endpoint_host": status.get("endpoint_host"),
            "currency": status.get("currency"),
            "balance_available": bool(status.get("balance")),
            "nav_available": bool(status.get("nav")),
            "dns_preflight": status.get("dns_preflight"),
            "error": status.get("error"),
        }
        if not status.get("ok"):
            report["blocker"] = status.get("error") or "Practice connection failed"
            OUTPUT_JSON.write_text(json.dumps(report, indent=2))
            print(json.dumps(report, indent=2))
            append_jsonl("reports", {
                "created_at": _now(),
                "report_type": "oanda_practice_check",
                "mode": "paper",
                "receiver_status": "n/a",
                "broker_status": "blocked",
                "live_trading_enabled": False,
                "paper_trading_enabled": True,
                "summary": report["status"],
                "blockers": [report["blocker"]],
                "verified_facts": report,
            })
            return 2
        report["practice_connection_verified"] = True
    except OandaSafetyError as exc:
        report["blocker"] = str(exc)
        OUTPUT_JSON.write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        append_jsonl("reports", {
            "created_at": _now(),
            "report_type": "oanda_practice_check",
            "mode": "paper",
            "receiver_status": "n/a",
            "broker_status": "blocked",
            "live_trading_enabled": False,
            "paper_trading_enabled": True,
            "summary": report["status"],
            "blockers": [report["blocker"]],
            "verified_facts": report,
        })
        return 2

    if report["practice_connection_verified"] and not place_test_order:
        report["status"] = "OANDA_PRACTICE_READY"
        report["fallback_mode"] = "not_needed"

    demo_enabled = os.getenv("OANDA_DEMO_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    if report["practice_connection_verified"] and place_test_order:
        try:
            if not demo_enabled:
                os.environ["OANDA_DEMO_ENABLED"] = "true"
            stop_loss, take_profit = _demo_brackets(adapter, "EUR_USD", "buy")
            order = adapter.place_demo_order(
                instrument="EUR_USD",
                side="buy",
                units=1,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason="nexus_oanda_practice_check",
            )
            report["practice_order_placed"] = bool(order.get("ok"))
            report["order_result"] = {
                "ok": bool(order.get("ok")),
                "environment": order.get("environment"),
                "instrument": order.get("instrument"),
                "side": order.get("side"),
                "units": order.get("units"),
                "placed_at": order.get("placed_at"),
                "error": order.get("error"),
            }
            if order.get("ok"):
                report["status"] = "OANDA_PRACTICE_READY"
                report["fallback_mode"] = "not_needed"
            else:
                report["blocker"] = order.get("error") or "Practice order failed"
        except OandaSafetyError as exc:
            report["blocker"] = str(exc)

    append_jsonl("reports", {
        "created_at": _now(),
        "report_type": "oanda_practice_check",
        "mode": "paper",
        "receiver_status": "n/a",
        "broker_status": "ready" if report["practice_connection_verified"] else "blocked",
        "live_trading_enabled": False,
        "paper_trading_enabled": True,
        "summary": report["status"],
        "blockers": [report["blocker"]] if report.get("blocker") else [],
        "verified_facts": report,
    })
    OUTPUT_JSON.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "OANDA_PRACTICE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
