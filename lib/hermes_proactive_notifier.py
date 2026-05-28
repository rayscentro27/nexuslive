"""
Hermes Proactive Telegram Notifier
Sends scheduled / event-driven status updates to Ray when he is away.
Uses hermes_gate.send() for all Telegram sends (never bypasses the gate).
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

NOTIFY_LOG = Path("docs/reports/hermes_proactive_notifications.jsonl")
NOTIFY_LOG.parent.mkdir(parents=True, exist_ok=True)

# Notification urgency levels → hermes_gate function mapping
_URGENCY_MAP = {
    "critical": "send_critical",
    "warning":  "send_warning",
    "summary":  "send_summary",
    "info":     "send_on_demand",
    "recovery": "send_recovery",
}


def _gate_send(text: str, urgency: str, event_type: str) -> bool:
    try:
        from lib import hermes_gate as gate
        fn = getattr(gate, _URGENCY_MAP.get(urgency, "send_on_demand"))
        return fn(text, event_type)
    except Exception as e:
        _log_notification(text, urgency, event_type, sent=False, error=str(e))
        return False


def _log_notification(text: str, urgency: str, event_type: str, sent: bool, error: str = "") -> None:
    record = {
        "sent_at":    datetime.utcnow().isoformat() + "Z",
        "urgency":    urgency,
        "event_type": event_type,
        "sent":       sent,
        "error":      error,
        "preview":    text[:120],
    }
    with open(NOTIFY_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")


class HermesProactiveNotifier:
    """
    Compose and send structured proactive Telegram messages to Ray.
    """

    def notify_cycle_complete(
        self,
        run_id: str,
        products: list[str],
        errors: list[str],
        runtime_min: float,
    ) -> bool:
        product_list = "\n".join(f"  ✅ {p}" for p in products) or "  (none)"
        error_list   = "\n".join(f"  ⚠️ {e}" for e in errors)  or "  (none)"
        text = (
            f"<b>Nexus Cycle Complete</b>\n"
            f"Run: <code>{run_id}</code>\n"
            f"Runtime: {runtime_min:.1f}min\n\n"
            f"<b>Products:</b>\n{product_list}\n\n"
        )
        if errors:
            text += f"<b>Errors:</b>\n{error_list}\n"
        urgency = "warning" if errors else "summary"
        sent = _gate_send(text, urgency, "cycle_complete")
        _log_notification(text, urgency, "cycle_complete", sent)
        return sent

    def notify_compliance_flag(self, strategy_name: str, status: str, reason: str) -> bool:
        text = (
            f"<b>⚠️ Compliance Flag</b>\n"
            f"Strategy: <i>{strategy_name}</i>\n"
            f"Status: <code>{status}</code>\n"
            f"Reason: {reason}"
        )
        sent = _gate_send(text, "warning", "compliance_flag")
        _log_notification(text, "warning", "compliance_flag", sent)
        return sent

    def notify_handoff_created(self, handoff_id: str, title: str, urgency: str = "normal") -> bool:
        text = (
            f"<b>Action Required</b>\n"
            f"Handoff: <code>{handoff_id}</code>\n"
            f"<b>{title}</b>\n"
            f"Check Nexus → hermes handoffs"
        )
        gate_urgency = "warning" if urgency in ("high", "critical") else "info"
        sent = _gate_send(text, gate_urgency, "handoff_created")
        _log_notification(text, gate_urgency, "handoff_created", sent)
        return sent

    def notify_error(self, component: str, error: str, run_id: str = "") -> bool:
        text = (
            f"<b>❌ Nexus Error</b>\n"
            f"Component: <code>{component}</code>\n"
            f"Run: <code>{run_id}</code>\n"
            f"Error: {error[:300]}"
        )
        sent = _gate_send(text, "critical", "nexus_error")
        _log_notification(text, "critical", "nexus_error", sent)
        return sent

    def notify_demo_order(self, instrument: str, side: str, units: int, ok: bool, detail: str = "") -> bool:
        status = "✅ Filled" if ok else "❌ Failed"
        text = (
            f"<b>OANDA Demo Order — {status}</b>\n"
            f"Instrument: <code>{instrument}</code>\n"
            f"Side: {side} | Units: {units} | Environment: practice\n"
        )
        if detail:
            text += f"Detail: {detail[:200]}"
        urgency = "info" if ok else "warning"
        sent = _gate_send(text, urgency, "demo_order")
        _log_notification(text, urgency, "demo_order", sent)
        return sent

    def notify_content_ready(self, platform: str, score: float, artifact_name: str) -> bool:
        text = (
            f"<b>Content Ready for Review</b>\n"
            f"Platform: {platform}\n"
            f"Score: {score:.1f}/100\n"
            f"File: <code>{artifact_name}</code>"
        )
        sent = _gate_send(text, "info", "content_ready")
        _log_notification(text, "info", "content_ready", sent)
        return sent

    def notify_custom(self, text: str, urgency: str = "info", event_type: str = "custom") -> bool:
        sent = _gate_send(text, urgency, event_type)
        _log_notification(text, urgency, event_type, sent)
        return sent

    def recent_notifications(self, n: int = 20) -> list[dict[str, Any]]:
        if not NOTIFY_LOG.exists():
            return []
        lines = NOTIFY_LOG.read_text().strip().splitlines()
        result = []
        for line in lines[-n:]:
            try:
                result.append(json.loads(line))
            except Exception:
                pass
        return result


# ── Singleton ──────────────────────────────────────────────────────────────────
_notifier = HermesProactiveNotifier()


def notify_cycle_complete(run_id: str, products: list[str], errors: list[str], runtime_min: float) -> bool:
    return _notifier.notify_cycle_complete(run_id, products, errors, runtime_min)


def notify_error(component: str, error: str, run_id: str = "") -> bool:
    return _notifier.notify_error(component, error, run_id)


def notify_handoff(handoff_id: str, title: str, urgency: str = "normal") -> bool:
    return _notifier.notify_handoff_created(handoff_id, title, urgency)


def notify_custom(text: str, urgency: str = "info") -> bool:
    return _notifier.notify_custom(text, urgency)
