# Telegram Spam — Root Cause Analysis
Date: 2026-05-15

## Root Cause: Node.js Research Supernode Bypassing hermes_gate.py

### What Was Happening

The `autonomous_research_supernode` Node.js workflow called the Telegram Bot API directly on every research run, completely bypassing the Python `hermes_gate.py` rate limiter, cooldown system, and content filter.

**Spam messages generated:**
- `"🏛️ *Nexus Research Run Complete*"` — from `telegram_research_alert.js::sendRunSummaryAlert()`
- `"🏛️ *Nexus Intelligence Brief*"` — from `telegram_brief_alert.js::sendTopicBriefAlert()`

### Trigger Frequency

Two launchd jobs invoked the orchestrator on a recurring schedule:

| Job | Interval | Topic |
|-----|----------|-------|
| `com.nexus.research-orchestrator-grants-browser` | Every 4 hours | grant_research |
| `com.nexus.research-orchestrator-transcript` | Every 2 hours | all transcripts |

Both jobs ran at boot (`RunAtLoad=true`) and on their intervals, producing 6–12+ Telegram messages per 24-hour period.

### Why hermes_gate.py Didn't Stop It

`hermes_gate.py` is a Python module. The research supernode is Node.js. The JS code loaded `.env` via `import "dotenv/config"` and called `fetch(https://api.telegram.org/bot.../sendMessage)` directly — there was no IPC bridge to the Python gate.

`hermes_gate.py` has `_FORBIDDEN_CONTENT_PATTERNS` including `"nexus research run complete"` and `"intelligence brief"` — but these patterns only apply to Python sends through the gate, not JS direct calls.

### Pre-existing Blocker That Wasn't Honored

`TELEGRAM_RESEARCH_ALERTS_ENABLED=false` was already present in both `.env` files, but neither `telegram_research_alert.js` nor `telegram_brief_alert.js` ever read this variable. The flag existed as dead config.

### Fanout Multiplier

Each orchestrator run generated multiple Telegram calls:
1. Per-source alert (`sendResearchAlert`) for each source processed
2. Per-topic brief (`sendTopicBriefAlert`) for each topic with results
3. Run-complete summary (`sendRunSummaryAlert`) at end of run

With 4 sources per run × 2 runs/cycle = up to 9 messages per orchestrator cycle.

### Other Sources Ruled Out

| Source | Status | Why Safe |
|--------|--------|----------|
| Python scheduler | NOT sending | `SCHEDULER_TELEGRAM_ENABLED=false` → `_notify()` returns early |
| Hermes gateway | NOT sending | No Telegram platform configured in `~/.hermes/config.yaml` |
| nexus-orchestrator service | NOT sending | `ENABLE_TELEGRAM_ALERTS=false`, confirmed `alerts_emitted: 0` in logs |
| monitoring_worker | NOT sending | Only fires on actual check failures; all checks passing |
| telegram_bot.py | NOT sending | Only heartbeats and command responses, no automated sends |
| critical_monitor scheduler task | NOT sending | `SCHEDULER_TELEGRAM_ENABLED=false` blocks `_notify()` |
