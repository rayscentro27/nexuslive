# Prompt — YouTube Shorts
_Inherits `_universal_content_rules.md`. Internal draft only; no upload/post/schedule._

**Purpose:** Create a YouTube Short from a topic, source, transcript, publish package, research artifact,
or board card.

## Inputs (see prompt_variables_schema.md)
`content_id`, `topic`, `source_paths`/`source_urls`, `audience`, `niche`, `offer`,
`affiliate_disclosure_required`, `voice_style`, `visual_style`, `desired_length` (default 30–45s), `board_id`.

## Instruction to the model
> You are a short-form scriptwriter for the Nexus brand. Using ONLY the provided sources, write a
> 30–45 second YouTube Short. Educational tone, mobile pacing, no guarantees, no "get approved". Output the
> structured artifact below. Every claim must trace to a source.

## Required output structure
1. **Hook formula** — first line stops the scroll. Use one of: *number+pain* ("3 myths costing you time"),
   *myth-vs-truth*, *mistake callout*, *question hook*. ≤ 12 words, spoken in the first 1.5s.
2. **Pacing** — 30–45s total; one idea per scene; short spoken lines (≤ 14 words).
3. **Scene structure (3–8 scenes)** — for each: `on-screen text`, `caption`, `voiceover line`,
   `visual/b-roll direction`, `motion`. Use the myth(red)/truth(green) pattern-interrupt system when relevant.
4. **Voiceover script** — clean narration text per scene (Piper-ready).
5. **Caption text** — kinetic, 1–4 words/beat, mobile-readable.
6. **Visual / b-roll direction** — per scene; clean illustrative visuals; no misleading luxury imagery.
7. **Title** — ≤ 60 chars + " #Shorts", non-clickbait.
8. **Description** — 2–3 lines + educational disclaimer + affiliate disclosure (if links) + hashtags.
9. **Hashtags** — 5–8 niche tags.
10. **Disclosure/compliance** — educational-only line; affiliate disclosure if `offer`/links present.

## Recommended video engine (route by need)
- **HyperFrames** (primary, free/local, agent-native motion graphics) → see `hyperframes_video.md`.
- **Remotion** (branded React template, via free CI) for template-locked looks.
- **Short Video Maker** (real b-roll; paused until free Pexels key + Linux host) → `broll_short_video.md`.
- **Manual Google Flow packet** for hero-quality first public posts.

## Output paths
- Scene plan: `reports/creative_short_plans/<short>_<slug>.scenes.json` (+ `.md`)
- Publish package: `reports/publish_packages/<short>_<slug>.md`
- Draft render (HyperFrames): `reports/tool_lab/hyperframes_renders/<short>_<slug>_v1.mp4`

## Board update instructions
```
python scripts/content_board_add.py --content-id <id> --title "<title>" --content-type "YouTube Short" \
    --platform "YouTube Shorts" --status "Drafted" --next-action "render draft"
# after render:
python scripts/content_board_update.py --id <id> --status "Video Rendered" --add-preview <mp4>
```
Set `prompt_used=youtube_shorts.md`, `quality_score=<1-10>`, `generated_artifacts=[...]` on the card.

## Approval rules
Score with the rubric. **<7 → `Improve / Retry`. 7–8 → `Needs Ray Review`. 9+ → recommended candidate,
still `Needs Ray Review`.** For review-ready items run `create_content_approval_card.py --id <id> --scope review`.
Never upload/post/schedule.
