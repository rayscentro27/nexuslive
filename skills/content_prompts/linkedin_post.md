# Prompt — LinkedIn Post
_Inherits `_universal_content_rules.md`. Draft only; no auto-posting._

**Purpose:** Turn research/content into a LinkedIn post.

## Inputs
`content_id`, `topic`, `source_paths`, `audience`, `niche`, `offer`, `affiliate_disclosure_required`, `board_id`.

## Required output structure (produce **3 alternate versions**)
1. **Authority hook** — line 1 stops the scroll with a credible, specific claim or contrarian truth
   (no hype, no "🚀 millionaire" energy).
2. **Short-form educational structure** — 3–6 short paragraphs / line breaks; one insight, made practical;
   skimmable; native formatting (no markdown headers, sparse emojis).
3. **No hype/guarantees** — ban income/approval/guarantee claims; keep it credible and useful.
4. **CTA** — soft: a question to drive comments, or "save this", or "follow for more". No spam links.
5. **Disclosure if affiliate** — include the affiliate disclosure line if any link/program is present.
6. **Platform-safe formatting** — ≤ ~1,300 chars ideal; first 2 lines carry the hook (before "see more").
7. **3 alternate versions** — (a) myth-vs-truth, (b) story/lesson, (c) listicle/framework.

## Output paths
- `reports/creative_short_packets/<short>_linkedin.md` (all 3 versions + compliance notes)

## Board + approval
`content_board_add.py … --content-type "LinkedIn Post" --platform "LinkedIn"`; status `Drafted` → score →
`Needs Ray Review`/`Improve / Retry`. **No auto-posting** — Ray approval required to publish. Approval card
via `create_content_approval_card.py`.
