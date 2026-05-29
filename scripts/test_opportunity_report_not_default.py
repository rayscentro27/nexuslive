"""
test_opportunity_report_not_default.py
Verifies "youtube channel" text no longer triggers the opportunity scorer,
and that other status/system questions are also blocked.
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

print("=== test_opportunity_report_not_default ===")

from lib.opportunity_analyzer import is_opportunity_input

# 1. "youtube channel" text no longer triggers scorer
SHOULD_NOT_TRIGGER = [
    "what is the last youtube channel that was processed",
    "show youtube channels",
    "youtube channel status",
    "what youtube channel did we add",
    "how many youtube channels are registered",
]

for msg in SHOULD_NOT_TRIGGER:
    check(f"NOT opportunity: {msg[:55]}", not is_opportunity_input(msg))

# 2. YouTube URL messages never trigger scorer
URL_MESSAGES = [
    "https://www.youtube.com/watch?v=9TfvBH_efCU",
    "what do you think about this https://youtube.com/watch?v=XYZ",
    "check out https://youtu.be/abc123",
]
for msg in URL_MESSAGES:
    check(f"URL msg NOT opportunity: {msg[:55]}", not is_opportunity_input(msg))

# 3. Genuine opportunity messages still trigger scorer
SHOULD_TRIGGER = [
    "can nexus monetize this affiliate program",
    "analyze this business idea: faceless content business",
    "score this saas opportunity",
    "is this a good niche for newsletters",
]
for msg in SHOULD_TRIGGER:
    check(f"IS opportunity: {msg[:55]}", is_opportunity_input(msg))

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
