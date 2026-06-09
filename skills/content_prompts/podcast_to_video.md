# Prompt — Podcast-to-Video Clips
_Inherits `_universal_content_rules.md`. Internal draft only; no upload/post/schedule._

**Purpose:** Turn a podcast / audio-overview script into video clips.

## Inputs
`content_id`, podcast script path, audio path, `audience`, `visual_style`, `target_platform`, `board_id`.

## Required output structure
1. **Character / host roles** — name + persona + on-brand color for each speaker (e.g. NOVA blue / REX red→green).
2. **Avatar / talking-character route** — only if a **free/local** tool exists; otherwise speaker name-cards
   over motion graphics. Paid avatar (HeyGen/D-ID) = manual packet, never autonomous spend.
3. **HyperFrames motion-graphics route** — map each dialogue turn to a scene (name card + kinetic transcript
   + waveform + myth/truth pattern interrupt). Route to `hyperframes_video.md`.
4. **Captions** — kinetic, word-timed (Whisper `init --audio` optional), high contrast.
5. **Quote cards** — 2–3 standout lines as bold quote frames.
6. **30-second clip plan** — one moment, hook-first, single idea.
7. **60-second clip plan** — 2–3 moments, mini arc.
8. **Platform metadata** — YouTube Shorts title/description/hashtags · LinkedIn snippet · TikTok caption.
9. **Manual route** — Google Flow / Symphony / CapCut packet if higher production is needed (Ray-run, manual).

## Output paths
- Packet: `reports/creative_short_packets/<short>_podcast_to_video_packet.md`
- Draft clips: `reports/tool_lab/hyperframes_renders/<short>_clip_*.mp4`

## Board + approval
`content_board_add.py … --content-type "Podcast-to-Video"`; status `Video Packet Ready` → render → `Video
Rendered` → score → `Needs Ray Review`/`Improve / Retry`. Approval card before publish. No upload/schedule.
