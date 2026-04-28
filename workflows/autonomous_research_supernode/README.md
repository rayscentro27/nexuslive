# Nexus Autonomous Research Supernode — Phase 8

> **RESEARCH ONLY. NO LIVE TRADING. NO BROKER EXECUTION. NO ORDER PLACEMENT.**

The Autonomous Research Supernode is a unified, multi-lane intelligence pipeline that
ingests YouTube transcripts, manual research files, and Perplexity Comet browser
research — classifies them, extracts structured claims and insights, persists everything
to the Nexus Brain (Supabase), generates research briefs with next actions, and
delivers intelligence to Telegram.

---

## Supported Research Domains

| Topic ID | Description |
|---|---|
| `trading` | Forex, options, equities — strategies, risk management, setups |
| `credit_repair` | Credit scores, dispute letters, tradelines, FCRA/CFPB |
| `grant_research` | Federal/state/local grants, SBIR/STTR, SBA programs |
| `business_opportunities` | SaaS, agency models, passive income, AI automation |
| `crm_automation` | CRM workflows, GoHighLevel, Zapier, Make.com, n8n |
| `general_business_intelligence` | Catch-all for mixed or unclassified content |

---

## Three Research Lanes

### 1. Transcript Lane (YouTube / local files)
- yt-dlp downloads auto-captions from YouTube channels or videos
- Local `.txt`, `.md`, `.vtt` files supported
- Falls back gracefully if transcript unavailable

### 2. Manual Lane (JSON / text files)
- JSON research files with structured entries
- Drop `.txt` / `.md` files into `manual_sources/` folder
- Name files with topic prefix: `credit_repair_my_notes.txt`

### 3. Browser Lane (Perplexity Comet)
- Sends website sources to Comet for structured extraction
- Domain-specific extraction goals per topic
- Default: `COMET_ADAPTER_MODE=placeholder` (synthetic data for dev/testing)
- Set `COMET_ADAPTER_MODE=real` and implement `realCometCall()` in `comet_researcher.js`
  when Comet exposes a programmatic API

---

## Architecture

```
source_registry.js          ── loads + routes sources to lanes
        │
        ├─► transcript_extractor.js   ── yt-dlp / local files (TRANSCRIPT lane)
        ├─► manual_source_loader.js   ── JSON / txt files (MANUAL lane)
        └─► comet_researcher.js       ── Comet browser adapter (BROWSER lane)
                │
                ▼ (all lanes converge here)
        topic_classifier.js
                │
                ▼
        claim_extractor.js            ── OpenClaw AI OR keyword fallback
                │
                ├─► artifact_writer.js     → Supabase: research_artifacts + research_claims
                ├─► memory_enricher.js     → Supabase: research (vector memory)
                ├─► graph_enricher.js      → Supabase: research_relationships
                └─► cluster_writer.js      → Supabase: research_clusters
                        │
                        ▼
                brief_generator.js        ── ResearchBrief object
                        │
                        ├─► next_action_generator.js   ── prioritized action list
                        ├─► telegram_research_alert.js ── per-source Telegram alert
                        └─► telegram_brief_alert.js    ── topic digest alert
```

---

## Quick Start

### Install dependencies

```bash
cd ~/nexus-ai/workflows/autonomous_research_supernode
npm install

# Symlink project root .env (recommended)
ln -sf ../../.env .env
```

### Install yt-dlp (for YouTube transcripts)

```bash
pip install yt-dlp
# or
brew install yt-dlp
```

---

## Run Commands

### All lanes, all topics
```bash
node research_orchestrator.js --once
```

### Filter by topic
```bash
node research_orchestrator.js --once --topic grant_research
node research_orchestrator.js --once --topic credit_repair
node research_orchestrator.js --once --topic business_opportunities
node research_orchestrator.js --once --topic crm_automation
node research_orchestrator.js --once --topic trading
```

### Run specific lanes only
```bash
node research_orchestrator.js --once --browser
node research_orchestrator.js --once --transcript
node research_orchestrator.js --once --manual
```

### Combine lane + topic
```bash
node research_orchestrator.js --once --browser --topic grant_research
node research_orchestrator.js --once --manual --topic credit_repair
```

### Limit sources (for testing)
```bash
node research_orchestrator.js --once --limit 2
```

### Custom source files
```bash
node research_orchestrator.js --once --sources my_sources.json
node research_orchestrator.js --once --manual --manual-file my_research.json
```

### Debug mode
```bash
DEBUG=1 node research_orchestrator.js --once --limit 1
```

---

## Source Configuration

### `sample_sources.json` — add your sources

