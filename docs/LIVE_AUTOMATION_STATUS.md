# Nexus Live Automation Status

This is the current live automation layer for Nexus on the Mac.

## Core Services

### `com.nexus.orchestrator`
- Purpose: event intake and job routing
- Status: persistent daemon
- Writes to:
  - `system_events`
  - `job_queue`
  - `orchestrator_workflow_runs`
  - `worker_heartbeats`
- Healthy means:
  - heartbeat row exists for `nexus-orchestrator-1`
  - no repeating schema-cache errors in `logs/nexus-orchestrator.error.log`

### `com.nexus.research-worker`
- Purpose: queue worker for `research_collect`, `daily_system_digest`, `stale_state_sweep`
- Status: persistent daemon
- Writes to:
  - `job_queue`
  - `system_digests`
  - `worker_heartbeats`
- Healthy means:
  - heartbeat row exists for `nexus-research-worker`
  - no repeated fatal errors in `logs/nexus-research-worker.error.log`

### `com.nexus.signal-review`
- Purpose: persistent signal review poller for `tv_normalized_signals`
- Status: launchd daemon with `KeepAlive`
- Reads from:
  - `tv_normalized_signals`
  - `research`
  - `signal_candidates`
- Writes to:
  - `tv_normalized_signals`
  - `signal_candidates`
  - `signal_scores`
  - `approved_signals`
- Logs:
  - `logs/signal_review.log`
  - `openclaw/logs/signal-review.log`
- Healthy means:
  - launchd shows `com.nexus.signal-review` loaded
  - `signal_poller.py` is running
  - new signals stop accumulating in `status='new'` without decisions

## Scheduled Research + Analysis Jobs

### `com.nexus.research-orchestrator-transcript`
- Purpose: real YouTube transcript ingestion
- Schedule: every 2 hours (`7200s`)
- Command:
  - `node research_orchestrator.js --once --transcript --sources sample_sources.json`
- Source file:
  - `workflows/autonomous_research_supernode/sample_sources.json`
- Writes to:
  - `research_artifacts`
  - `research_claims`
  - `research`
  - `research_relationships`
  - `research_clusters`
  - `research_briefs`
- Logs:
  - `logs/research-orchestrator-transcript.log`
  - `logs/research-orchestrator-transcript.error.log`
- Quiet is normal when:
  - no new transcripts are available
  - some videos have no captions
- Broken means:
  - repeated Supabase write failures
  - repeated `yt-dlp` failures
  - no fresh `research_artifacts` rows after a run window

### `com.nexus.research-orchestrator-grants-browser`
- Purpose: official-site grant research ingestion
- Schedule: every 4 hours (`14400s`)
- Command:
  - `node research_orchestrator.js --once --browser --topic grant_research --sources sample_sources.json --limit 4`
- Source file:
  - `workflows/autonomous_research_supernode/sample_sources.json`
- Writes to:
  - `research_artifacts`
  - `research_claims`
  - `research`
  - `research_relationships`
  - `research_clusters`
  - `research_briefs`
- Logs:
  - `logs/research-orchestrator-grants-browser.log`
  - `logs/research-orchestrator-grants-browser.error.log`
- Quiet is normal when:
  - no new useful grant extraction is produced from the selected browser sources
- Broken means:
  - repeated browser-lane write failures
  - no fresh `grant_research` artifacts after a run window

### `com.nexus.opportunity-worker`
- Purpose: turn research artifacts into ranked business opportunities
- Schedule: every 2 hours (`7200s`)
- Command:
  - `node opportunity_worker/opportunity_worker.js --since 30 --min-score 35`
- Reads from:
  - `research_artifacts` where topic is `business_opportunities` or `crm_automation`
- Writes to:
  - `business_opportunities`
- Logs:
  - `logs/opportunity-worker.log`
  - `logs/opportunity-worker.error.log`
- Quiet is normal when:
  - no artifacts score above threshold
- Broken means:
  - schema write errors
  - repeated fatal Supabase GET/POST failures
  - no rows in `business_opportunities` despite qualifying artifacts

### `com.nexus.grant-worker`
- Purpose: turn grant artifacts into ranked grant opportunities
- Schedule: every 4 hours (`14400s`)
- Command:
  - `node grant_worker/grant_worker.js --since 30 --min-score 40`
- Reads from:
  - `research_artifacts` where topic is `grant_research`
- Writes to:
  - `grant_opportunities`
- Logs:
  - `logs/grant-worker.log`
  - `logs/grant-worker.error.log`
- Quiet is normal when:
  - no `grant_research` artifacts exist yet
  - no grants score above threshold
- Broken means:
  - schema write errors
  - fatal Supabase GET/POST failures
  - grant artifacts exist but nothing is ever surfaced

## Current Practical State

- Transcript ingestion: live and working
- Grant browser ingestion: live and working
- Research enrichment: live and working
- Opportunity ranking: live and writing rows
- Grant ranking: live and writing rows

## Confirmed Live Outputs

- `research_artifacts`
  - confirmed fresh transcript artifacts from channels like `Credit Plug` and `Monica Main`
  - confirmed fresh `grant_research` artifacts from `Grants.gov`
- `business_opportunities`
  - confirmed rows written by `opportunity_worker`
- `grant_opportunities`
  - confirmed rows written by `grant_worker`

## Quick Checks

### Check launchd registration
```bash
launchctl list | rg 'com\\.nexus\\.(orchestrator|research-worker|signal-review|research-orchestrator-transcript|research-orchestrator-grants-browser|opportunity-worker|grant-worker)'
```

### Check recent transcript ingestion
```bash
tail -n 80 ~/nexus-ai/logs/research-orchestrator-transcript.log
```

### Check recent grant browser ingestion
```bash
tail -n 80 ~/nexus-ai/logs/research-orchestrator-grants-browser.log
```

### Check recent opportunity scan
```bash
tail -n 80 ~/nexus-ai/logs/opportunity-worker.log
```

### Check recent grant scan
```bash
tail -n 80 ~/nexus-ai/logs/grant-worker.log
```

### Check fresh Supabase outputs
```bash
select id, title, topic, created_at
from research_artifacts
order by created_at desc
limit 10;
```

```bash
select id, title, niche, score, created_at
from business_opportunities
order by created_at desc
limit 10;
```

```bash
select id, title, score, created_at
from grant_opportunities
order by created_at desc
limit 10;
```

## What “No Output” Usually Means

- `research-orchestrator-transcript`
  - often means no captions available or no newly useful transcript rows
- `opportunity-worker`
  - often means artifacts were ingested, but none cleared the score threshold
- `grant-worker`
  - often means recent `grant_research` artifacts did not clear the score threshold
