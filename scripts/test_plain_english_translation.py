"""
test_plain_english_translation.py
Verifies "explain that simply" and common-language commands work.
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

print("=== test_plain_english_translation ===")

from lib.hermes_internal_first import try_internal_first

# 1. "explain that simply" routes to plain_english topic
PLAIN_ENGLISH_COMMANDS = [
    "explain that simply",
    "give me the plain english version",
    "plain english",
    "what does that mean",
    "explain in plain language",
    "summarize for ceo review",
]

for cmd in PLAIN_ENGLISH_COMMANDS:
    result = try_internal_first(cmd)
    check(f"has reply for: {cmd[:45]}", result is not None)
    if result:
        check(f"topic is plain_english: {cmd[:40]}", result.matched_topic == "plain_english")
        check(f"reply mentions plain or language: {cmd[:35]}",
              "plain" in result.text.lower() or "language" in result.text.lower()
              or "explain" in result.text.lower())

# 2. "show technical details" routes to technical_details topic
TECHNICAL_COMMANDS = [
    "show technical details",
    "show raw evidence",
    "show debug details",
    "show logs",
    "technical details",
]

for cmd in TECHNICAL_COMMANDS:
    result = try_internal_first(cmd)
    check(f"has reply for: {cmd[:45]}", result is not None)
    if result:
        check(f"topic is technical_details: {cmd[:40]}", result.matched_topic == "technical_details")
        check(f"reply mentions technical or details: {cmd[:35]}",
              "technical" in result.text.lower() or "detail" in result.text.lower()
              or "raw" in result.text.lower() or "log" in result.text.lower())

# 3. Plain English mode does NOT show raw logs by default
result_pe = try_internal_first("explain that simply")
if result_pe:
    check("plain english reply has no Traceback", "Traceback" not in result_pe.text)
    check("plain english reply has no KeyError", "KeyError" not in result_pe.text)
    check("plain english reply is concise (<1000 chars)", len(result_pe.text) < 1000)

# 4. Operating doctrine mentions plain language rule
from pathlib import Path
doctrine = Path(__file__).resolve().parent.parent / "docs" / "HERMES_OPERATING_DOCTRINE.md"
if doctrine.exists():
    text = doctrine.read_text()
    check("doctrine mentions plain language communication", "plain" in text.lower())
    check("doctrine mentions technical output only when asked",
          "only when" in text.lower() or "only appear" in text.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
