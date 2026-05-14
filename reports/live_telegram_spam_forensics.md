# Live Telegram Spam Forensics

## Exact spam source

- Process: `com.nexus.research-orchestrator-transcript` (launchd agent)
- File: `workflows/autonomous_research_supernode/research_orchestrator.js`
- Functions:
  - `sendResearchAlert` in `workflows/autonomous_research_supernode/telegram_research_alert.js`
  - `sendTopicBriefAlert` in `workflows/autonomous_research_supernode/telegram_brief_alert.js`
  - `sendRunSummaryAlert` in `workflows/autonomous_research_supernode/telegram_research_alert.js`
- Trigger: periodic launchd run (`run interval = 7200 seconds`)

## Secondary fanout contributors

- `workflows/research_ingestion/telegram_research_ingestion_alert.js` (`sendIngestionAlert`)
- `workflows/research_desk/telegram_research_alert.js` (`sendResearchAlert`)

## Evidence

- `logs/research-orchestrator-transcript.log` contains repeated patterns:
  - `[telegram-research-alert] Alert sent for:`
  - `[telegram-brief-alert] Topic brief sent for:`
  - `[telegram-research-alert] Run summary alert sent.`
- Repeated at high volume with the same operational cadence and recurring summaries.

## Launch mode

- Launchd-driven recurring worker (not manual-only), confirmed by launchctl service metadata and recurring log writes.
