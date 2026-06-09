# Prompt — B-roll Short Video
_Inherits `_universal_content_rules.md`. Draft only; no upload/post/schedule._

**Purpose:** Create a b-roll-based Short using Pexels/free footage + Piper voice + captions, assembled with
FFmpeg/MoviePy or Short Video Maker if available.

> Note: Short Video Maker / Pexels lane is **paused** until a **free Pexels key** + a Linux render host are
> provisioned (Ray decision on the key — Pexels is free, but provisioning is an external step). Until then,
> produce the plan + script + caption + assembly packet; render via HyperFrames/FFmpeg where possible.

## Inputs
`content_id`, `topic`, `source_paths`, `audience`, `broll_keywords`, `voice_style`, `visual_style`,
`desired_length` (30–45s), `affiliate_disclosure_required`, `board_id`.

## Required output structure
1. **B-roll search terms** — 1–2 concrete, literal search terms per scene (e.g. "person at laptop",
   "calendar pages", "bar chart rising"). Free sources only (Pexels/Pixabay). **No misleading luxury/wealth imagery.**
2. **Per-scene visual mapping** — scene → b-roll clip term → spoken line → on-screen text.
3. **Caption style** — kinetic, 1–4 words/beat, high contrast, safe margins.
4. **Music / sound direction** — royalty-free bed (mood: light corporate / lo-fi); duck under VO; or no music.
5. **Voice** — Piper (`en_US-amy-medium`), local/free; clean per-scene narration.
6. **Compliance / disclosure** — educational-only line; affiliate disclosure if links; no guarantees.
7. **Output MP4 path** — `reports/tool_lab/creative_renders/<short>_broll_v1.mp4`.

## Assembly notes (free/local)
FFmpeg concat of trimmed b-roll + Piper VO + caption overlay; or Short Video Maker REST (`POST /api/short-video`)
once its Pexels key + Linux host exist. **No upload behavior** in any path.

## Board + approval
`content_board_add.py … --content-type "B-roll Short" --platform "<targets>"`; status `Video Packet Ready`/
`Video Rendered`; score → route. Approval card before any publish. Pexels key = paid-tool-style external
step → Ray. No upload/schedule.
