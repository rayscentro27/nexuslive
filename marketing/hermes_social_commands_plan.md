# Hermes Social Media Command Planning Doc
**Last Updated:** 2026-05-11  
**Status:** Planning only — no auto-posting, no platform API connections  
**Purpose:** Define how Hermes will answer social media planning questions

---

## Supported Commands (Read-Only, Planning Only)

These commands return information from the content queue and account inventory.  
They do not post, schedule, or interact with any social platform API.

---

### "What content should we post today?"

**Intent:** `social_today_content`  
**Response type:** List of queue items with `publish_date = today` AND `status IN ('approved', 'scheduled manually')`  
**Format:**

```
📅 Today's content plan (2026-05-11):

▸ [C002] YouTube Shorts + Reels — "5 steps to fund your business in 90 days"
  Status: approved | CTA: Free Starter Kit | Disclaimer: No
  Asset: Script ready, needs recording

▸ [C003] TikTok — "This grant closes in 30 days"
  Status: scheduled manually | CTA: Comment GRANTS | Disclaimer: No
  Asset: Video ready

ℹ️  All publishing is manual. No auto-posting is enabled.
```

---

### "What social accounts are connected?"

**Intent:** `social_account_status`  
**Response type:** Account inventory summary  
**Format:**

```
📱 Nexus Social Account Status:

YouTube          → Not yet created
Instagram        → Not yet created
Facebook Page    → Not yet created
TikTok           → Not yet created
LinkedIn         → Profile active (Company page pending)
X/Twitter        → Not yet created

API access: None requested.
Auto-posting: Disabled on all accounts.
```

---

### "What content is ready for review?"

**Intent:** `social_review_queue`  
**Response type:** Queue items with `status = 'drafted'`  
**Format:**

```
📝 Content awaiting review (3 items):

▸ [C004] YouTube — "I built an AI that does grant research for me"
  Platform: YouTube + LinkedIn | Format: Long
  Drafted by: Raymond | Last updated: 2026-05-10

▸ [C007] TikTok — "Your EIN is sitting there doing nothing"
  Platform: Reels + TikTok | Format: Short
  Drafted by: Raymond | Last updated: 2026-05-09

▸ [C009] YouTube + Reels — "Side hustle to business in 60 days"
  Platform: YouTube + Reels | Format: Short + Long
  Drafted by: Raymond | Last updated: 2026-05-08

Action: Review and mark 'reviewed' or return with notes.
```

---

### "What is this week's YouTube plan?"

**Intent:** `social_youtube_week`  
**Response type:** YouTube queue items for the current week  
**Format:**

```
🎬 YouTube plan for week of 2026-05-11:

Monday (5/11):    [C001] "How to Build Business Credit from Zero" — idea phase
Wednesday (5/13): [C002] "5 Steps to Fund Your Business in 90 Days" — approved
Friday (5/15):    [C008] "What is Business Credit" — drafted

Shorts (cross-post from above):
  C002 → post to YouTube Shorts same day as long-form

Note: 0 videos have been recorded this week. 1 is approved and ready.
```

---

### "What content needs approval?"

**Intent:** `social_approval_queue`  
**Response type:** Queue items with `status = 'reviewed'`  
**Format:**

```
✅ Content awaiting your approval (2 items):

▸ [C005] "LLC vs Sole Prop — Which One Actually Protects You?"
  Platforms: YouTube Shorts + TikTok
  Format: Short | Disclaimer: No | CTA: Comment LLC
  Reviewed: Yes | Next step: Approve to move to recording

▸ [C010] "Paper Trading 101"
  Platforms: YouTube
  Format: Long | ⚠️ Disclaimer: REQUIRED (trading content)
  Reviewed: Yes | Next step: Approve after confirming disclaimer is in script

Approve each item manually to move to 'approved' status.
```

---

## Hermes Intake Map Entry (Future)

When implemented in `hermes_command_router/intake.py`:

```python
(
    ["what content should we post today", "today's content", "what to post today",
     "social post today", "content for today"],
    "social_today_content", "low", False
),
(
    ["what social accounts are connected", "social account status", "which accounts are live",
     "are our social accounts set up", "social media accounts"],
    "social_account_status", "low", False
),
(
    ["what content is ready for review", "content review queue", "what needs review",
     "content waiting for review", "drafts to review"],
    "social_review_queue", "low", False
),
(
    ["what is this week's youtube plan", "youtube plan this week", "youtube schedule",
     "what youtube videos are planned"],
    "social_youtube_week", "low", False
),
(
    ["what content needs approval", "content approval queue", "approve content",
     "what needs to be approved", "content to approve"],
    "social_approval_queue", "low", False
),
```

---

## What Hermes Will NOT Do

| Action | Status |
|--------|--------|
| Post to any social platform | NEVER — not implemented |
| Schedule posts automatically | NEVER — manual only |
| Send DMs on behalf of Nexus | NEVER |
| Access platform APIs | Not until explicitly approved |
| Generate and auto-publish content | NEVER |
| Comment on behalf of Nexus | NEVER |

---

## Implementation Notes

- Phase 0 (this pass): Planning doc only
- Phase 1: Add `social_today_content` and `social_review_queue` intents to intake.py (read from markdown or future DB table)
- Phase 2: Add Supabase `social_content_queue` table and wire Hermes to query it
- Phase 3: Add dashboard widget support in control center

No API connections required for Phase 0 or Phase 1.
