from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

# Evidence gating — NO ARTIFACT = NO CLAIM
try:
    from lib.hermes_evidence_mode import (
        is_fake_trading_claim as _is_fake_trading,
        has_theatrical_language as _has_theatrical,
    )
    _EVIDENCE_GATING = True
except ImportError:
    _EVIDENCE_GATING = False
    def _is_fake_trading(t: str) -> bool: return False  # type: ignore[misc]
    def _has_theatrical(t: str) -> bool: return False  # type: ignore[misc]


ROUTE_CHAT = "chat"
ROUTE_COMMAND = "command"
ROUTE_DAILY_PLAN = "daily_plan"
ROUTE_TASK_SELECTION = "task_selection"
ROUTE_APPROVAL = "approval"
ROUTE_COMPLETION_NOTICE = "completion_notice"
ROUTE_REPORT_REQUEST = "report_request"
ROUTE_FUNDING_INSIGHTS = "funding_insights"
ROUTE_CREDIT_INSIGHTS = "credit_insights"
ROUTE_KNOWLEDGE_REPORT = "knowledge_report"
# ── Strategic operating partner routes (Part 12) ────────────────────────────��─
ROUTE_NEXUS_STATUS    = "nexus_status"       # "catch me up", "where are we"
ROUTE_STRATEGIC_CHAT  = "strategic_chat"     # open-ended strategic question
ROUTE_HANDOFF_CHECK   = "handoff_check"      # "what needs my approval", "pending handoffs"
ROUTE_DECISION_LOG    = "decision_log"       # "what did Hermes decide"
ROUTE_DEMO_STATUS     = "demo_status"        # "OANDA demo status", "last demo order"
ROUTE_PREMIUM_BLOCKER = "premium_blocker"    # "free alternative to Beehiiv"
ROUTE_SAVE_FEEDBACK   = "save_feedback"      # "record lesson", "remember this"

# Patterns that trigger each strategic route (checked before classify_message_route)
_STRATEGIC_PATTERNS: list[tuple[str, str]] = [
    (r"catch me up|where are we|are we on track|what did nexus produce|what happened since", ROUTE_NEXUS_STATUS),
    (r"pending handoff|what.*approv|waiting.*on me|what.*need.*sign", ROUTE_HANDOFF_CHECK),
    (r"what.*hermes.*decid|decision log|hermes.*own decision", ROUTE_DECISION_LOG),
    (r"oanda|demo.*order|demo.*broker|last.*trade.*demo", ROUTE_DEMO_STATUS),
    (r"beehiiv.*alternative|premium.*blocker|free.*alternative.*to\s+\w+|replace.*beehiiv", ROUTE_PREMIUM_BLOCKER),
    (r"record lesson|remember this|save.*feedback|save.*lesson", ROUTE_SAVE_FEEDBACK),
]


