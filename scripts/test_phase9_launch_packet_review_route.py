"""test_phase9_launch_packet_review_route.py — launch packet review uses deterministic approval summary."""
import sys

from phase9_test_helpers import cleanup_env, make_bot

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


bot = make_bot()
try:
    response = bot.handle_inbound_message(
        "Review the Funding Readiness Launch Packet and give me the approval decision summary."
    )
    lower = response.lower()
    check("launch packet header present", response.startswith("FUNDING READINESS APPROVAL SUMMARY"))
    check("ready section present", "ready for internal approval" in lower)
    check("not ready section present", "not ready for public approval" in lower)
    check("monetization section present", "recommended first monetization path" in lower)
    check("compliance section present", "compliance risks" in lower)
    check("approval authorize section present", "what approval authorizes" in lower)
    check("approval boundary section present", "what approval does not authorize" in lower)
    check("next safe step present", "next safe step" in lower)
finally:
    cleanup_env()

print(f"\nPhase 9 launch packet review route: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
