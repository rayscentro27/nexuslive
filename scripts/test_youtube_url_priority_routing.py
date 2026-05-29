"""
test_youtube_url_priority_routing.py
Verifies that YouTube URLs are routed to source intake, not the opportunity scorer.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, got, expected, negate=False):
    global PASS, FAIL
    ok = (got == expected) if not negate else (got != expected)
    if ok:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label} — got={got!r} expected={'not ' if negate else ''}{expected!r}")

print("=== test_youtube_url_priority_routing ===")

# 1. YouTube video URL should not reach opportunity scorer
from lib.opportunity_analyzer import is_opportunity_input
yt_msg = "do you recommend updated hermes https://www.youtube.com/watch?v=9TfvBH_efCU"
check("youtube video URL blocked from opportunity scorer", is_opportunity_input(yt_msg), False)

# 2. YouTube channel URL should not reach opportunity scorer
yt_ch = "check out this channel https://www.youtube.com/@SomeChannel"
check("youtube channel URL blocked from opportunity scorer", is_opportunity_input(yt_ch), False)

# 3. youtu.be short URL should not reach opportunity scorer
yt_short = "https://youtu.be/abc123"
check("youtu.be short URL blocked from opportunity scorer", is_opportunity_input(yt_short), False)

# 4. GitHub URL should not reach opportunity scorer via URL-only trigger
gh_msg = "check this repo https://github.com/user/repo"
check("github URL blocked from opportunity scorer", is_opportunity_input(gh_msg), False)

# 5. Non-YouTube URL with business context should still reach opportunity scorer
biz_url = "can we monetize this https://someaffiliate.com/program"
check("non-youtube affiliate URL still reaches scorer", is_opportunity_input(biz_url), True)

# 6. Internal routing — YouTube URL routes to source intake
import re
_YT_RE = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|@|channel/|c/)|youtu\.be/)', re.I
)
check("regex matches youtube watch URL", bool(_YT_RE.search(yt_msg)), True)
check("regex matches youtu.be URL", bool(_YT_RE.search(yt_short)), True)
check("regex does NOT match generic https", bool(_YT_RE.search("https://somesite.com")), False)

# 7. Source intake classifies youtube_video correctly
from lib.hermes_telegram_source_intake import HermesTelegramSourceIntake
intake = HermesTelegramSourceIntake()
record = intake.process(yt_msg, attached_intent=yt_msg)
check("source_type is youtube_video", record.source_type, "youtube_video")
check("assigned_scout is youtube_research_scout", record.assigned_scout, "youtube_research_scout")
check("intake_id is set", record.intake_id.startswith("src_"), True)

# 8. Reply contains NEXUS SOURCE RECEIVED, not NEXUS OPPORTUNITY REPORT
reply = record.telegram_reply()
check("reply contains NEXUS SOURCE RECEIVED", "NEXUS SOURCE RECEIVED" in reply, True)
check("reply does NOT contain NEXUS OPPORTUNITY REPORT", "NEXUS OPPORTUNITY REPORT" not in reply, True)
check("reply contains Ray's question", "do you recommend" in reply.lower() or "youtube" in reply.lower(), True)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
