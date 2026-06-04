"""test_nav_relay_no_live_links.py — readiness packet and approval summary keep placeholder-only links."""
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
bot = make_bot()
try:
    bot.handle_inbound_message(
        "Prepare the Nav and Relay affiliate application readiness packet. Include what information Ray needs before applying, required website/social/channel details, compliance-safe program description, proposed traffic sources, and approval checklist. Do not submit applications, do not activate links, do not publish, and do not email anyone."
    )
    latest_json = sorted(glob.glob(str(root / "docs" / "reports" / "funnel" / "nav_relay_affiliate_application_readiness_packet_*.json")))[-1]
    payload = json.loads(Path(latest_json).read_text(encoding="utf-8"))
    nav_plan = "\n".join(payload.get("nav_placement_plan", []))
    relay_plan = "\n".join(payload.get("relay_placement_plan", []))
    check("nav placeholder present", "[NAV_AFFILIATE_LINK_PENDING_RAY_APPROVAL]" in nav_plan)
    check("relay placeholder present", "[RELAY_AFFILIATE_LINK_PENDING_RAY_APPROVAL]" in relay_plan)
    check("no live affiliate URLs in nav plan", "http" not in nav_plan.lower())
    check("no live affiliate URLs in relay plan", "http" not in relay_plan.lower())
finally:
    cleanup_env()

print(f"\nNav/Relay no live links: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
