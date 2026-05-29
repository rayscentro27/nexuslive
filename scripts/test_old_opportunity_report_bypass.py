"""
test_old_opportunity_report_bypass.py
Verifies that YouTube URLs never produce the old NEXUS OPPORTUNITY REPORT.
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

print("=== test_old_opportunity_report_bypass ===")

from lib.opportunity_analyzer import is_opportunity_input, generate_opportunity_report

YOUTUBE_MESSAGES = [
    "https://www.youtube.com/watch?v=9TfvBH_efCU",
    "do you recommend updated hermes https://www.youtube.com/watch?v=9TfvBH_efCU",
    "what do you think about this https://youtube.com/watch?v=XYZ",
    "check out https://youtu.be/abc123",
    "https://www.youtube.com/@SomeChannel",
]

for msg in YOUTUBE_MESSAGES:
    check(f"YouTube URL blocked from scorer: {msg[:50]}", not is_opportunity_input(msg))

# Verify system-context messages are also blocked
SYSTEM_MESSAGES = [
    "should I update hermes https://www.youtube.com/watch?v=9TfvBH_efCU",
    "hermes auth failed https://youtube.com/watch?v=XYZ",
    "is the gateway connection down https://youtu.be/ABC",
    "what model is hermes using https://youtube.com/watch?v=DEF",
]

for msg in SYSTEM_MESSAGES:
    check(f"System + YouTube blocked from scorer: {msg[:50]}", not is_opportunity_input(msg))

# Verify that explicit opportunity messages still work (no YouTube)
OPPORTUNITY_MESSAGES = [
    "can nexus monetize this affiliate program",
    "analyze this business idea: faceless content business",
    "score this saas opportunity",
]

for msg in OPPORTUNITY_MESSAGES:
    check(f"Explicit opportunity triggers scorer: {msg[:50]}", is_opportunity_input(msg))

# Verify the report template
report = generate_opportunity_report("affiliate marketing saas")
check("NEXUS OPPORTUNITY REPORT in template", "NEXUS OPPORTUNITY REPORT" in report)
check("DIMENSION SCORES in template", "DIMENSION SCORES" in report)
check("Nexus Synergy in template", "Nexus Synergy" in report)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
