# Nexus Monetization Research Engine — Reactivation (Phase 1)

Turns Nexus into an active monetization scout: keyword → YouTube discovery →
demand/recognition/revenue scoring → review tables → (after review) Nexus OS →
Hermes recommendation → draft-only content.

## What already existed (not rebuilt)

| Component | Role | Status |
|-----------|------|--------|
| `lib/youtube_intelligence_worker.py` | Extracts intel from **registered** YouTube sources (`config/nexus_sources.yaml`) → `source_extractions`, `worker_recommendations` | Active, registry-driven |
| `lib/monetization_operating_engine.py` | Ranks revenue paths from **existing** Nexus knowledge (LLM) | Active, synthesis-only |
| `lib/opportunity_research_worker.py` | Scores funding opportunities per **user profile** | Active (cron 6h) |
| `lib/github_trend_researcher.py` | GitHub trending repos to improve ops | Active (weekly) |
| `services/nexus-research-worker` (node) | `research_collect` job handler | **Stub** ("real fetcher can be wired here") |

**The gap:** nothing searched YouTube/Google **by keyword** to *discover new*
recognizable, in-demand topics. Intake was limited to a hand-registered URL list.

## Root cause (why it wasn't powering Nexus OS)

- `no_youtube_search_provider` / `no_keyword_seed_config` — discovery was registry-only.
- `no_google_search_provider` — no free/paid web-search provider configured.
- `Hermes_evidence_missing_tables` / `no_bridge_to_nexus_os` — research lands in
  `source_extractions` (105) / `worker_recommendations` (315) / `knowledge_items` (54),
  but OS Hermes evidence reads only `nexus_os_*` (5 sources). The bridge is thin.

## What was added

`scripts/run_monetization_research_cycle.py` — keyword discovery using **yt-dlp
`ytsearch`** (free, no API key, no paid credits). Scores demand / recognition /
revenue-fit / content-fit / compliance-risk / confidence, maps each topic to an
existing Revenue Hub campaign, and writes review rows only:
- `source_extractions` (scout_id=`monetization_search_scout`)
- `knowledge_items` (`domain='monetization'`, `status='proposed'`)

Dry-run by default; `--apply` writes; web discovery disabled (no free provider).
No publishing, posting, scheduling, email, ads, or Nexus OS bridge.

## Compared to external references

| Reference | Nexus has | Missing / not yet |
|-----------|-----------|-------------------|
| YouTube Topic Insights (API+Gemini) | keyword→YouTube via yt-dlp + LLM extraction | official Data API metrics (views/trend deltas) — optional, paid |
| Topic Mine (keyword/headline gen) | campaign keyword seeds + angle text | ad-copy/headline expansion |
| n8n Trend Explorer (scheduled) | runner exists (manual) | cron schedule (add after review) |
| Postiz (approved scheduler) | — | do **not** enable posting now |
| OpenShorts / Shorts generators | transcript pull (yt-dlp) | short-video render (see plan below) |

Smallest path to "on": schedule the runner (cron, dry-run→review), then add the
Hermes evidence hook below. No new platform install required.

## Missing Hermes bridge (next action)

OS Hermes (`useNexusRecommendations.ts`) reads only `nexus_os_*`. To let Hermes
answer "what monetization topics did we discover?", add **one of**:
- **(recommended) read-only evidence hook**: a `monetization_research` intent that
  reads `knowledge_items(domain='monetization', status='proposed')` +
  `source_extractions(scout_id='monetization_search_scout')`, summary-only; or
- **review→bridge**: promote approved proposed items into `nexus_os_sources` so the
  existing graph-enriched path surfaces them.

Recommend option 1 (mirrors the approved system-map hook), built as a separate
approved pass. Until then, Hermes should not claim to see the new rows.

---

## Cost-effective social video plan

Goal: produce social/short videos cheaply, **draft-only**, no auto-posting.

- **Option A — manual-assisted (cheapest):** Hermes writes the script + captions;
  Ray edits in CapCut/Canva/DaVinci. Zero automation risk. Good for week 1.
- **Option B — local template pipeline (RECOMMENDED):** script + captions + stock
  images/B-roll → **ffmpeg** render (ffmpeg already installed) → vertical 1080×1920
  draft file → human reviews and uploads. Optional local TTS voiceover. No API cost,
  no posting risk.
- **Option C — open-source shorts systems** (OpenShorts / AI Shorts Generator /
  short-video-maker): best for long-video→short and transcript→short. Evaluate
  before integrating; heavier setup.
- **Option D — text-to-video models** (Open-Sora / Wan / CogVideoX): GPU-heavy, not
  the first revenue path. Defer.

**Recommendation:** Start with **Option B** — a small local ffmpeg template that
turns an approved Content Studio script into a draft vertical video. Draft-only;
Ray uploads manually. No auto-posting until explicitly approved (Postiz later).

## Safety

Free provider only (yt-dlp). No paid API calls, no publishing/posting/email/ads,
no scheduling, no Nexus OS bridge, no live trading, no secrets printed. All writes
are review rows (`status='proposed'`) requiring human approval.
