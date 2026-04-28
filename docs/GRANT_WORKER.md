# GrantWorker

Specialized Nexus AI employee that scans research_artifacts for grant opportunities, normalizes them into structured records, scores by priority, and surfaces actionable findings via Supabase + Telegram.

## Purpose

Transforms raw grant research (ingested by ResearchWorker) into a ranked, filterable list of grant opportunities relevant to small business owners. No AI inference calls — pure heuristic processing on existing artifacts.

## Location

```
~/nexus-ai/workflows/ai_workforce/grant_worker/
├── grant_worker.js          ← Entry point (direct-run + queue mode)
├── grant_normalizer.js      ← Extracts structured fields from artifacts
├── grant_scoring.js         ← Scores 0-100 using heuristics
└── grant_brief_generator.js ← Formats brief + sends Telegram alert
```

## Inputs

| Source | Description |
|--------|-------------|
| `research_artifacts` (Supabase) | Rows with `topic = 'grant_research'` |
| `--since <days>` CLI flag | Restricts to artifacts created in the last N days |

## Outputs

| Destination | Description |
|-------------|-------------|
| `grant_opportunities` (Supabase) | Normalized + scored grant records |
| Console | Ranked brief with all grant details |
| Telegram | Alert with top 3 grants (MarkdownV2) |

## Normalized Fields

| Field | Source | Example |
|-------|--------|---------|
| `source` | artifact.source | "SBIR.gov" |
| `title` | artifact.title | "SBIR Phase I Award" |
| `program_name` | Extracted from title/summary | "SBIR" |
| `funding_amount` | Regex on content | "$50,000" |
| `geography` | Keyword matching | "National / Federal" |
| `target_business_type` | Keyword matching | "Small Business, Technology" |
| `eligibility_notes` | First eligibility-related key_point | "Must be US-based for-profit..." |
| `deadline` | Regex / keyword | "Rolling / ongoing" |
| `confidence` | From topic classifier | 0.85 |
| `score` | Computed by grant_scoring.js | 72 |

## Scoring Logic (0–100)

| Component | Max Points | Basis |
|-----------|-----------|-------|
| Funding amount | 30 | ≥$500K=30, ≥$100K=25, ≥$50K=20... |
| Deadline urgency | 20 | ≤14d=20, ≤30d=18, rolling=12... |
| Geography | 15 | National/Federal=15, Arizona=14... |
| Eligibility clarity | 15 | Length + detail of notes |
| Source authority | 10 | .gov / known programs = highest |
| Confidence bonus | 10 | Classifier confidence × 10 |

Minimum score to surface: **30** (configurable with `--min-score`).

## Queue Compatibility

```js
// Queue job type: "grant_scan"
import { runGrantWorker } from "./grant_worker/grant_worker.js";

const result = await runGrantWorker({
  since_days: 7,   // look back window
  min_score: 40,   // raise threshold for queue runs
  dry_run: false,
  quiet: true,     // suppress console in queue context
});
// result = { grants: [...], brief: {...} }
```

## Direct-Run Commands

```bash
cd ~/nexus-ai/workflows/ai_workforce

# Safe dry run — no writes, no Telegram, see what would surface
node grant_worker/grant_worker.js --dry-run

# Standard run: last 30 days, score ≥ 30
node grant_worker/grant_worker.js

# Look back 7 days, higher threshold
node grant_worker/grant_worker.js --since 7 --min-score 50

# All-time scan
node grant_worker/grant_worker.js --since all --min-score 40

# Quiet mode (less console output)
node grant_worker/grant_worker.js --quiet
```

## Supabase Table Setup

Run `docs/grant_opportunities.sql` in Supabase SQL editor before first production write:

```sql
-- Creates: grant_opportunities table + indexes + auto-updated_at trigger
-- See: ~/nexus-ai/docs/grant_opportunities.sql
```

## Production Safety Notes

- **No AI calls** — processing is pure regex/keyword heuristics on existing artifacts
- **Additive only** — never modifies research_artifacts or research_claims
- **Silent failure** — if grant_opportunities table missing, logs warning and continues
- **Idempotent** — re-running scores the same artifacts; scores may change if new key_points are added
- **No client PII** — operates only on general research content, not client records
- **No trading** — purely informational grant discovery

## Blockers / Prerequisites

1. Run `docs/grant_opportunities.sql` in Supabase to create output table
2. Requires at least one `research_artifacts` row with `topic = 'grant_research'`
3. `SUPABASE_URL` and `SUPABASE_KEY` must be set in `.env`
4. `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` for alerts (optional — fails silently if missing)
