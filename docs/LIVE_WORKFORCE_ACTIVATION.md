# Nexus Workforce Activation

Current truth for this repo:

- `services/nexus-orchestrator` is running
- `services/nexus-research-worker` is running
- the queue schema is fixed and healthy
- the queued `research_collect` handler is still mock-mode
- the real YouTube-to-Supabase path today is `workflows/autonomous_research_supernode/research_orchestrator.js`

## What To Run For YouTube Ingestion

If you want YouTube channels transcribed and written into Supabase now, use the direct research orchestrator:

```bash
cd ~/nexus-ai/workflows/autonomous_research_supernode
node research_orchestrator.js --once --transcript
```

Filter to one topic:

```bash
node research_orchestrator.js --once --transcript --topic credit_repair
node research_orchestrator.js --once --transcript --topic grant_research
node research_orchestrator.js --once --transcript --topic business_opportunities
node research_orchestrator.js --once --transcript --topic crm_automation
node research_orchestrator.js --once --transcript --topic trading
```

Test with a small batch first:

```bash
node research_orchestrator.js --once --transcript --limit 2
```

## Where Channels Go

Add your YouTube sources to:

- `workflows/autonomous_research_supernode/sample_sources.json`

Each source should look like:

```json
{
  "type": "youtube_channel",
  "lane": "transcript",
  "topic": "business_opportunities",
  "name": "My Channel",
  "url": "https://www.youtube.com/@example",
  "max_videos": 3
}
```

## What Gets Written

The direct research orchestrator writes to Supabase tables including:

- `research_artifacts`
- `research_claims`
- `research`
- `research_relationships`
- `research_clusters`
- `research_briefs`

## After Research Ingestion

Once `research_artifacts` exists, run the downstream workers:

Grant scoring:

```bash
cd ~/nexus-ai/workflows/ai_workforce
node grant_worker/grant_worker.js --since 30
```

Opportunity scoring:

```bash
cd ~/nexus-ai/workflows/ai_workforce
node opportunity_worker/opportunity_worker.js --since 14
```

## Why Everything Is Not Automatically Active Yet

Right now there are two different research paths:

1. Queue/orchestrator path
   - healthy infrastructure
   - `research_collect` currently returns mock results

2. Direct supernode path
   - real transcript/manual/browser ingestion
   - real Supabase artifact writes

So if your goal is "take my YouTube channels, transcribe them, and add them to Supabase", use the direct supernode path today.

## To Make It Fully Automatic

You need one of these:

1. Schedule `research_orchestrator.js`
   - easiest and lowest-risk
   - use launchd or cron to run `--once --transcript` on an interval

2. Replace the mock `research_collect` handler
   - wire `services/nexus-research-worker/src/handler.js` to call the real autonomous research pipeline
   - then the orchestrator queue becomes the real ingestion path

## Recommended Next Step

Recommended production path right now:

1. Keep `nexus-orchestrator` and `nexus-research-worker` running
2. Add all channels to `sample_sources.json`
3. Schedule `research_orchestrator.js --once --transcript`
4. Schedule `grant_worker` and `opportunity_worker` after ingestion

