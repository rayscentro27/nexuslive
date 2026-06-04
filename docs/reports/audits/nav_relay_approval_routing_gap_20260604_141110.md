# Hermes Routing Gap: Nav.com and Relay Approval Misrouted
**Date:** 2026-06-04  
**Type:** Routing gap documentation  
**Status:** Documented — fix required in future cleanup phase

---

## What Happened

Ray sent:
> "ok lets do nav first and then relay"  
> "i approve nav.com and relay"

Hermes routed both messages into the generic **bulk approval safety check**, which contained:
- Lesson approvals (unrelated)
- Lead magnet public-use approval (unrelated)
- Newsletter subscriber email approval (unrelated)
- Short video script social posting approval (unrelated)

None of these items were what Ray intended to approve.

---

## Correct Interpretation

These messages should have been routed to a **funding_readiness_monetization_approval** intent:

- Ray is selecting monetization paths for internal preparation in the Funding Readiness Funnel context.
- "I approve Nav.com and Relay" = "I choose Nav.com and Relay as the paths to prepare internally."
- This is NOT a bulk approval of unrelated queue items.
- Scope is limited to internal preparation: CTA drafts, placement options, approval records.
- No affiliate applications, live links, publishing, or emails are authorized.

---

## Root Cause

The `approval_bulk_request` pattern in `hermes_cfo_brain` and the generic bulk-approval handler matched on phrases like:
- "i approve"
- "i approve them all"
- "approve all"

When Ray said "i approve nav.com and relay", the phrase "i approve" was matched and routed to the generic bulk approval queue — which happened to contain unrelated lessons, lead magnets, and video scripts.

The system had no `funding_readiness_monetization_approval` intent and no context-aware routing for "I approve [named program]" in the Funding Readiness Funnel context.

---

## Impact

- No unsafe actions were taken (bulk approval safety check did not auto-approve high-risk items).
- Ray's actual intent was not fulfilled by the Telegram response.
- Hermes responded with a list of unrelated items instead of confirming Nav.com and Relay selection.
- The approval artifact for Nav.com and Relay was not created automatically.
- This task exists to correct the record manually.

---

## Recommended Fix (Future Cleanup Phase)

### 1. Add `funding_readiness_monetization_approval` intent

Add to `hermes_cfo_brain` / `hermes_command_router`:

```python
"funding_readiness_monetization_approval": [
    r"i approve nav", r"approve nav.com", r"nav.com and relay",
    r"i approve relay", r"approve relay", r"lets do nav",
    r"nav first.*relay", r"approve.*monetization path",
    r"approve.*affiliate.*choice",
]
```

### 2. Context-aware routing condition

When the active topic is `funding_readiness_funnel` or `monetization_selection`:
- "I approve [program names]" → `funding_readiness_monetization_approval`
- NOT → `approval_bulk_request`

### 3. Named-program approval handler

Build a handler that:
- Accepts named programs (Nav.com, Relay, D&B, etc.)
- Confirms scope as internal preparation only
- Creates approval artifact automatically
- Does NOT route to generic bulk approval queue

### 4. Disambiguation gate

When a message says "I approve" + proper nouns (company names):
- Check if the names match known affiliate/monetization programs in research reports
- If yes: route to `funding_readiness_monetization_approval`
- If no: fall through to generic `approval_bulk_request`

---

## Hermes Lesson Proposal (Local Only — Not Written to Supabase)

**Lesson:** When Ray says "I approve Nav.com and Relay" (or similar named-program approval) in the Funding Readiness Funnel context, Hermes should interpret that as approval of the monetization path for internal preparation only. It should NOT route to the generic bulk approval queue containing unrelated lessons, lead magnets, or video scripts.

**Trigger context:** Message contains "I approve" + known affiliate program names (Nav.com, Relay, D&B, etc.) + active funnel context is funding_readiness_funnel.

**Correct intent:** `funding_readiness_monetization_approval`

**Correct scope:** Internal preparation only. No applications, live links, publishing, emails.

**Status:** Proposed locally. Writing to Hermes memory (hermes_memory_v2) requires separate explicit Ray approval through the existing learning loop.

---

## Files Created to Correct the Record

- `docs/reports/approvals/nav_relay_internal_monetization_approval_20260604_141110.md`
- `docs/reports/approvals/nav_relay_internal_monetization_approval_20260604_141110.json`
- `docs/reports/funnel/funding_readiness_monetization_decision_20260604_141110.md`
- `docs/reports/funnel/funding_readiness_monetization_decision_20260604_141110.json`
- `docs/reports/funnel/nav_relay_cta_placement_draft_20260604_141110.md`
- `docs/reports/audits/nav_relay_approval_routing_gap_20260604_141110.md` (this file)
