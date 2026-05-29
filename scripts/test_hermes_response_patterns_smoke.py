"""
test_hermes_response_patterns_smoke.py
Smoke test: all internal handlers return without exception and meet basic quality checks.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_hermes_response_patterns_smoke ===")

from lib.hermes_internal_first import try_internal_first

ALL_HANDLER_PROBES = [
    # Existing handlers
    ("what did codex finish", "opencode"),
    ("funding blockers", "funding"),
    ("what should i work on today", "today"),
    ("knowledge emails", "knowledge_email"),
    ("before travel", "travel"),
    ("notebooklm status", "notebooklm"),
    ("what ai providers are available", "ai_providers"),
    ("marketing research", "marketing"),
    ("trading status", "trading"),
    ("circuit breaker status", "circuit_breaker"),
    ("workforce status", "workforce"),
    ("ceo briefing", "ceo_briefing"),
    ("claw3d status", "claw3d"),
    ("evidence guard", "evidence"),
    ("improvement queue", "improvement"),
    ("show memory", "executive_memory"),
    ("what are the priorities", "execution_priorities"),
    ("monetization", "monetization"),
    ("scout status", "scouts"),
    ("source intelligence", "source_intelligence"),
    ("watcher status", "watchers"),
    # New handlers
    ("what did claude code work on", "claude_code_work"),
    ("where do you get your information", "information_sources"),
    ("what is nexus", "nexus_project"),
    ("30 day goals", "goals_30_day"),
    ("youtube status", "youtube_status"),
]

for query, expected_topic in ALL_HANDLER_PROBES:
    try:
        result = try_internal_first(query)
        if result is None:
            FAIL += 1
            print(f"  ❌ no reply for '{query}' (expected topic: {expected_topic})")
            continue
        check(f"'{query[:40]}' → topic={result.matched_topic}", result.matched_topic == expected_topic)
        check(f"'{query[:40]}' → non-empty reply", len(result.text.strip()) > 5)
    except Exception as exc:
        FAIL += 1
        print(f"  ❌ exception for '{query}': {exc}")

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
