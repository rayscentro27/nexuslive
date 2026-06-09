from __future__ import annotations

import os
import plistlib
from pathlib import Path
from typing import Any


SAFE_BROKER_MODES = {
    "demo",
    "paper",
    "practice",
    "broker_demo",
    "local_paper",
    "oanda_practice",
}

LAUNCH_AGENT = Path.home() / "Library" / "LaunchAgents" / "com.nexus.trading-engine.plist"
SYNC_ENV_NAMES = (
    "BROKER_TYPE",
    "LIVE_TRADING",
    "NEXUS_AUTO_TRADING",
    "NEXUS_DRY_RUN",
    "PAPER_ONLY",
    "TRADING_LIVE_EXECUTION_ENABLED",
    "OANDA_ENVIRONMENT",
    "OANDA_ALLOW_LIVE",
    "OANDA_DEMO_ENABLED",
    "OANDA_API_URL",
    "OANDA_ACCOUNT_ID",
    "OANDA_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_ANON_KEY",
)


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def seed_safe_trading_env_from_launch_agent() -> None:
    """Use the local LaunchAgent file as the safety source of truth when present."""
    if not LAUNCH_AGENT.exists():
        return
    try:
        payload = plistlib.loads(LAUNCH_AGENT.read_bytes())
        env = (payload.get("EnvironmentVariables") or {}) if isinstance(payload, dict) else {}
        for name in SYNC_ENV_NAMES:
            value = env.get(name)
            if value is not None:
                os.environ[name] = str(value)
    except Exception:
        return


def evaluate_trading_safety(*, broker_mode: str | None = None, api_url: str | None = None) -> dict[str, Any]:
    seed_safe_trading_env_from_launch_agent()
    live_trading = _flag("LIVE_TRADING", "false")
    live_execution_enabled = _flag("TRADING_LIVE_EXECUTION_ENABLED", "false")
    dry_run_requested = _flag("NEXUS_DRY_RUN", "true")
    paper_only = _flag("PAPER_ONLY", "true")
    auto_trading = _flag("NEXUS_AUTO_TRADING", "false")
    oanda_env = (os.getenv("OANDA_ENVIRONMENT", "practice") or "practice").strip().lower()
    oanda_allow_live = _flag("OANDA_ALLOW_LIVE", "false")
    effective_broker_mode = (broker_mode or os.getenv("BROKER_TYPE", "demo") or "demo").strip().lower()
    effective_api_url = (api_url or os.getenv("OANDA_API_URL", "") or "").strip().lower()
    effective_dry_run = dry_run_requested or not live_execution_enabled

    blockers: list[str] = []
    if live_trading:
        blockers.append("LIVE_TRADING=true")
    if live_execution_enabled:
        blockers.append("TRADING_LIVE_EXECUTION_ENABLED=true")
    if not paper_only:
        blockers.append("PAPER_ONLY=false")
    if effective_broker_mode not in SAFE_BROKER_MODES:
        blockers.append(f"unsafe broker mode: {effective_broker_mode or 'missing'}")
    if effective_broker_mode.startswith("oanda") or "oanda" in effective_api_url:
        if oanda_env not in {"practice", "demo"}:
            blockers.append(f"OANDA_ENVIRONMENT={oanda_env}")
        if oanda_allow_live:
            blockers.append("OANDA_ALLOW_LIVE=true")
        if "fxtrade" in effective_api_url:
            blockers.append("live OANDA endpoint detected")

    return {
        "safe": len(blockers) == 0 and effective_dry_run,
        "effective_dry_run": effective_dry_run,
        "paper_only": paper_only,
        "live_trading": live_trading,
        "live_execution_enabled": live_execution_enabled,
        "auto_trading": auto_trading,
        "broker_mode": effective_broker_mode,
        "oanda_environment": oanda_env,
        "oanda_allow_live": oanda_allow_live,
        "api_url_mode": "practice" if "fxpractice" in effective_api_url else "live" if "fxtrade" in effective_api_url else "n/a",
        "blockers": blockers,
    }


def assert_safe_for_execution(*, broker_mode: str | None = None, api_url: str | None = None) -> dict[str, Any]:
    status = evaluate_trading_safety(broker_mode=broker_mode, api_url=api_url)
    if not status["safe"]:
        raise RuntimeError("Trading safety gate blocked execution: " + "; ".join(status["blockers"]))
    return status
