# Prompt — Long-form YouTube (6–12 min)
_Inherits `_universal_content_rules.md`. Internal draft only; no upload/post/schedule._

**Purpose:** Create a 6–12 minute YouTube video plan/script from research/sources.

## Inputs
`content_id`, `topic`, `source_paths`/`source_urls`, `audience`, `niche`, `offer`, `desired_length`
(default 8 min), `affiliate_disclosure_required`, `board_id`.

## Required output structure
1. **Title ideation** — 5 non-clickbait titles, ≤ 60 chars; pick the strongest with a one-line reason.
2. **Thumbnail concept** — 1–2 ideas: subject, 3–4 word text overlay, color contrast; no misleading imagery.
3. **Intro hook (0–30s)** — promise + stakes + "stay for X"; no slow logo intro.
4. **Retention loops** — open loops at the start, pay them off later; note 2–3 mid-roll re-hooks.
5. **Sections / chapters** — 4–8 chapters with timestamps, each a clear sub-claim + source.
6. **CTA** — value-first (subscribe / next video), not hype.
7. **Description** — summary + chapters + educational disclaimer + affiliate disclosure (if links) + links placeholder.
8. **Pinned comment** — one engaging question or resource pointer.
9. **Clip opportunities for Shorts** — 3–5 timestamped clip-worthy moments → route each to `youtube_shorts.md`.
10. **Newsletter / social derivatives** — 1 newsletter angle + 3 social captions (route to repurposing).
11. **Compliance checks** — no guarantees; claims sourced; disclosures present.

## Output paths
- Plan/script: `reports/creative_short_plans/<short>_longform.md`
- Derivative seeds logged for repurposing.

## Board + approval
`content_board_add.py … --content-type "Long-form YouTube" --platform "YouTube"`; status `Drafted` →
score → `Needs Ray Review`/`Improve / Retry`. Approval card before any publish. No upload/schedule.
