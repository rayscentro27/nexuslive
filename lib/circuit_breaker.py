"""
circuit_breaker.py — Nexus Trading Circuit Breaker System

Implements unconditional trading halts. Circuit breakers override all strategy
logic, AI signals, and operator preferences until manually reset or timer expires.

This module is read/write for system events and read-only for Hermes.
Only the operator can reset circuit breakers (except auto-reset types).
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_FILE = Path(__file__).resolve().parent.parent / ".circuit_breaker_state.json"

# Circuit breaker trigger types and their reset modes
BREAKER_CONFIG = {
    "daily_loss_exceeded": {
        "auto_reset": True,
        "auto_reset_hours": 24,
        "description": "Daily loss limit exceeded",
        "halt_all": True,
    },
    "weekly_drawdown_exceeded": {
        "auto_reset": True,
        "auto_reset_hours": 168,  # 1 week
        "description": "Weekly drawdown limit exceeded",
        "halt_all": True,
    },
    "consecutive_losses": {
        "auto_reset": True,
        "auto_reset_hours": 4,
        "description": "Consecutive loss threshold breached",
        "halt_all": False,  # strategy-level only
    },
    "volatility_spike": {
        "auto_reset": True,
        "auto_reset_hours": 0.5,  # 30 min
        "description": "Volatility spike — ATR > 3x normal",
        "halt_all": False,
    },
    "api_failure": {
        "auto_reset": False,
        "description": "API failure or latency > 2s",
        "halt_all": True,
    },
    "slippage_anomaly": {
        "auto_reset": False,
        "description": "Slippage > 3x expected — manual review required",
        "halt_all": True,
    },
    "abnormal_pnl": {
        "auto_reset": False,
        "description": "Abnormal P&L swing detected — positions frozen",
        "halt_all": True,
    },
    "operator_halt": {
        "auto_reset": False,
        "description": "Manual halt by operator",
        "halt_all": True,
    },
    "market_gap": {
        "auto_reset": True,
        "auto_reset_hours": 0,  # immediate — just skip the trade
        "description": "Market gap > 1% — skip trade",
        "halt_all": False,
    },
}


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"active_breakers": {}, "history": []}


def _save_state(state: dict) -> None:
    try:
        _STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except Exception as e:
        logger.error(f"circuit_breaker: failed to save state: {e}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fire(
    trigger_type: str,
    trigger_value: float | None = None,
    strategy_id: str | None = None,
    notes: str = "",
) -> dict:
    """
    Fire a circuit breaker.
    Returns the event dict. Caller is responsible for alerting Hermes.
    """
    if trigger_type not in BREAKER_CONFIG:
        raise ValueError(f"Unknown circuit breaker type: {trigger_type}")

    config = BREAKER_CONFIG[trigger_type]
    state = _load_state()

    event = {
        "id": f"{trigger_type}_{_now_iso()}",
        "trigger_type": trigger_type,
        "trigger_value": trigger_value,
        "strategy_id": strategy_id,
        "triggered_at": _now_iso(),
        "resolved": False,
        "resolved_at": None,
        "resolved_by": None,
        "auto_reset": config["auto_reset"],
        "auto_reset_hours": config.get("auto_reset_hours"),
        "halt_all": config["halt_all"],
        "description": config["description"],
        "notes": notes,
    }

    key = f"{trigger_type}:{strategy_id or 'global'}"
    state["active_breakers"][key] = event
    state["history"].append(event)
    # Keep history to last 100 events
    state["history"] = state["history"][-100:]
    _save_state(state)

    logger.warning(
        f"CIRCUIT BREAKER FIRED: {trigger_type} | value={trigger_value} | strategy={strategy_id}"
    )
    return event


def reset(
    trigger_type: str,
    strategy_id: str | None = None,
    resolved_by: str = "operator",
    notes: str = "",
) -> bool:
    """
    Reset a specific circuit breaker. Returns True if found and reset.
    Automated systems cannot reset circuit breakers (use resolved_by='operator').
    """
    state = _load_state()
    key = f"{trigger_type}:{strategy_id or 'global'}"

    if key not in state["active_breakers"]:
        return False

    event = state["active_breakers"][key]
    event["resolved"] = True
    event["resolved_at"] = _now_iso()
    event["resolved_by"] = resolved_by
    if notes:
        event["notes"] = (event.get("notes") or "") + f" | Reset: {notes}"

    # Update in history too
    for h in state["history"]:
        if h.get("id") == event.get("id"):
            h.update({"resolved": True, "resolved_at": event["resolved_at"],
                       "resolved_by": resolved_by})
            break

    del state["active_breakers"][key]
    _save_state(state)
    logger.info(f"Circuit breaker reset: {trigger_type} | by={resolved_by}")
    return True


def reset_all(resolved_by: str = "operator") -> int:
    """Reset all active circuit breakers. Returns count reset."""
    state = _load_state()
    count = len(state["active_breakers"])
    now = _now_iso()
    for key, event in state["active_breakers"].items():
        event.update({"resolved": True, "resolved_at": now, "resolved_by": resolved_by})
    state["active_breakers"] = {}
    _save_state(state)
    logger.info(f"All circuit breakers reset by {resolved_by} ({count} cleared)")
    return count


def check_auto_resets() -> list[str]:
    """
    Check all active breakers for expired auto-reset timers.
    Returns list of trigger types that were auto-reset.
    Only breakers with auto_reset=True and auto_reset_hours > 0 are eligible.
    """
    state = _load_state()
    reset_keys = []
    now = datetime.now(timezone.utc)

    for key, event in list(state["active_breakers"].items()):
        if not event.get("auto_reset"):
            continue
        hours = event.get("auto_reset_hours", 0)
        if hours <= 0:
            continue
        triggered = datetime.fromisoformat(event["triggered_at"])
        if (now - triggered) >= timedelta(hours=hours):
            reset_keys.append(key)

    for key in reset_keys:
        event = state["active_breakers"].pop(key)
        event.update({"resolved": True, "resolved_at": now.isoformat(),
                       "resolved_by": "auto"})
        logger.info(f"Circuit breaker auto-reset: {event['trigger_type']}")

    if reset_keys:
        _save_state(state)

    return [k.split(":")[0] for k in reset_keys]


def is_halted(strategy_id: str | None = None) -> bool:
    """
    Check if any active circuit breaker blocks trading.
    Returns True if trading should be halted.
    """
    if os.getenv("NEXUS_DRY_RUN", "true").lower() == "true":
        return False  # dry run always allows — circuit breakers don't apply to paper dry-run checks

    state = _load_state()
    if not state["active_breakers"]:
        return False

    for key, event in state["active_breakers"].items():
        if event.get("halt_all"):
            return True
        # Strategy-specific halt
        if strategy_id and event.get("strategy_id") == strategy_id:
            return True

    return False


def get_status() -> dict:
    """Return full circuit breaker status for Hermes and dashboard."""
    state = _load_state()
    check_auto_resets()  # clear expired ones
    state = _load_state()  # reload after auto-reset

    active = list(state["active_breakers"].values())
    return {
        "any_active": len(active) > 0,
        "halt_all": any(e.get("halt_all") for e in active),
        "active_count": len(active),
        "active_breakers": active,
        "recent_history": state["history"][-10:],
    }
