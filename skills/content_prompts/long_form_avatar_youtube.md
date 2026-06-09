# Prompt — Long-form Avatar / Host YouTube (5–10 min)
_Inherits `_universal_content_rules.md`. Draft/packet only; no upload/post/schedule._

**Purpose:** create a 5–10 minute YouTube avatar/host video **script + production packet** from research/sources.
On a GPU-less host, the avatar is delivered as a **manual hosted packet** + a free faceless-host alternative.

## Inputs
`content_id`, `topic`, `source_paths`/`source_urls`, `audience`, `niche`, `offer`, `desired_length` (default 8 min),
`affiliate_disclosure_required`, `board_id`.

## Required output structure
1. **Title** — 5 non-clickbait options ≤ 60 chars; pick the strongest + reason.
2. **Thumbnail concept** — host + 3–4 word overlay + contrast; no misleading imagery.
3. **Intro hook (0–30s)** — host promise + stakes + "stay for X"; no slow intro.
4. **Host script** — full spoken script in host voice, sectioned; short sentences; sourced claims; no hype/guarantees.
5. **Section outline** — 4–8 chapters w/ timestamps, each a sub-claim + source.
6. **Retention loops** — open loops early, payoffs later; 2–3 mid-roll re-hooks.
7. **Visual inserts** — per section: b-roll term, on-screen card, or chart (HyperFrames overlay).
8. **Chart / card moments** — where motion-graphics cards/charts replace the talking head.
9. **CTA** — value-first (subscribe / next video); affiliate disclosure if links.
10. **Shorts clips to extract** — 3–5 timestamped clip-worthy moments → route to `youtube_shorts.md` / `avatar_host_video.md`.
11. **Social derivatives** — 1 newsletter angle + 3 social captions (route to `content_repurposing.md`).
12. **Compliance / disclosure** — educational; no guarantees; disclosures present; claims sourced.
13. **Production route** — free faceless-host (HyperFrames + Piper) for the autonomous draft; manual hosted
    avatar (CapCut free; HeyGen/Symphony/Flow only if Ray approves paid) for the hero version.

## Output paths
- Packet/script: `reports/content_engine/generated/avatar_video_packets/<short>_longform_avatar_packet.md`

## Board update instructions
```
python scripts/content_board_add.py --content-id <id> --title "<title>" \
    --content-type "Long-form Avatar YouTube" --platform "YouTube" --status "Drafted" \
    --next-action "build faceless-host draft OR manual hosted packet"
# set: prompt_used=long_form_avatar_youtube.md, quality_score, generated_artifacts
```
Score with the rubric → route (<7 Improve/Retry · 7–8 Needs Ray Review · 9+ candidate). Approval card before
any publish. No upload/schedule; executor disabled.
