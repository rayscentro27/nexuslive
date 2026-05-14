# Telegram Auto Summary Removal

## Removed/hard-disabled automatic summary paths

- Hard default-deny policy applied to research summary event types.
- Added blocking policy checks in:
  - `workflows/autonomous_research_supernode/telegram_research_alert.js`
  - `workflows/autonomous_research_supernode/telegram_brief_alert.js`
  - `workflows/research_ingestion/telegram_research_ingestion_alert.js`
  - `workflows/research_desk/telegram_research_alert.js`

## Fanout reduction

- Per-source research alert path now effectively disabled by default policy and explicit per-source flag requirement.
- Ingestion and research-desk summary sends are now default-denied and require explicit enablement + policy allow.

## Legacy auto worker summary suppression (Python)

- Added policy checks before direct Telegram sends in:
  - `revenue_engine/revenue_worker.py`
  - `readiness/readiness_worker.py`
  - `improvement_engine/improvement_worker.py`
  - `source_health/health_worker.py`
  - `optimization_engine/optimization_summary_job.py`
  - `optimization_engine/optimization_worker.py`

Result: automatic summary/report paths now deny by default instead of relying on cooldowns.
