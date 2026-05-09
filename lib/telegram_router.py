from __future__ import annotations

from dataclasses import dataclass


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


@dataclass
class TelegramRouter:
    classify_message_route: callable
    handle_command_mode: callable
    build_daily_plan: callable
    task_selection_reply: callable
    handle_approval_reply: callable
    risky_action_requested: callable
    conversational_reply: callable
    report_email: callable
    send_report_email: callable
    report_confirmation: callable
    funding_insights_reply: callable
    credit_insights_reply: callable
    knowledge_report_email: callable
    knowledge_report_confirmation: callable
    help_text: callable
    email_reports_enabled: callable
    full_reports_enabled: callable
    report_response: callable
    approval_request_response: callable
    chat_response: callable
    model_error_response: callable | None = None

    def route_incoming_message(self, text: str) -> tuple[str, str]:
        approval = self.handle_approval_reply(text)
        if approval:
            return ROUTE_APPROVAL, self.chat_response(approval)

        risky = self.risky_action_requested(text)
        if risky:
            return ROUTE_APPROVAL, self.approval_request_response(risky)

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
