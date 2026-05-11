# Nexus Brain Research Ingestion Lab — Phase 7

> **RESEARCH ONLY. NO LIVE TRADING. NO BROKER EXECUTION. NO ORDER PLACEMENT.**

The Research Ingestion Lab is a multi-domain intelligence pipeline that ingests YouTube
transcripts and local documents, classifies them by topic, extracts structured claims and
insights using OpenClaw AI, and writes enriched research artifacts into the Nexus Brain
knowledge base in Supabase.

---

## Supported Research Domains

| Topic ID | Description |
|---|---|
| `trading` | Forex, options, equities — strategies, risk management, setups |
| `credit_repair` | Credit scores, dispute letters, tradelines, FCRA tactics |
| `grant_research` | Federal/state/local grants, SBA programs, nonprofit funding |
| `business_opportunities` | SaaS, agency models, passive income, automation businesses |
| `crm_automation` | CRM workflows, lead generation, GoHighLevel, Zapier, funnels |
| `general_business_intelligence` | Catch-all for mixed or unclassified content |

---

## Architecture

```
Source Seeds (sample_sources.json)
        │
        ▼
transcript_extractor.js     ── yt-dlp OR local drop_in/ files
        │
        ▼
topic_classifier.js         ── keyword scoring → topic + subthemes
        │
        ▼
claim_extractor.js          ── OpenClaw AI OR keyword fallback
        │
        ├─► artifact_writer.js     → Supabase: research_artifacts + research_claims
        ├─► memory_enricher.js     → Supabase: research (vector memory, existing table)
        ├─► graph_enricher.js      → Supabase: research_relationships
        └─► cluster_writer.js      → Supabase: research_clusters (Phase 6 compatible)
                │
                ▼
        telegram_research_ingestion_alert.js  → Telegram notification
```

---

## Transcript-First Workflow

1. **YouTube sources**: yt-dlp downloads auto-captions (VTT format) from channels/videos
2. **Local drop-ins**: Place `.txt`, `.md`, or `.vtt` files in `drop_in/`
3. **If transcript unavailable**: logged and skipped — batch continues safely
4. **All ingestion is read-only** — no scraping credentials, no account access

### yt-dlp Installation

```bash
pip install yt-dlp
# or
brew install yt-dlp
```

---

## Source Seed Format

`sample_sources.json`:
```json
{
  "sources": [
    {
      "type": "youtube_channel",
      "topic": "credit_repair",
      "name": "CreditWarrior",
      "url": "https://www.youtube.com/@CreditWarrior",
      "max_videos": 3
    },
    {
      "type": "youtube_channel",
      "topic": "grant_research",
      "name": "GrantsForWomen",
      "url": "https://www.youtube.com/@grantsforwomen",
      "max_videos": 2
    }
  ]
}
```

**type** options: `youtube_channel`, `youtube_video`, `local_file`
**topic** must be one of the supported domain IDs above.

---

## Manual Transcript Drop-In

Drop `.txt`, `.md`, or `.vtt` files into `workflows/research_ingestion/drop_in/`.

**Naming convention** — prefix with topic:
```
credit_repair_my_notes.txt
grant_research_sbir_guide.md
business_opportunities_saas_strategy.txt
trading_london_breakout_notes.txt
```

Then run:
```bash
node research_ingestion_runner.js --drop-ins
node research_ingestion_runner.js --drop-ins --topic credit_repair
```

---

## Run Commands

### Full ingestion from source seed file
```bash
node research_ingestion_runner.js --once --sources sample_sources.json
```

### Filter by topic
```bash
node research_ingestion_runner.js --topic credit_repair --sources sample_sources.json
node research_ingestion_runner.js --topic grant_research --sources sample_sources.json
node research_ingestion_runner.js --topic business_opportunities --sources sample_sources.json
node research_ingestion_runner.js --topic crm_automation --sources sample_sources.json
node research_ingestion_runner.js --topic trading --sources sample_sources.json
```

### Manual transcript file
```bash
node research_ingestion_runner.js --transcript /path/to/transcript.txt --topic credit_repair
```

