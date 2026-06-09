# Prompt — Avatar / Host Video
_Inherits `_universal_content_rules.md`. Draft/packet only; **no upload/post/schedule**._

**Purpose:** turn a script, podcast/audio overview, or source topic into an avatar/host-style video plan —
either a free **faceless-host** draft (HyperFrames + Piper) or a **manual hosted-avatar packet** when local
talking-avatar generation is blocked (e.g., no GPU on the build host).

## Inputs (see prompt_variables_schema.md)
`content_id`, `topic`/script (`source_paths`), `voice_style` + voiceover wav (Piper), `visual_style`,
`target_platform`, `audience`, `desired_length`, `board_id`.

## Required output structure
1. **Host role** — what the host does (advisor/teacher/analyst); tone (calm, credible, no-hype).
2. **Avatar / persona description** — clean business host / virtual advisor; faceless or stylized; **no real
   person's likeness, no creator impersonation**; Nexus palette.
3. **Voice style** — Piper (`en_US-amy-medium`) local/free, or a provided wav; confident, clear, friendly.
4. **Shot list** — per shot: host framing (talking-head / over-shoulder / full), on-screen focus, b-roll insert.
5. **Scene timing** — per-scene seconds synced to the voiceover; total = target length.
6. **Lower-thirds** — name/title bar text (e.g. "Nexus · Business Credit"), per-section labels.
7. **Motion graphics** — HyperFrames overlays: key-point cards, myth/truth flips, charts, accent bars.
8. **Captions** — kinetic, mobile-readable, high-contrast (HyperFrames `.clip` or Whisper `init --audio`).
9. **B-roll inserts** — literal, free-source terms per shot; **no misleading luxury/wealth imagery**.
10. **Compliance / disclosure** — educational-only line; affiliate disclosure if links; no guarantees; claims sourced.
11. **Manual hosted-tool packet (if local avatar blocked)** — exact step list for CapCut (free assembly) +,
    only if Ray approves a paid/manual tool, HeyGen/Symphony/Google Flow: host setup, script paste, voice,
    export settings. **No accounts connected, no posting.**
12. **No-upload rule** — draft/packet only; publishing requires scoped Ray approval; executor stays disabled.

## Routes
- **Free autonomous (this host):** faceless-host HyperFrames composition + Piper VO → draft MP4
  (`reports/tool_lab/hyperframes_renders/`). Route the overlays via `hyperframes_video.md`.
- **Hero/manual:** hosted-avatar packet (CapCut free; HeyGen/Symphony/Flow only if Ray approves paid).

## Output paths
- Packet: `reports/content_engine/generated/avatar_video_packets/<short>_avatar_host_packet.md`
- Draft render (faceless host): `reports/tool_lab/hyperframes_renders/<short>_avatar_host_v1.mp4`

## Board + approval
`content_board_add.py … --content-type "Avatar/Host Video"`; status by quality (`<7 Improve/Retry · 7–8 Needs
Ray Review · 9+ candidate`). Approval card via `create_content_approval_card.py`. Never self-advance to Approved*/Published.
