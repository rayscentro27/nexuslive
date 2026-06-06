# Skill: recommend-next-nexus-step

Trigger: Ray asks "what next?", "what should I do today?", "what's the highest-impact move?"

## Procedure
1. Read USER.md + MEMORY.md for preferences and live state.
2. Check Revenue Hub state (nexus_os_revenue_campaigns): which campaigns exist, priority, application_status, compliance, blockers.
3. Check Content Studio state (nexus_os_content_items): drafts, status, linked campaigns, what's awaiting approval.
4. Check pending approvals (owner_approval_queue, status=pending).
5. Identify the single highest-impact next step. Prioritize: (a) speed to revenue, (b) safety/approval gates, (c) unblocking current blockers.

## Output
- One clear recommendation first.
- Why it matters (with the concrete evidence that drove it).
- The blocker, if any.
- Approval needed? yes/no.
- At most 2 alternatives if useful.

## Rules
- Do not SELECT *. Query only the fields needed.
- Do not execute anything. If the step is risky, recommend preparing an approval.
- Do not claim projected earnings.
