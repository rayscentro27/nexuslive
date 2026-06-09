# Prompt — YouTube Viral Pattern Research
_Inherits `_universal_content_rules.md`. Research + original drafting only; **no upload/post/schedule**._

**Purpose:** Study successful public YouTube videos in Nexus niches to learn **what works** (hook/title/
format/pacing patterns), then produce **original** Nexus faceless content from those proven patterns —
never copies. Reuses the existing scouts (do not build a duplicate): discovery via
`scripts/run_monetization_research_cycle.py` (free yt-dlp `ytsearch`), transcripts + hook/title extraction
via `lib/youtube_intelligence_worker.py` / `lib/youtube_intelligence_extractor.py` (free heuristic path),
quality/compliance via `lib/youtube_quality_reviewer.py`, persistence via `source_extractions`.

## Hard rules (model, don't copy)
- **Analyze patterns ONLY.** Learn the *structure* (hook type, title formula, format, pacing, length, thumbnail cue).
- **Never copy scripts or wording.** No verbatim lines from any source transcript.
- **Never reuse copyrighted footage, audio, thumbnails, or B-roll** from the source.
- **Never impersonate a creator**, channel, or brand; no "[Creator]'s method"; no logos/faces of others.
- **Always generate ORIGINAL Nexus scripts and visuals** with our own angle, palette, and voice.
- Educational only; no guarantees; affiliate disclosure when links are used; claims traced to sources.
- **No paid APIs by default** — use the free discovery + heuristic extraction paths; any paid LLM use is Ray-gated.

## Inputs (see prompt_variables_schema.md)
`niche`, `topic`/keywords, `audience`, `source_urls` (optional seeds), `target_platform`, `board_id`.

## Process
1. **Discover** (free): run keyword search via the monetization research cycle (dry-run) → candidate videos
   with `view_count`/recency. Rank by a popularity+fit signal (views × recency × niche fit).
2. **Study** top candidates: reuse transcript + hook/title/viral-angle extraction (free heuristic path).
3. **Distill** each into a `viral_pattern_card` (structure only — see below).
4. **Score** originality + compliance (must be model-not-copy; compliance ≤5 → Improve/Retry).
5. **Generate original** Nexus drafts from the pattern → route to `youtube_shorts.md` →
   `hyperframes_video.md` → `content_repurposing.md`.

## Output 1 — `viral_pattern_card` (save to `reports/content_engine/viral_patterns/`)
```
pattern_id · source_extraction_id · source_video_id · niche · views · published
hook_formula (the TYPE, e.g. "number+pain") · title_formula (pattern, not the exact title)
format (myth-vs-truth | listicle | story | tutorial) · pacing · length · thumbnail_cue
why_it_works · originality_note ("pattern only — no script/footage reuse") · compliance_flags[] · nexus_angle
```

## Output 2 — original Nexus draft (via youtube_shorts.md)
A new, original script using the proven **structure** with Nexus's own words, examples, and visuals.
Disclosure + educational-only line included. No source wording, no source footage.

## Source / extraction saving
- `source_extractions` via the existing pipeline (Supabase, dry-run/proposed by default) — reuse, no new table.
- Pattern cards as local files (file-based first; no DB migration).

## Board update
```
python scripts/content_board_add.py --content-id <id> --status "Researched" \
    --content-type "YouTube Short" --next-action "draft original from pattern vp-<id>"
# set on the card: prompt_used=youtube_viral_pattern_research.md, parent_source_id=<source_extraction id>
```
Merge-only (never clobber). Score the original draft with `content_quality_rubric.md`:
**<7 → Improve / Retry · 7–8 → Needs Ray Review · 9+ → candidate (still Ray-gated).**

## Approval rules
Research + original drafting are autonomous. **Ray approval is required before any upload/post/schedule.**
The publish path (`social_publish_executor.py`) stays disabled by default. Generate an approval card
(`create_content_approval_card.py`) for review-ready drafts; never publish.
