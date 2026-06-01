"""test_hermes_language_pack.py — Verify language pack phrase sets and helpers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")

print("=== test_hermes_language_pack ===\n")

from lib.hermes_language_pack import (
    SMALL_TALK_PHRASES, SMALL_TALK_RESPONSE,
    CAPABILITY_PHRASES, CAPABILITY_RESPONSE,
    SYSTEM_HEALTH_PHRASES, MONETIZATION_PHRASES,
    MEMORY_SOURCE_PHRASES, CONTENT_ASSET_PHRASES,
    EXTERNAL_INFO_KEYWORDS, is_external_info, external_info_topic,
    format_external_unavailable_response,
    CATEGORY_SMALL_TALK, CATEGORY_CAPABILITY, CATEGORY_SYSTEM_HEALTH,
    CATEGORY_MONETIZATION, CATEGORY_CONTENT_ASSET, CATEGORY_MEMORY_SOURCE,
    CATEGORY_EXTERNAL_INFO, CATEGORY_UNKNOWN, ALL_CATEGORIES,
)

# Phrase sets are non-empty frozensets
for name, s in [("SMALL_TALK", SMALL_TALK_PHRASES), ("CAPABILITY", CAPABILITY_PHRASES),
                ("SYSTEM_HEALTH", SYSTEM_HEALTH_PHRASES), ("MONETIZATION", MONETIZATION_PHRASES)]:
    check(f"{name}_PHRASES is non-empty frozenset", isinstance(s, frozenset) and len(s) > 0)

# Key phrases present
check("'did you sleep' in SMALL_TALK", "did you sleep" in SMALL_TALK_PHRASES)
check("'how are you' in SMALL_TALK", "how are you" in SMALL_TALK_PHRASES)
check("'what can you answer' in CAPABILITY", "what can you answer" in CAPABILITY_PHRASES)
check("'system health' in SYSTEM_HEALTH", "system health" in SYSTEM_HEALTH_PHRASES)
check("'best money making' in MONETIZATION", "best money making" in MONETIZATION_PHRASES)
check("'show memory sources' in MEMORY_SOURCE", "show memory sources" in MEMORY_SOURCE_PHRASES)

# Static responses not empty
check("SMALL_TALK_RESPONSE not empty", len(SMALL_TALK_RESPONSE) > 20)
check("CAPABILITY_RESPONSE has bullet points", "•" in CAPABILITY_RESPONSE)
check("CAPABILITY_RESPONSE mentions status", "status" in CAPABILITY_RESPONSE.lower())
check("CAPABILITY_RESPONSE mentions gaps", "gap" in CAPABILITY_RESPONSE.lower())

# External info helpers
check("is_external_info('weather today')", is_external_info("weather today"))
check("is_external_info('stock price')", is_external_info("stock price"))
check("not is_external_info('nexus status')", not is_external_info("nexus status"))
check("external_info_topic('weather today') has 'weather'", "weather" in external_info_topic("weather today"))
resp = format_external_unavailable_response("weather")
check("unavailable resp mentions provider", "provider" in resp.lower())
check("unavailable resp mentions gap", "gap" in resp.lower())
check("unavailable resp no OFFLINE stale data", "OFFLINE" not in resp)

# Category constants
check("ALL_CATEGORIES has 8 items", len(ALL_CATEGORIES) == 8)
check("CATEGORY_UNKNOWN in ALL_CATEGORIES", CATEGORY_UNKNOWN in ALL_CATEGORIES)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
