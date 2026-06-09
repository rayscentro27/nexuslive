# Prompt — Blog / SEO Article
_Inherits `_universal_content_rules.md`. Draft only; no publish/schedule._

**Purpose:** Turn research/content into an SEO blog outline or draft.

## Inputs
`content_id`, `topic`, target keyword(s), `source_paths`/`source_urls`, `audience`, `niche`, `offer`,
`affiliate_disclosure_required`, `board_id`.

## Required output structure
1. **Keyword intent** — primary keyword + search intent (informational/commercial) + 3–5 secondary keywords.
2. **Title / meta description** — title ≤ 60 chars with keyword; meta ≤ 155 chars, compelling, accurate.
3. **H2 / H3 structure** — full outline; each H2 a sub-topic answering intent; H3s for specifics; logical flow.
4. **Internal link suggestions** — 3–5 anchor → target ideas (other Nexus articles/pages); note as suggestions.
5. **FAQ section** — 4–6 real questions (People-Also-Ask style) with short, accurate answers.
6. **Source citations needed** — list every claim that requires a citation + which source covers it.
7. **CTA** — value-first (read next / try the checklist); affiliate disclosure if links.
8. **Compliance notes** — educational tone; no guarantees; E-E-A-T (clarity, accuracy, sourced claims).

## Output paths
- Outline/draft: `reports/creative_short_packets/<short>_blog_seo.md`

## Board + approval
`content_board_add.py … --content-type "Blog/SEO" --platform "Blog"`; status `Drafted` → score → route.
Publishing to a live site is a Ray-gated external action. Approval card before publish. No auto-publish.