### Drop-in folder
```bash
node research_ingestion_runner.js --drop-ins
node research_ingestion_runner.js --drop-ins --topic grant_research
```

---

## Output Tables

| Table | Purpose | Notes |
|---|---|---|
| `research_artifacts` | Full artifact per transcript | Run `docs/research_artifacts_extensions.sql` |
| `research_claims` | Individual extracted claims | Run `docs/research_claims_extensions.sql` |
| `research` | Vector memory chunks | Existing table — Phase 1 compatible |
| `research_clusters` | Topic+subtheme clusters | Phase 6 compatible format |
| `research_relationships` | Knowledge graph edges | Run `docs/research_claims_extensions.sql` |

---

## Memory Enrichment Behavior

`memory_enricher.js` writes chunks to the existing `research` table:
- 1 summary chunk per transcript
- Up to 3 key point chunks
- Up to 4 high-confidence claim chunks (≥0.6 confidence)

**With `HF_TOKEN` set**: Each chunk gets a 384-dim embedding via
`sentence-transformers/all-MiniLM-L6-v2` (HuggingFace Inference API).
Embeddings enable semantic search across all Nexus Brain research.

**Without `HF_TOKEN`**: Chunks write text-only (embedding column stays NULL).
Text search still works. Set `HF_TOKEN` in `.env` to enable vector search.

---

## Graph Enrichment Behavior

`graph_enricher.js` writes to `research_relationships`:
- `topic → subtheme` (contains)
- `topic → source` (sourced_from)
- `claim_type → topic` (extracted_from)
- `subtheme → source` (sourced_from)

Examples:
```
credit_repair → dispute_letters        (contains)
grant_research → small_business_grants (contains)
business_opportunities → saas_opportunities (contains)
opportunity → business_opportunities   (extracted_from)
trading → TraderNick                   (sourced_from)
```

---

## SQL Setup (Supabase Dashboard)

Run these SQL docs in order in the Supabase Dashboard SQL editor:

```
docs/research_artifacts_extensions.sql   ← new + ALTER TABLE (safe to re-run)
docs/research_claims_extensions.sql      ← new + ALTER TABLE + research_relationships
```

Full table definitions (if creating from scratch):
```
docs/research_artifacts.sql
docs/research_claims.sql
docs/research_relationships.sql
```

---

## Validation SQL

```sql
-- Check research_artifacts
SELECT topic, COUNT(*) FROM research_artifacts
  GROUP BY topic ORDER BY COUNT(*) DESC;

-- Check research_claims
SELECT topic, claim_type, COUNT(*), ROUND(AVG(confidence),3) AS avg_conf
  FROM research_claims
  GROUP BY topic, claim_type ORDER BY COUNT(*) DESC;

-- Check vector memory
SELECT source, title, created_at,
       (embedding IS NOT NULL) AS has_embedding
  FROM research
  ORDER BY created_at DESC LIMIT 20;

-- Check research_clusters (Phase 6 + 7 shared)
SELECT theme, cluster_name, source_count, confidence
  FROM research_clusters
  ORDER BY created_at DESC LIMIT 20;

-- Check graph relationships
SELECT from_node, relation, to_node, COUNT(*)
  FROM research_relationships
  GROUP BY from_node, relation, to_node
  ORDER BY COUNT(*) DESC LIMIT 20;
```

---

## Environment Variables

Copy `.env.example` to `.env` or symlink the project root `.env`:
```bash
ln -sf ../../.env .env
```

Required:
- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` — for writes
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — for alerts
- `OPENCLAW_AUTH_TOKEN` — for AI claim extraction (falls back to keyword mode if missing)

Optional:
- `HF_TOKEN` — for vector embeddings (falls back to text-only if missing)
- `MAX_RESEARCH_SOURCES` — default 10, limits sources per run

---

## Safety Notice

This system is **RESEARCH AND INGESTION ONLY**.

- No live trading
- No broker API connections
- No order placement
- No destructive scraping
- No credential harvesting
- No bypass of platform protections

All data flows are: ingest → classify → extract → store → notify.