```json
{
  "sources": [
    {
      "type": "youtube_channel",
      "lane": "transcript",
      "topic": "credit_repair",
      "name": "CreditWarrior",
      "url": "https://www.youtube.com/@CreditWarrior",
      "max_videos": 3
    },
    {
      "type": "website",
      "lane": "browser",
      "topic": "grant_research",
      "name": "Grants.gov",
      "url": "https://www.grants.gov"
    }
  ]
}
```

**type** options: `youtube_channel`, `youtube_video`, `local_file`, `website`
**lane** options: `transcript`, `manual`, `browser`

---

## Manual Research Drop-In

### JSON format (`sample_manual_research.json`)

```json
{
  "entries": [
    {
      "topic": "credit_repair",
      "title": "My FCRA Dispute Notes",
      "source_name": "Personal Research",
      "content_text": "Key insights from my FCRA study..."
    }
  ]
}
```

### Text files in `manual_sources/` folder

```
credit_repair_dispute_strategy.txt
grant_research_sbir_notes.md
business_opportunities_saas_ideas.txt
```

Then run:
```bash
node research_orchestrator.js --once --manual
```

---

## Comet Browser Research Integration

The browser lane uses `comet_researcher.js` with an adapter pattern:

**Placeholder mode (default):**
- Returns realistic synthetic data so the full pipeline runs end-to-end
- Use for development, testing, and when Comet API isn't available
- Set via: `COMET_ADAPTER_MODE=placeholder` (or unset)

**Real mode:**
- Set `COMET_ADAPTER_MODE=real` in `.env`
- Implement `realCometCall()` in `comet_researcher.js`
- Integration patterns documented in the file comments:
  - REST API: POST to Comet's endpoint
  - MCP: configure in OpenClaw/Claude SDK mcp_servers
  - CLI: spawn child_process, parse JSON output

Domain-specific researchers:
- `comet_grant_researcher.js` — grant programs, eligibility, deadlines
- `comet_business_researcher.js` — business models, revenue, acquisition channels
- `comet_credit_policy_researcher.js` — FCRA/CFPB policy, dispute procedures
- `comet_competitor_researcher.js` — CRM stacks, automation workflows

---

## Output Tables (Supabase)

| Table | Purpose |
|---|---|
| `research_artifacts` | Full artifact per source |
| `research_claims` | Individual extracted claims |
| `research` | Vector memory chunks |
| `research_relationships` | Knowledge graph edges |
| `research_clusters` | Topic + subtheme clusters |
| `research_briefs` | Formatted intelligence briefs (optional) |

**SQL setup** — run these in Supabase Dashboard if needed:
```
~/nexus-ai/docs/research_artifacts_extensions.sql
~/nexus-ai/docs/research_claims_extensions.sql
```

---

## Environment Variables

Copy `.env.example` to `.env` or symlink the project root `.env`:

```bash
ln -sf ../../.env .env
```

Required:
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` — for DB writes
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — for Telegram alerts

Optional:
- `OPENCLAW_AUTH_TOKEN` — for AI claim extraction (falls back to keyword mode if missing)
- `HF_TOKEN` — for vector embeddings (falls back to text-only if missing)
- `COMET_ADAPTER_MODE` — `placeholder` (default) or `real`

---

## Validation SQL

```sql
-- Check artifacts by lane
SELECT source_type, topic, COUNT(*)
  FROM research_artifacts
  GROUP BY source_type, topic ORDER BY COUNT(*) DESC;

-- Check claims by topic
SELECT topic, claim_type, COUNT(*), ROUND(AVG(confidence),3) AS avg_conf
  FROM research_claims
  GROUP BY topic, claim_type ORDER BY COUNT(*) DESC;

-- Check vector memory
SELECT source, title, created_at, (embedding IS NOT NULL) AS has_embedding
  FROM research ORDER BY created_at DESC LIMIT 20;

-- Check knowledge graph
SELECT from_node, relation, to_node, COUNT(*)
  FROM research_relationships
  GROUP BY from_node, relation, to_node ORDER BY COUNT(*) DESC LIMIT 20;

-- Check clusters
SELECT theme, cluster_name, source_count, confidence
  FROM research_clusters ORDER BY created_at DESC LIMIT 20;
```

---

## Relationship to Phase 7 (Research Ingestion Lab)

Phase 8 thin-wraps Phase 7 modules:
- `topic_classifier.js` — direct re-export
- `graph_enricher.js` — direct re-export
- `cluster_writer.js` — direct re-export
- `claim_extractor.js`, `artifact_writer.js`, `memory_enricher.js` — adapters that bridge
  the `content_text` → `transcript_text` field name difference

Phase 7 continues to work independently at `../research_ingestion/`.

---

## Safety Notice

This system is **RESEARCH AND INGESTION ONLY**.

- No live trading
- No broker API connections
- No order placement
- No destructive scraping
- No credential harvesting

All data flows are: acquire → classify → extract → store → notify.
