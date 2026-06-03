"""
test_cfo_brain_general_router.py
Phase 7B: CFO Brain — general routing tests.
Verifies that should_use_cfo_brain and classify_cfo_intent
route natural messages correctly.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

passes = 0
failures = 0

def check(label, cond):
    global passes, failures
    status = "PASS" if cond else "FAIL"
    if not cond:
        failures += 1
    else:
        passes += 1
    print(f"  [{status}] {label}")
    return cond


from lib.hermes_cfo_brain import should_use_cfo_brain, classify_cfo_intent

print("\nCFO Brain General Router Tests")
print("=" * 50)

print("\n-- should_use_cfo_brain: natural language --")
check("morning question", should_use_cfo_brain("what did you do this morning") is True)
check("task question", should_use_cfo_brain("what tasks are in the queue") is True)
check("simplify request", should_use_cfo_brain("can you simplify your response") is True)
check("option selection", should_use_cfo_brain("let's do 1") is True)
check("money strategy", should_use_cfo_brain("how do we make money this week") is True)
check("failure feedback", should_use_cfo_brain("that is not what i meant") is True)
check("explain request", should_use_cfo_brain("explain your recommendation in plain language") is True)
check("scout dispatch", should_use_cfo_brain("can your scouts figure it out") is True)

print("\n-- should_use_cfo_brain: commands fall through --")
check("show command", should_use_cfo_brain("show approval queue") is False)
check("run command", should_use_cfo_brain("run daily operating cycle") is False)
check("build command", should_use_cfo_brain("build revenue asset packet") is False)
check("single word", should_use_cfo_brain("help") is False)

print("\n-- classify_cfo_intent --")
check("simplify → simplify_previous_response",
      classify_cfo_intent("can you simplify your response") == "simplify_previous_response")
check("explain → explain_previous_response",
      classify_cfo_intent("explain your recommendation in plain language") == "explain_previous_response")
check("option → option_selection",
      classify_cfo_intent("let's do 1") == "option_selection")
check("task → task_reference",
      classify_cfo_intent("what was task 1") == "task_reference")
check("morning → morning_activity_question",
      classify_cfo_intent("what did you do this morning") == "morning_activity_question")
check("queue → queue_status_question",
      classify_cfo_intent("what tasks are in the queue") == "queue_status_question")
check("money → money_strategy_question",
      classify_cfo_intent("how do we make money this week") == "money_strategy_question")
check("failure → failure_feedback",
      classify_cfo_intent("that is not what i meant") == "failure_feedback")
check("prompt → implementation_prompt_request",
      classify_cfo_intent("create a prompt for claude") == "implementation_prompt_request")
check("scout → scout_dispatch_request",
      classify_cfo_intent("can your scouts figure it out") == "scout_dispatch_request")
check("number only → option_selection",
      classify_cfo_intent("1") == "option_selection")

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
