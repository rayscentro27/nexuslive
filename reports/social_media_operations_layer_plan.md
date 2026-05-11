# Nexus Social Media Operations Layer — Dashboard Plan
**Date:** 2026-05-11  
**Status:** Planning document — no implementation yet

---

## Overview

This document defines the future Social Media Operations dashboard to be built into the Nexus AI control center. All widgets are read-only, planning-focused, and do not connect to live platform APIs until explicitly approved.

---

## Dashboard Location

When implemented:  
`/admin/social-operations` in the Flask control center  
Access: admin token required (same as other `/admin/` routes)

---

## Planned Dashboard Widgets

### Widget 1 — Content Queue

**Purpose:** View and manage the content pipeline by status  
**Data source:** `marketing/social_content_queue.md` (manual) → future: `social_content_queue` DB table  
**Columns:** ID, Title, Platform, Format, Status, Publish Date, Owner  
**Filters:** By status, by platform, by week  
**Actions (manual only):**
- Mark as approved (human approval click)
- Move to "scheduled manually"
- Add review notes

**Safety:** No auto-posting. "Scheduled manually" means human opens platform and posts.

---

### Widget 2 — Account Inventory

**Purpose:** See all social accounts and their connection/API status at a glance  
**Data source:** `marketing/social_account_inventory.md` (manual) → future: `social_accounts` DB table  
**Columns:** Platform, Account Name, 2FA Status, API Status, Posting Status  
**Indicators:** Green (active + 2FA), Amber (needs setup), Red (missing 2FA)

---

### Widget 3 — Platform Readiness Scorecard

**Purpose:** Quick visual of which platforms are ready to publish  
**Data source:** Manual checklist state  
**Display:**
```
YouTube          [████░░░░] 40% — Channel not created
Instagram        [██░░░░░░] 20% — Account not linked to Meta Suite
Facebook Page    [████░░░░] 40% — Page created, no 2FA verified
TikTok           [░░░░░░░░]  0% — Not started
LinkedIn         [██████░░] 70% — Profile active, page pending
X/Twitter        [████░░░░] 40% — Account exists
```

---

### Widget 4 — Weekly Publishing Plan

**Purpose:** Show what's planned for the next 7 days across all platforms  
**Data source:** Content queue items with publish dates in the next 7 days  
**Display:** Calendar grid — Day × Platform  
**Manual action:** Human schedules each item directly on platform

---

### Widget 5 — Lead Magnet Clicks

**Purpose:** Track how often the free Starter Kit CTA is clicked  
**Data source:** Nexus platform analytics / link tracker  
**Metrics:** Clicks this week, clicks this month, top referring platform  
**Note:** Requires UTM parameters on CTA links — no platform API needed

---

### Widget 6 — Content Status Summary

**Purpose:** At-a-glance count of items in each pipeline stage  
**Display:**
```
Idea:              12
Drafted:            5
Reviewed:           3
Approved:           2
Scheduled manually: 1
Published:         10
Repurposed:         4
```

---

### Widget 7 — Approval Queue

**Purpose:** Show content awaiting human review/approval  
**Display:** List of drafted items needing owner review  
**Action:** Human clicks "Approve" or "Send back for revision"  
**Safety:** No content publishes without explicit approval click

---

### Widget 8 — Analytics (Future Only)

**Purpose:** Platform performance metrics  
**Status:** NOT built yet — requires API connections that are not yet approved  
**Planned data:**
- YouTube: views, subscribers, watch time
- Instagram: reach, impressions, follower growth
- TikTok: views, follows
- LinkedIn: impressions, engagements

**Requires:**
- Platform API apps created and approved
- Tokens stored securely (not in code)
- Read-only scopes only (no posting permissions)

---

## Hermes Social Media Commands

These commands will be supported by Hermes when content data is available:

| Command | Response |
|---------|---------|
| "What content should we post today?" | Returns today's approved queue items by platform |
| "What social accounts are connected?" | Returns account inventory table |
| "What content is ready for review?" | Returns all items in 'drafted' status |
| "What is this week's YouTube plan?" | Returns queue items for YouTube this week |
| "What content needs approval?" | Returns all items in 'reviewed' status awaiting approval |
| "How many pieces are in the content queue?" | Returns queue status summary counts |

**Implementation note:** These commands map to `social_media_status` intent in the Hermes intake router. No auto-posting capability. Read-only responses only.

---

## Database Schema (Future)

When the content queue moves to Supabase:

```sql
CREATE TABLE social_content_queue (
  id          TEXT PRIMARY KEY,         -- e.g. C001
  title       TEXT NOT NULL,
  platform    TEXT NOT NULL,
  format      TEXT,
  hook        TEXT,
  script_url  TEXT,
  cta         TEXT,
  status      TEXT DEFAULT 'idea',
  owner       TEXT,
  publish_date DATE,
  asset_needed TEXT,
  disclaimer_required BOOLEAN DEFAULT FALSE,
  notes       TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE social_accounts (
  id          SERIAL PRIMARY KEY,
  platform    TEXT NOT NULL,
  account_name TEXT,
  url         TEXT,
  owner       TEXT,
  tfa_enabled BOOLEAN DEFAULT FALSE,
  api_status  TEXT DEFAULT 'not_requested',
  posting_status TEXT DEFAULT 'manual_only',
  notes       TEXT,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Planning docs and markdown content queue | Complete (this pass) |
| 1 | Manual content workflow established | Pending — needs manual publishing |
| 2 | Supabase tables for queue and accounts | Future |
| 3 | Dashboard widgets (read-only) | Future |
| 4 | Hermes command integration | Future |
| 5 | API connections (read-only analytics) | Future — requires approval |
| 6 | Scheduling assistance (human approves, tool assists) | Future — requires approval |

**Auto-posting:** Not in any phase. All publishing is manual.
