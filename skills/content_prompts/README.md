# Nexus Content Prompt Library v1
_Category-specific, repeatable prompts for the Nexus content engine. Internal use; nothing here publishes._

Successful AI creators don't use one generic prompt — they use strong, repeatable prompts **per content
type**. This library gives Hermes/Nexus that system, wired into the existing Content Workspace Board.

## What each prompt is for
| Prompt file | Use it to produce |
|---|---|
| `youtube_shorts.md` | 30–45s YouTube Short (script, captions, visuals, metadata) |
| `tiktok_reels.md` | TikTok / Instagram Reels short (first-second hook, fast captions) |
| `long_form_youtube.md` | 6–12 min YouTube video plan/script + derivatives |
| `notebooklm_podcast_audio_overview.md` | NotebookLM-style audio overview / two-host podcast from sources |
| `podcast_to_video.md` | Video clips from a podcast/audio-overview script |
| `hyperframes_video.md` | Agent-native HTML/CSS/JS composition for the HyperFrames renderer |
| `broll_short_video.md` | B-roll-based Short (Pexels/free footage + Piper voice + captions) |
| `linkedin_post.md` | LinkedIn authority post (3 variants) |
| `newsletter.md` | Newsletter draft (subject lines, body, CTA) |
| `blog_seo_article.md` | SEO blog outline/draft (keywords, H2/H3, FAQ) |
| `content_repurposing.md` | One source → a full content family |
| `performance_improvement.md` | Diagnose 24h/72h performance → revised content |
| `_universal_content_rules.md` | Rules every prompt inherits (safety, compliance, board, approvals) |

## When Hermes should use each prompt
Routing is defined in `reports/content_engine/content_prompt_routing.md`. In short: pick the prompt
that matches the requested **content type / platform**; for multi-asset requests use `content_repurposing.md`;
for a 24h/72h review use `performance_improvement.md`. Every prompt run inherits `_universal_content_rules.md`.

## Required inputs
Each prompt lists its own inputs, drawn from the shared variable set in
`reports/content_engine/prompt_library/prompt_variables_schema.md` (board_id, content_id, topic,
source_paths, target_platform, audience, niche, offer, disclosure flags, length/style, output_paths, etc.).
Minimum: a **topic or source** + a **target platform/format**.

## Expected outputs
Structured artifacts only (markdown packets, scene JSON, scripts, metadata blocks) — never a raw blob.
Every run produces: (1) the content artifact(s), (2) a **quality score** (rubric below), and (3) a
**board card create/update** with `prompt_used` + `generated_artifacts`.

## Where artifacts are saved
- Scripts/plans → `reports/creative_short_plans/`, packets → `reports/creative_short_packets/`
- Publish packages → `reports/publish_packages/`
- Renders → `reports/tool_lab/hyperframes_renders/` (HyperFrames) / `reports/tool_lab/creative_renders/` (others)
- Prompt-run examples/log → `reports/content_engine/prompt_library/examples/`
- Each prompt file states its exact output path(s).

## How prompt outputs update the Content Workspace Board
After generating artifacts, the prompt instructs Hermes to call the **existing** board scripts (do not
rebuild the board):
```
python scripts/content_board_add.py --content-id <id> --title "..." --status <status> \
    --content-type "..." --platform "..." --preview <path>     # create-or-MERGE (won't clobber)
python scripts/content_board_update.py --id <id> --status "Video Rendered" --add-preview <mp4> \
    --next-action "..."                                         # advance + record
```
Future cards should also set `prompt_used`, `quality_score`, `generated_artifacts`, `content_family`,
`parent_source_id` (fields added to `lib/content_board.py` v1.1).

## How board status is chosen (quality gate)
Score each artifact with `reports/content_engine/prompt_library/content_quality_rubric.md`:
- **< 7/10 → `Improve / Retry`** (do NOT send to Ray)
- **7–8/10 → `Needs Ray Review`**
- **9+/10 → Recommended publish candidate → still `Needs Ray Review`** (Ray approval always required)

## How approval cards are generated
For any publish-ready asset (status `Needs Ray Review`), generate a draft approval card with the
**existing** generator (request only, never executes):
```
python scripts/create_content_approval_card.py --id <id> --scope review|unlisted
```

## How Telegram digests reference prompt outputs
`scripts/content_board_digest.py` reads the board; future cards carry `prompt_used` so the digest can
show which prompt/category produced each item. The digest is written to
`reports/content_engine/telegram_digests/` and is **not auto-sent** (gated `--send` only).

## Ray approval rules (inherited by every prompt)
Nexus may **research, draft, render, score, route, and recommend autonomously**. Ray approval is
**required** before: publishing, scheduling, public posting, sending emails/newsletters, paid APIs/tools,
credential changes, production deploys, DB migrations, live trading, or moving money. The publish path
(`scripts/social_publish_executor.py`) stays disabled by default. See `_universal_content_rules.md`.
