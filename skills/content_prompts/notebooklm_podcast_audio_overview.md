# Prompt — NotebookLM-style Podcast / Audio Overview
_Inherits `_universal_content_rules.md`. Internal draft only; no upload/post/schedule._

**Purpose:** Replicate NotebookLM-style audio overview / two-host podcast creation from sources.

## Inputs
`content_id`, `topic`, `source_paths`/`source_urls`, `audience`, `niche`, `desired_length`, `board_id`.

## Source ingestion instructions
Load only the provided sources (transcripts, blog posts, newsletters, research_artifacts,
source_extractions, knowledge_items, manual NotebookLM exports). **Summarize and verify — never copy.**
Every claim must trace to a source_extraction. Flag anything you cannot verify; do not invent statistics.

## Required output structure
1. **Two-host dialogue structure** — HOST (warm, curious) + ANALYST (blunt, evidence-first). Natural turns,
   short lines, one host teaches while the other probes. Label every line.
2. **Educational summary** — the core takeaways in plain language; no guarantees, no hype.
3. **Tension / curiosity moments** — 2–3 spots that pose a question or overturn a myth to hold attention.
4. **60-second version** — tight single-narrator or quick two-host overview for a Short.
5. **5–10 minute podcast version** — full dialogue with intro, 3–5 segments, recap, soft CTA.
6. **Clip-worthy moments** — 3 timestamped lines that stand alone (route to `podcast_to_video.md`).
7. **Show notes** — bullet summary + sources + disclosure.
8. **Social snippets** — 3 captions derived from the strongest moments (route to repurposing).

## Voice / render
Two Piper voices (e.g. `en_US-amy-medium` + a second voice) — local/free. Audio → `reports/tool_lab/creative_renders/`.

## Output paths
- Script: `reports/creative_short_plans/<short>_podcast.md`
- Packet (clips/snippets/metadata): `reports/creative_short_packets/<short>_podcast_to_video_packet.md`

## Board + approval rules
`content_board_add.py … --content-type "Podcast/Audio Overview"`; status `Podcast Scripted` → score →
`Needs Ray Review`/`Improve / Retry`. Publishing/emailing/posting requires Ray approval; audio synthesis and
draft clips are autonomous. No auto-send.
