"""test_nav_relay_readiness_packet_creation.py — readiness packet is created locally and validates."""
import glob
import json
import sys
from pathlib import Path

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


root = Path(__file__).resolve().parent.parent
pattern_md = str(root / "docs" / "reports" / "funnel" / "nav_relay_affiliate_application_readiness_packet_*.md")
pattern_json = str(root / "docs" / "reports" / "funnel" / "nav_relay_affiliate_application_readiness_packet_*.json")
before_md = set(glob.glob(pattern_md))
before_json = set(glob.glob(pattern_json))

bot = make_bot()
try:
    response = bot.handle_inbound_message(
        "Prepare the Nav and Relay affiliate application readiness packet. Include what information Ray needs before applying, required website/social/channel details, compliance-safe program description, proposed traffic sources, and approval checklist. Do not submit applications, do not activate links, do not publish, and do not email anyone."
    )
    after_md = set(glob.glob(pattern_md))
    after_json = set(glob.glob(pattern_json))
    new_md = sorted(after_md - before_md)
    new_json = sorted(after_json - before_json)
    check("response confirms packet created", "internal readiness packet created" in response.lower())
    check("markdown file created", len(new_md) == 1)
    check("json file created", len(new_json) == 1)
    if new_md and new_json:
        md_text = Path(new_md[-1]).read_text(encoding="utf-8")
        payload = json.loads(Path(new_json[-1]).read_text(encoding="utf-8"))
        check("markdown includes purpose", "internal readiness packet only. no applications submitted." in md_text.lower())
        check("json report_type valid", payload.get("report_type") == "nav_relay_affiliate_application_readiness_packet")
        check("json purpose valid", payload.get("purpose") == "Internal readiness packet only. No applications submitted.")
        check("json safety confirms no applications", payload.get("safety_confirmation", {}).get("affiliate_applications_submitted") == "NO")
finally:
    cleanup_env()

print(f"\nNav/Relay readiness packet creation: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
