# Skill: recommend-revenue-action

Trigger: Ray asks about money, revenue, "how do we make money next", "what's closest to paying".

## Procedure
1. Read MEMORY.md for live revenue state.
2. Look at nexus_os_revenue_campaigns: priority, application_status, link_status, landing_page_status, compliance_ok, disclosure_ok, content_queue_count.
3. Look at nexus_os_content_items linked to those campaigns: how many drafts exist per campaign, their status.
4. Look at owner_approval_queue for anything revenue-related already pending.
5. Rank campaigns by readiness-to-revenue: closest to launch with fewest blockers and highest priority wins.

## Output
- The single campaign closest to revenue, and why.
- Its current blocker.
- The exact next action (e.g., "apply to the program", "draft 3 content pieces", "add disclosure").
- Approval needed before publish/activate? yes/no.

## Rules
- Never claim projected or guaranteed earnings — no evidence exists for those.
- Affiliate CTA requires disclosure before any publish recommendation.
- Funding/credit content stays educational; no approval/result guarantees.
- Query only relevant fields. Summarize; don't dump rows.
