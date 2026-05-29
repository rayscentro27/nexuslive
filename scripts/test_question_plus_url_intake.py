"""
test_question_plus_url_intake.py
Verifies that a question + YouTube URL preserves the question as attached_intent.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, got, expected):
    global PASS, FAIL
    ok = bool(got) if expected is True else (not bool(got)) if expected is False else got == expected
    if ok:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label} — got={got!r}")

print("=== test_question_plus_url_intake ===")

from lib.hermes_telegram_source_intake import HermesTelegramSourceIntake
intake = HermesTelegramSourceIntake()

msg = "do you recommend updated hermes https://www.youtube.com/watch?v=9TfvBH_efCU"
record = intake.process(msg, attached_intent=msg)

# 1. Question is preserved
intent = record._data.get("attached_intent", "")
check("attached_intent is stored", bool(intent), True)
check("URL stripped from intent", "https://" not in intent, True)
check("question text preserved in intent", len(intent) > 3, True)

# 2. Reply includes the question
reply = record.telegram_reply()
check("reply shows Ray's question", "Ray's question" in reply, True)
check("reply shows scout assigned", "youtube_research_scout" in reply, True)
check("reply shows artifacts pending", "Artifacts pending" in reply, True)
check("reply shows evidence path", "intake" in reply.lower(), True)
check("reply shows next action", "next action" in reply.lower(), True)

# 3. Intake record has correct fields
check("source_type detected", record.source_type == "youtube_video", True)
check("url extracted", "youtube.com" in record.url, True)
check("status is registered", record.status == "registered", True)

# 4. Different question styles
msg2 = "what do you think about https://youtube.com/watch?v=XYZ123 for nexus"
r2 = intake.process(msg2, attached_intent=msg2)
check("second intake also stores intent", bool(r2._data.get("attached_intent")), True)

# 5. URL-only message (no question)
msg3 = "https://www.youtube.com/watch?v=ABC456"
r3 = intake.process(msg3, attached_intent=msg3)
intent3 = r3._data.get("attached_intent", "")
check("url-only has empty or minimal intent", len(intent3) < 5, True)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
