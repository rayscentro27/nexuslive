# Telegram Spam Root Cause

## Exact origin identified

- Primary process: `workflows/autonomous_research_supernode/research_orchestrator.js`
- Trigger source: scheduled/repeated research runs and ingestion runs
- Repeated event source: direct Telegram sends in research modules bypassing Hermes gate

## Duplicate fanout path

- For each source processed, orchestrator called per-source alert (`sendResearchAlert`) in `workflows/autonomous_research_supernode/telegram_research_alert.js`.
- Same run also emitted topic brief alerts (`sendTopicBriefAlert`) in `workflows/autonomous_research_supernode/telegram_brief_alert.js`.
- Same run also emitted run summary alert (`sendRunSummaryAlert`) in `workflows/autonomous_research_supernode/telegram_research_alert.js`.
- Separate ingestion path also sent direct summary alert in `workflows/research_ingestion/telegram_research_ingestion_alert.js`.
- Research desk path sent direct summary alerts in `workflows/research_desk/telegram_research_alert.js`.

This created stacked fanout (per-source + per-topic + run summary + ingestion + desk), which became spam under repeated runs or overlapping trigger cadence.

## Recursion/loop amplifier

- Research escalation path could recreate very similar tickets when matching relied only on broad `ilike` + open-ticket checks.
- Under repeated low-confidence queries, this increased repeated "researching/needs_review" flows and notification pressure.
