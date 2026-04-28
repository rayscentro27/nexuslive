# Skill: Research Pipeline — Knowledge Ingestion

## Purpose
Continuously ingest YouTube content, extract trading and business strategies,
and store them in Supabase so all agents can query institutional knowledge.

## How to Submit Content
Email a YouTube URL (one per line) to: **goclearonline@gmail.com**
Subject line doesn't matter. The email-pipeline worker polls every 2 minutes.

## Pipeline Flow
1. YouTube URL arrives via email → `email-pipeline` worker extracts it
2. `research-orchestrator-transcript` downloads transcript via yt-dlp
3. Saved to `~/nexus-ai/research-engine/transcripts/`
4. `summarize.py` generates summary → `~/nexus-ai/research-engine/summaries/`
5. `strategy_extractor.py` extracts actionable strategies → `~/nexus-ai/research-engine/strategies/`
6. Strategies written to Supabase `research_strategies` table

## Manual Pipeline Run
```bash
cd ~/nexus-ai/research-engine
python3 summarize.py
python3 strategy_extractor.py
```

## Pipeline Status Check
```bash
python3 -c "
from pathlib import Path
b = Path('/Users/raymonddavis/nexus-ai/research-engine')
print(f'Transcripts: {len(list((b/\"transcripts\").glob(\"*\")))}')
print(f'Summaries:   {len(list((b/\"summaries\").glob(\"*\")))}')
print(f'Strategies:  {len(list((b/\"strategies\").glob(\"*\")))}')
"
```

## Recent Strategies
```bash
ls -lt ~/nexus-ai/research-engine/strategies/ | head -10
```

## Content Priorities
High-value content to ingest:
- Forex trading strategies (EURUSD, GBPUSD, USDJPY focus)
- AI agent architecture and multi-agent systems
- Business automation and SOP documentation
- Grant writing and funding strategies
- Client acquisition and onboarding systems

## Oracle ARM Instance
A remote Ollama instance runs at `http://161.153.40.41:11434` (model: qwen2.5:14b).
This is used as a fallback LLM for heavy research summarization tasks.
SSH access: `ssh -i ~/.ssh/oracle_vm ubuntu@161.153.40.41`