@dataclass
class TelegramRouter:
    classify_message_route: Callable
    handle_command_mode: Callable
    build_daily_plan: Callable
    task_selection_reply: Callable
    handle_approval_reply: Callable
    risky_action_requested: Callable
    conversational_reply: Callable
    report_email: Callable
    send_report_email: Callable
    report_confirmation: Callable
    funding_insights_reply: Callable
    credit_insights_reply: Callable
    knowledge_report_email: Callable
    knowledge_report_confirmation: Callable
    help_text: Callable
    email_reports_enabled: Callable
    full_reports_enabled: Callable
    report_response: Callable
    approval_request_response: Callable
    chat_response: Callable
    model_error_response: Callable | None = None
    # ── Strategic operating partner handlers (optional — default to None) ──────
    nexus_status_reply: Callable | None = None      # "catch me up"
    handoff_check_reply: Callable | None = None     # "pending handoffs"
    decision_log_reply: Callable | None = None      # "decision log"
    demo_status_reply: Callable | None = None       # "OANDA demo status"
    premium_blocker_reply: Callable | None = None   # "Beehiiv alternative"
    save_feedback_reply: Callable | None = None     # "record lesson"

    def route_incoming_message(self, text: str) -> tuple[str, str]:
        # ── Evidence gate: block all fake trading execution claims globally ───
        if _EVIDENCE_GATING and _is_fake_trading(text):
            return ROUTE_DEMO_STATUS, self.chat_response(
                "I cannot report trade execution claims without a verified broker artifact. "
                "No order ID found. OANDA demo requires a real execution packet.\n\n"
                "To check real demo status: ask 'show me oanda demo status'"
            )

        approval = self.handle_approval_reply(text)
        if approval:
            return ROUTE_APPROVAL, self.chat_response(approval)

        risky = self.risky_action_requested(text)
        if risky:
            return ROUTE_APPROVAL, self.approval_request_response(risky)

        # ── Strategic operating partner routes (checked before general classify) ──
        strategic_route = self._match_strategic(text)
        if strategic_route:
            return self._handle_strategic(strategic_route, text)

        route = self.classify_message_route(text)
        if route == ROUTE_COMMAND:
            return ROUTE_COMMAND, self.handle_command_mode(text)
        if route == ROUTE_REPORT_REQUEST:
            body = self.report_email(text)
            if self.email_reports_enabled():
                self.send_report_email("Hermes Requested Report", body)
            if self.full_reports_enabled():
                return ROUTE_REPORT_REQUEST, self.report_response(body)
            return ROUTE_REPORT_REQUEST, self.report_confirmation()
        if route == ROUTE_FUNDING_INSIGHTS:
            return ROUTE_FUNDING_INSIGHTS, self.chat_response(self.funding_insights_reply())
        if route == ROUTE_CREDIT_INSIGHTS:
            return ROUTE_CREDIT_INSIGHTS, self.chat_response(self.credit_insights_reply())
        if route == ROUTE_KNOWLEDGE_REPORT:
            body = self.knowledge_report_email()
            if self.email_reports_enabled():
                self.send_report_email("Hermes Knowledge Brain Report", body)
            return ROUTE_KNOWLEDGE_REPORT, self.chat_response(self.knowledge_report_confirmation())
        if route == ROUTE_DAILY_PLAN:
            return ROUTE_DAILY_PLAN, self.chat_response(self.build_daily_plan())
        if route == ROUTE_TASK_SELECTION:
            selected = self.task_selection_reply(text)
            if selected:
                if "queued" in selected.lower() or "notify" in selected.lower():
                    return ROUTE_COMPLETION_NOTICE, self.chat_response(selected)
                return ROUTE_TASK_SELECTION, self.chat_response(selected)
            return ROUTE_TASK_SELECTION, "Please ask for today's plan first so I can map the item correctly."

        try:
            return ROUTE_CHAT, self.chat_response(self.conversational_reply(text))
        except Exception as e:
            if self.model_error_response is not None:
                return ROUTE_CHAT, self.chat_response(self.model_error_response(e))
            return ROUTE_CHAT, self.chat_response(self.help_text())

    # ── Strategic route helpers ────────────────────────────────────────────────

    def _match_strategic(self, text: str) -> str | None:
        lower = text.lower()
        for pattern, route in _STRATEGIC_PATTERNS:
            if re.search(pattern, lower):
                return route
        return None

    def _handle_strategic(self, route: str, text: str) -> tuple[str, str]:
        # ── Evidence gate: block fake trading claims before routing ───────────
        if _EVIDENCE_GATING and _is_fake_trading(text) and route == ROUTE_DEMO_STATUS:
            return route, self.chat_response(
                "I cannot report trade execution claims without a verified broker artifact. "
                "No order ID found in OANDA demo reports.\n\n"
                "To check real demo status, run: "
                "`python scripts/test_oanda_demo_execution_loop.py --dry-run`"
            )

        handler_map = {
            ROUTE_NEXUS_STATUS:    self.nexus_status_reply,
            ROUTE_HANDOFF_CHECK:   self.handoff_check_reply,
            ROUTE_DECISION_LOG:    self.decision_log_reply,
            ROUTE_DEMO_STATUS:     self.demo_status_reply,
            ROUTE_PREMIUM_BLOCKER: self.premium_blocker_reply,
            ROUTE_SAVE_FEEDBACK:   self.save_feedback_reply,
        }
        handler = handler_map.get(route)
        if handler is not None:
            try:
                reply = handler(text)
                # Post-check: block theatrical language in handler responses
                if _EVIDENCE_GATING and _has_theatrical(reply):
                    reply = re.sub(
                        r'\*[^*]{1,60}\*',  # strip *action* roleplay italics
                        '', reply
                    ).strip()
                return route, self.chat_response(reply)
            except Exception as e:
                return route, self.chat_response(f"Strategic handler error: {e}")
        # Fallback: delegate to hermes_collaboration_service (already evidence-gated)
        try:
            from lib.hermes_collaboration_service import HermesCollaboration
            result = HermesCollaboration().handle(text)
            return route, self.chat_response(result.get("answer", "No response generated."))
        except Exception as e:
            return ROUTE_CHAT, self.chat_response(self.help_text())
