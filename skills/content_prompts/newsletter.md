# Prompt — Newsletter
_Inherits `_universal_content_rules.md`. Draft only; **no-send without Ray approval**._

**Purpose:** Turn research/content into a newsletter draft.

## Inputs
`content_id`, `topic`, `source_paths`, `audience`, `niche`, `offer`, `affiliate_disclosure_required`, `board_id`.

## Required output structure
1. **Subject lines** — 3–5 options, ≤ 50 chars, curiosity + clarity, no clickbait/guarantees.
2. **Preview text** — 1 line (~80–110 chars) that complements (not repeats) the subject.
3. **Intro** — 2–3 sentences; relatable problem + what they'll get.
4. **Main insight** — the core teaching, sourced; 2–4 short sections; scannable.
5. **Practical takeaway** — a concrete step/checklist the reader can act on today.
6. **CTA** — one clear action (reply, read, watch); value-first.
7. **Disclosure** — educational-only line; affiliate disclosure if any link/program.
8. **No-send rule** — explicitly mark: *draft only; sending requires Ray approval.*

## Output paths
- `reports/creative_short_packets/<short>_newsletter.md`

## Board + approval (sending is high-risk)
`content_board_add.py … --content-type "Newsletter" --platform "Email" --publish-risk "external/public"`;
status `Drafted` → score → `Needs Ray Review`/`Improve / Retry`. **Sending email/newsletter is a Ray-gated
action** (category `subscriber_email`, high-risk, never bulk-approved). Generate an approval card; never auto-send.
