"""
test_telegram_evidence_gating.py
=================================
Verify that TelegramRouter applies evidence gating to strategic routes.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.telegram_router import TelegramRouter, ROUTE_DEMO_STATUS, ROUTE_NEXUS_STATUS

PASS = 0
FAIL = 0


def check(desc: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  ✅ {desc}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {desc}")
        FAIL += 1


print("\n=== test_telegram_evidence_gating ===\n")

# Build a minimal TelegramRouter
router = TelegramRouter(
    classify_message_route=lambda t: "chat",
    handle_command_mode=lambda t: "cmd",
    build_daily_plan=lambda: "plan",
    task_selection_reply=lambda t: None,
    handle_approval_reply=lambda t: None,
    risky_action_requested=lambda t: None,
    conversational_reply=lambda t: "reply",
    report_email=lambda t: "report",
    send_report_email=lambda s, b: None,
    report_confirmation=lambda: "confirmed",
    funding_insights_reply=lambda: "funding",
    credit_insights_reply=lambda: "credit",
    knowledge_report_email=lambda: "knowledge",
    knowledge_report_confirmation=lambda: "knowledge_conf",
    help_text=lambda: "help",
    email_reports_enabled=lambda: False,
    full_reports_enabled=lambda: True,
    report_response=lambda b: b,
    approval_request_response=lambda r: str(r),
    chat_response=lambda r: r,
)

# 1. Fake trading claim → blocked response at ROUTE_DEMO_STATUS
route, reply = router.route_incoming_message("scalp active, target hit at 1.0850")
check("fake trade claim → ROUTE_DEMO_STATUS", route == ROUTE_DEMO_STATUS)
check("fake trade blocked message shown", "cannot report" in reply.lower() or "no order id" in reply.lower() or "blocked" in reply.lower())

# 2. Normal demo status query → goes to strategic route
route2, reply2 = router.route_incoming_message("what happened with the oanda demo")
check("oanda demo query → strategic route", route2 == ROUTE_DEMO_STATUS)

# 3. Nexus status → strategic route
route3, _ = router.route_incoming_message("catch me up, where are we?")
check("catch me up → nexus status route", route3 == ROUTE_NEXUS_STATUS)

# 4. Theatrical language stripped from handler reply
call_count = [0]
def theatrical_handler(t: str) -> str:
    call_count[0] += 1
    return "*taps tablet* Here is the latest status update. *leans forward*"

router_with_handler = TelegramRouter(
    **{
        **{f: getattr(router, f) for f in [
            "classify_message_route", "handle_command_mode", "build_daily_plan",
            "task_selection_reply", "handle_approval_reply", "risky_action_requested",
            "conversational_reply", "report_email", "send_report_email",
            "report_confirmation", "funding_insights_reply", "credit_insights_reply",
            "knowledge_report_email", "knowledge_report_confirmation", "help_text",
            "email_reports_enabled", "full_reports_enabled", "report_response",
            "approval_request_response", "chat_response",
        ]},
        "nexus_status_reply": theatrical_handler,
    }
)
route4, reply4 = router_with_handler.route_incoming_message("catch me up")
check("nexus_status_reply handler was called", call_count[0] == 1)
check("route is nexus_status", route4 == ROUTE_NEXUS_STATUS)
# The theatrical stripper removes *..* patterns
check("theatrical asterisk-phrases stripped from reply",
      "taps tablet" not in reply4 or "*" not in reply4)

# 5. Strategic match before general classify
route5, _ = router.route_incoming_message("what do you need my approval on")
from lib.telegram_router import ROUTE_HANDOFF_CHECK
check("approval query → handoff_check route", route5 == ROUTE_HANDOFF_CHECK)

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
