# Skill: recommend-from-content

Trigger: Ray asks for recommendations from sources/content, "which content should I approve", "what should we publish", "which campaign needs content first".

## Procedure
1. Read USER.md + MEMORY.md for preferences.
2. Search relevant Nexus content/sources only (nexus_os_content_items, nexus_os_sources) — filter by status, priority, linked campaign. Do not SELECT *.
3. Build a decision matrix internally:
   | Fit | Tradeoff | Why it matters to Nexus |
4. For "which campaign needs content first": cross-reference high-priority campaigns with content_queue_count = 0.
5. For "what to approve": find items in needs_review/approval_requested with compliance complete.

## Output
- One recommendation, then at most 2 alternatives.
- Each with the tradeoff and why it matters.
- Approval needs flagged for anything public-facing.

## Rules
- Affiliate CTA requires disclosure_added before publish.
- No earnings claims, no guarantees in recommended copy.
- Summarize evidence; never dump raw rows or affiliate URLs.
