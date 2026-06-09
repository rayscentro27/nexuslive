# Prompt — Performance Improvement (24h / 72h)
_Inherits `_universal_content_rules.md`. Analysis + draft revision only; no publish/schedule._

**Purpose:** Improve future content based on 24h/72h performance data for an already-published item.

## Inputs
`content_id`, `board_id`, performance data (views, retention/avg view duration, CTR, saves, comments,
follows), the original artifact + metadata. Read-only on our own posts; paid analytics APIs are Ray-gated.

## Required output structure
1. **Hook diagnosis** — did the first 1–3s hold? If retention drops < 70% by 3s, the hook is the problem;
   propose 3 stronger hooks.
2. **Retention diagnosis** — find the biggest drop-off point; hypothesize why (pacing, dead air, weak middle);
   propose a fix (tighter cut, re-hook, reorder).
3. **Title / thumbnail diagnosis** — if impressions high but CTR low, fix title/thumbnail; propose 3 titles + 1 thumbnail idea.
4. **Caption diagnosis** — readability, timing, length; propose adjustments.
5. **Revised script** — a concrete v2 script incorporating the fixes (route to the original content-type prompt).
6. **Next test recommendation** — one specific A/B (hook vs hook, title vs title) to run next.
7. **Knowledge graph update** — record what worked/failed: link source ↔ script ↔ render ↔ metric ↔ lesson.
8. **Board move** — based on score of the revised plan:
   - revised plan **< 7/10** or needs another pass → **`Improve / Retry`**
   - revised plan **≥ 7/10** and ready for a new draft/render → **`Needs Ray Review`** (after re-render)

## Output paths
- Diagnosis + revision: `reports/content_engine/prompt_library/examples/<short>_performance_review.md`

## Board + approval
`content_board_update.py --id <id> --performance-status "<24h/72h summary>" --status "<Improve / Retry|Needs
Ray Review>" --next-action "..."`. Set `prompt_used=performance_improvement.md`. Any re-publish requires Ray approval.
