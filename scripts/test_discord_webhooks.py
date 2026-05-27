"""
Test all three Discord webhook channels with realistic example payloads.
Usage: python3 scripts/test_discord_webhooks.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v

from lib.discord_notifier import ceo, content, ops, verify_webhooks, configured_channels

print("=" * 60)
print("NEXUS DISCORD WAR ROOM — WEBHOOK TEST")
print("=" * 60)

# 1. Check configuration
print("\n1. Channel Configuration:")
channels = configured_channels()
for ch, ok in channels.items():
    print(f"   {'✅' if ok else '❌'} {ch.upper()}: {'configured' if ok else 'MISSING webhook URL'}")

if not any(channels.values()):
    print("\n❌ No webhooks configured. Check .env for DISCORD_*_WEBHOOK vars.")
    sys.exit(1)

print("\n2. Verifying webhooks (ping each channel)...")
results = verify_webhooks()
for ch, ok in results.items():
    print(f"   {'✅' if ok else '❌'} {ch.upper()}: {'OK' if ok else 'FAILED'}")

time.sleep(3)

# 3. CEO briefing example
print("\n3. Sending CEO briefing example...")
sample_briefing = """# NEXUS EXECUTIVE BRIEFING — 2026-05-26
**08:00 | Mission: $1,000/week | DRY_RUN=true | NO LIVE TRADING**

---

## 1. REVENUE PROGRESS
**Weekly Target:** $1,000/week
- Newsletter subscribers: 0 / 250 target
- Affiliate clicks: 0 / 500 target
- Content outputs this week: 2 / 15 target

## 2. SYSTEM HEALTH
**Status:** OPERATIONAL
- Active workers: 3 | Stalled: 0
- PM2: nexus-watchers ✅ | nexus-executor ✅ | nexus-claw3d ✅

## 3. MONETIZATION OPPORTUNITIES
- [CRITICAL] Fix content engine LLM — OpenRouter now routing to deepseek-r1
- [CRITICAL] Launch Beehiiv newsletter — 250 subscriber target
- [HIGH] SEO article batch — 20 articles targeting funding keywords

## 4. TOP PRIORITY ACTIONS
1. Complete Beehiiv newsletter setup
2. Run first full content pipeline
3. Submit Lendio affiliate application
4. Add YouTube Studio profile links
"""
ok = ceo.send_briefing(sample_briefing)
print(f"   {'✅' if ok else '❌'} CEO briefing: {'sent' if ok else 'FAILED'}")

time.sleep(3)

# 4. KPI update
print("\n4. Sending KPI update...")
ok = ceo.send_kpi_update({
    "newsletter_subscribers": "0 / 250",
    "affiliate_clicks":       "0 / 500",
    "weekly_revenue_usd":     "$0 / $1,000",
    "funding_leads":          "0 / 15",
    "content_outputs_week":   "2 / 15",
    "seo_articles":           "0 / 20",
})
print(f"   {'✅' if ok else '❌'} KPI update: {'sent' if ok else 'FAILED'}")

time.sleep(3)

# 5. Content draft example
print("\n5. Sending content draft example...")
ok = content.send_draft(
    content_type="youtube_script",
    title="How to Build Business Credit Fast (Even With Bad Personal Credit)",
    body="""TITLE: How to Build Business Credit Fast (Even With Bad Personal Credit)
TARGET KEYWORD: build business credit fast

HOOK (0:00-0:30):
Most business owners don't realize their personal credit score doesn't matter for business funding. Here's what banks actually look at — and how to game it in 30 days.

INTRO (0:30-1:30):
Today I'm going to show you the exact steps to build a PAYDEX score of 80+ in 30 days, qualify for net-30 vendor accounts, and unlock $50,000+ in business credit without a personal guarantee.

SECTION 1 — The Credit Separation (1:30-3:00):
Step 1: Get your EIN from IRS.gov — free, 10 minutes.
Step 2: Open a dedicated business checking account.
Step 3: Register with Dun & Bradstreet for free DUNS number.

SECTION 2 — The Vendor Ladder (3:00-5:00):
Start with net-30 vendors that report to business bureaus:
• Uline (office supplies)
• Grainger (industrial)
• Quill (office)
Buy small. Pay on time. PAYDEX score builds in 60 days.

CTA (last 30s):
Get the free Business Credit Checklist at goclearonline.cc
""",
    topic="business credit building",
    word_count=187,
    quality_score=82,
    row_id="abc123-def456",
)
print(f"   {'✅' if ok else '❌'} YouTube script draft: {'sent' if ok else 'FAILED'}")

time.sleep(3)

# 6. Content pipeline summary
print("\n6. Sending pipeline summary example...")
ok = content.send_pipeline_summary(
    date="2026-05-26",
    topic="business credit building",
    outputs=[
        {"type": "youtube_script",  "words": 850,  "row_id": "row-001"},
        {"type": "newsletter",      "words": 480,  "row_id": "row-002"},
        {"type": "seo_article",     "words": 1240, "row_id": "row-003"},
        {"type": "linkedin_post",   "words": 210,  "row_id": "row-004"},
        {"type": "tiktok_hook",     "words": 18,   "row_id": "row-005"},
        {"type": "x_post",          "words": 22,   "row_id": "row-006"},
    ],
    errors=[],
)
print(f"   {'✅' if ok else '❌'} Pipeline summary: {'sent' if ok else 'FAILED'}")

time.sleep(3)

# 7. System ops alerts
print("\n7. Sending system ops examples...")
ok1 = ops.send_pm2_status([
    {"name": "nexus-watchers",      "status": "online",  "restarts": 0, "memory": "71MB"},
    {"name": "nexus-executor",      "status": "online",  "restarts": 0, "memory": "28MB"},
    {"name": "nexus-claw3d",        "status": "online",  "restarts": 0, "memory": "136MB"},
    {"name": "nexus-claw3d-adapter","status": "online",  "restarts": 0, "memory": "39MB"},
])
print(f"   {'✅' if ok1 else '❌'} PM2 status: {'sent' if ok1 else 'FAILED'}")

time.sleep(3)

ok2 = ops.send_openrouter_health(healthy=True, model="deepseek/deepseek-r1", latency=2.4)
print(f"   {'✅' if ok2 else '❌'} OpenRouter health: {'sent' if ok2 else 'FAILED'}")

time.sleep(3)

ok3 = ops.alert(
    "warning",
    "Ollama offline — local model unavailable",
    detail="localhost:11555 not responding. Content routing to OpenRouter (deepseek-r1). No action needed unless budget concern.",
    fields=[
        {"name": "Fallback", "value": "openrouter:deepseek/deepseek-r1", "inline": True},
        {"name": "Impact",   "value": "Low — content still generating", "inline": True},
    ],
)
print(f"   {'✅' if ok3 else '❌'} Ops warning: {'sent' if ok3 else 'FAILED'}")

# Summary
print("\n" + "=" * 60)
all_ok = all([ok, ok1, ok2, ok3])
print(f"RESULT: {'✅ ALL WEBHOOKS OPERATIONAL' if all_ok else '⚠️  SOME WEBHOOKS FAILED'}")
print()
print("Active routing map:")
print("  CEO Command    → morning briefing, KPIs, opportunities, priority actions")
print("  Content Engine → YouTube scripts, newsletters, SEO articles, pipeline summaries")
print("  System Ops     → PM2 status, watcher alerts, OpenRouter health, failures")
print()
print("Discord is now the live operational visibility layer for Nexus.")
