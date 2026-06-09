# Prompt — HyperFrames Video (agent-native HTML/CSS/JS → MP4)
_Inherits `_universal_content_rules.md`. Draft render only; **no upload/post/schedule**._

**Purpose:** Generate agent-native HTML/CSS/JS video instructions for the HyperFrames renderer
(Apache-2.0, free/local; proven to render locally on macOS 12).

## Inputs
`content_id`, scene plan (`*.scenes.json`) or dialogue turns, `voice_style` + voiceover wav path,
`visual_style`, `broll_keywords`, branding, `board_id`. Adapter: `scripts/export_creative_plan_to_hyperframes.py`.

## Required output structure
1. **Scene layout** — per scene: background (Nexus palette: navy #1A2244, blue #5B7CFA, red #FF4D4D,
   green #27D17F), big on-screen headline, caption pill, optional badge/stamp (myth ✕ / truth ✓).
2. **Timing** — per-scene `data-start` / `data-duration` synced to the voiceover timing JSON; 30fps;
   total = sum of scene durations.
3. **Motion instructions** — seekable GSAP timeline registered at `window.__timelines["main"]`; per scene:
   reveal (scale/opacity/back.out), accent-bar wipe, caption rise, hard `tl.set(opacity:0)` at scene end
   (avoids stale visibility on non-linear seeking — the linter requires this).
4. **Captions** — `.clip` caption divs (kinetic) OR `hyperframes init --audio <wav>` local Whisper captions.
5. **Voiceover input** — single `<audio id="vo" …>` track (Piper wav); must have an `id` or it renders silent.
6. **Branding** — persistent Nexus wordmark + small disclosure line clip; separate track indices to avoid overlap.
7. **B-roll / texture suggestions** — optional `<video>` clips or subtle gradient/texture to lift it above a slide deck.
8. **Render output path** — `reports/tool_lab/hyperframes_renders/<short>_<slug>_v1.mp4`.

## How to build & render (free/local)
```
python scripts/export_creative_plan_to_hyperframes.py --scenes <scenes.json> --timing <timing.json> \
    --audio <voiceover.wav> --outdir tool-lab/hyperframes-shorts
npx --yes hyperframes@latest lint                      # expect 0 errors
python scripts/render_creative_short_hyperframes.py --project tool-lab/hyperframes-shorts \
    --out reports/tool_lab/hyperframes_renders/<short>_<slug>_v1.mp4   # absolute -o (cwd=project)
```

## Quality checklist (before scoring)
- [ ] Lint: 0 errors (audio has id; scene hard-kills; no overlapping same-track clips)
- [ ] Captions readable on a phone; one idea per scene
- [ ] Voiceover audible and synced
- [ ] Brand + disclosure present; no misleading imagery
- [ ] Above slide-deck quality (motion + pattern interrupts)

## Board + approval
After render: `content_board_update.py --id <id> --status "Video Rendered" --add-preview <mp4>`; set
`prompt_used=hyperframes_video.md`, `quality_score`, `generated_artifacts`. Score → route. **No upload/post.**
