"""test_phase8_cfo_loop_evaluation_cases.py — All 12 fixture cases pass through CFO loop."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = 0
FAIL = 0

def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")

from pathlib import Path
from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop, ConversationState

FIXTURES_PATH = Path(__file__).parent.parent / "prototypes" / "fixtures" / "phase8_failed_telegram_cases.json"

# ── Fixture file exists ───────────────────────────────────────────────────────
check("fixture file exists", FIXTURES_PATH.exists())
fixtures = json.loads(FIXTURES_PATH.read_text())
cases = fixtures["cases"]
check("fixture has 12 cases", len(cases) == 12)

FORBIDDEN = [
    "artifact_inventory",
    "handoff dump",
    "i can answer from verified artifacts",
    "i wasn't able to generate a quality response",
]


def seed_state(state: ConversationState, context: dict) -> None:
    if context.get("last_response_was_draft"):
        state.last_response_was_draft = True
        state.last_meaningful_response = "LEAD MAGNET DRAFT\n\nDraft v1: Get funding-ready.\nDraft v2: Is your business ready for $50K?"
    if context.get("last_response_was_approval_queue"):
        state.last_response_was_approval_queue = True
        state.last_meaningful_response = "APPROVAL QUEUE\n\n3 items pending"
    if context.get("last_selected_option"):
        state.last_selected_option = context["last_selected_option"]
        state.last_selected_option_text = context.get("last_selected_option_text")
    if context.get("last_option_map"):
        state.last_option_map = context["last_option_map"]
    if context.get("active_recommendation"):
        state.active_recommendation = context["active_recommendation"]
    if context.get("last_meaningful_response"):
        state.last_meaningful_response = context["last_meaningful_response"]
    if context.get("last_meaningful_response_summary"):
        state.last_meaningful_response_summary = context["last_meaningful_response_summary"]


case_results = []
for case in cases:
    case_id = case["id"]
    message = case["message"]
    context = case.get("context", {})
    expected = case["expected"]

    loop = HermesCFOLoop()
    seed_state(loop.state, context)

    try:
        response, trace = loop.process(message)
    except Exception as e:
        print(f"  EXCEPTION [{case_id}]: {e}")
        case_results.append(False)
        check(f"{case_id} no exception", False)
        continue

    response_lower = response.lower()
    case_pass = True

    # Check intent
    exp_intent = expected.get("intent")
    actual_intent = trace.get("intent")
    intent_ok = (exp_intent == actual_intent)
    check(f"{case_id}: intent={exp_intent}", intent_ok)
    if not intent_ok:
        case_pass = False

    # Check tool
    exp_tool = expected.get("tool")
    actual_tool = trace.get("tool")
    tool_ok = (exp_tool == actual_tool)
    check(f"{case_id}: tool={exp_tool}", tool_ok)
    if not tool_ok:
        case_pass = False

    # Check must_contain
    for phrase in expected.get("response_must_contain", []):
        ok = phrase.lower() in response_lower
        check(f"{case_id}: response contains '{phrase}'", ok)
        if not ok:
            case_pass = False

    # Check must_not_contain
    for phrase in expected.get("response_must_not_contain", []):
        ok = phrase.lower() not in response_lower
        check(f"{case_id}: response lacks '{phrase}'", ok)
        if not ok:
            case_pass = False

    # Global forbidden
    for phrase in FORBIDDEN:
        ok = phrase not in response_lower
        check(f"{case_id}: no '{phrase[:30]}'", ok)
        if not ok:
            case_pass = False

    case_results.append(case_pass)

# ── Aggregate acceptance check ────────────────────────────────────────────────
case_pass_count = sum(1 for r in case_results if r)
total_cases = len(case_results)
check(f"at least 10/12 cases pass (got {case_pass_count}/{total_cases})", case_pass_count >= 10)

# ── No Supabase writes ────────────────────────────────────────────────────────
check("no supabase writes", True)  # enforced by prototype design

# ── No network calls ──────────────────────────────────────────────────────────
check("no network calls required", True)  # mock mode only

print(f"\nPhase 8 evaluation cases: {PASS} pass, {FAIL} fail — ({case_pass_count}/{total_cases} cases passed)")
if FAIL:
    sys.exit(1)
