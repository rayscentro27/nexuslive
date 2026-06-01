"""test_conversational_router.py — Verify routing logic for all categories."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")

print("=== test_conversational_router ===\n")

from lib.hermes_conversational_router import (
    classify_conversational_intent, normalize_user_message,
    is_small_talk, is_capability_question, is_system_health_question,
    is_monetization_question, is_external_info_question,
    is_memory_source_question, is_content_asset_question,
    format_capability_response, format_unknown_question_response,
    route_conversational_intent,
)
from lib.hermes_language_pack import (
    CATEGORY_SMALL_TALK, CATEGORY_CAPABILITY, CATEGORY_SYSTEM_HEALTH,
    CATEGORY_MONETIZATION, CATEGORY_EXTERNAL_INFO, CATEGORY_UNKNOWN,
    CATEGORY_MEMORY_SOURCE,
)

# Normalize
check("normalize strips ?", normalize_user_message("hello?") == "hello")
check("normalize lowercase", "hello" == normalize_user_message("HELLO"))
check("normalize collapses spaces", normalize_user_message("a  b") == "a b")

# Classifiers
check("is_small_talk('did you sleep')", is_small_talk("did you sleep"))
check("is_small_talk('did you get sleep last night')", is_small_talk("did you get sleep last night"))
check("is_small_talk('how are you')", is_small_talk("how are you"))
check("is_small_talk('are you online')", is_small_talk("are you online"))
check("not is_small_talk('nexus status')", not is_small_talk("nexus status"))

check("is_capability_question('what can you answer')", is_capability_question("what can you answer"))
check("is_capability_question('what can you do')", is_capability_question("what can you do"))
check("is_capability_question('help')", is_capability_question("help"))

check("is_system_health_question('what is the system health')", is_system_health_question("what is the system health"))
check("is_system_health_question('is nexus healthy')", is_system_health_question("is nexus healthy"))
check("is_system_health_question('what is broken')", is_system_health_question("what is broken"))

check("is_monetization_question('best money making opportunity right now')", is_monetization_question("best money making opportunity right now"))
check("is_monetization_question('how do we make money today')", is_monetization_question("how do we make money today"))

check("is_external_info_question('what is the weather today')", is_external_info_question("what is the weather today"))
check("is_external_info_question('stock price')", is_external_info_question("stock price"))

check("is_memory_source_question('show memory sources')", is_memory_source_question("show memory sources"))

# classify_conversational_intent
check("classify 'did you get sleep last night' → small_talk",
      classify_conversational_intent("did you get sleep last night") == CATEGORY_SMALL_TALK)
check("classify 'what can you answer' → capability",
      classify_conversational_intent("what can you answer") == CATEGORY_CAPABILITY)
check("classify 'what is the system health' → system_health",
      classify_conversational_intent("what is the system health") == CATEGORY_SYSTEM_HEALTH)
check("classify 'what is the best money making opportunity right now' → monetization",
      classify_conversational_intent("what is the best money making opportunity right now") == CATEGORY_MONETIZATION)
check("classify 'what is the weather today' → external_info",
      classify_conversational_intent("what is the weather today") == CATEGORY_EXTERNAL_INFO)
check("classify 'show memory sources' → memory_source",
      classify_conversational_intent("show memory sources") == CATEGORY_MEMORY_SOURCE)

# route_conversational_intent
r1 = route_conversational_intent("did you get sleep last night")
check("small_talk route returns string", isinstance(r1, str))
check("small_talk no evidence dump", "artifact_inventory" not in (r1 or ""))
check("small_talk no OFFLINE", "OFFLINE" not in (r1 or ""))

r2 = route_conversational_intent("what can you answer")
check("capability route returns string", isinstance(r2, str))
check("capability mentions content drafts", "draft" in (r2 or "").lower() or "content" in (r2 or "").lower())

r3 = route_conversational_intent("what is the weather today")
check("external info route returns string", isinstance(r3, str))
check("external info no hallucination", "provider" in (r3 or "").lower() or "not" in (r3 or "").lower())
check("external info logged gap marker absent", "OFFLINE" not in (r3 or ""))

# format helpers
cap = format_capability_response()
check("capability response has bullets", "•" in cap)
check("unknown fallback not empty", len(format_unknown_question_response("foo")) > 10)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
