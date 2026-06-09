# Prompt — Content Repurposing (one source → a content family)
_Inherits `_universal_content_rules.md`. Draft only; no publish/schedule._

**Purpose:** Turn one source (video, transcript, research artifact, long-form, podcast) into a full content
family, linked by a shared `content_family` id and `parent_source_id`.

## Inputs
`content_id` (parent), `parent_source_id`, `topic`, `source_paths`, `audience`, `niche`, `offer`,
`affiliate_disclosure_required`, `board_id`.

## Required outputs (the family)
1. **1 YouTube Short** — route to `youtube_shorts.md` (script + metadata).
2. **1 LinkedIn post** — route to `linkedin_post.md` (pick the strongest of 3).
3. **1 newsletter snippet** — 80–150 words (route to `newsletter.md` for full version).
4. **1 blog outline** — route to `blog_seo_article.md`.
5. **3 social captions** — short, platform-flexible, each from a distinct angle.
6. **3 quote cards** — standout lines as bold quote frames (text + suggested visual).
7. **1 podcast / audio-overview angle** — route to `notebooklm_podcast_audio_overview.md`.

## Linking
Assign one `content_family` id (e.g. `fam-<short>`); set `parent_source_id` on every derived card.
Each derived asset gets its own board card but shares the family id for tracking and the Knowledge Graph.

## Output paths
- Family index: `reports/creative_short_packets/<short>_content_family.md`
- Each asset saved per its own prompt's output path.

## Board card update instructions
For each asset:
```
python scripts/content_board_add.py --content-id <asset_id> --title "..." --content-type "<type>" \
    --platform "<targets>" --status "Drafted" --next-action "score + route"
# then set on each card: prompt_used, quality_score, content_family=fam-<short>, parent_source_id=<parent>
```
Score each asset independently → route (<7 Improve/Retry · 7–8 Needs Ray Review · 9+ candidate). Approval cards
per publish-ready asset. No upload/post/schedule.
