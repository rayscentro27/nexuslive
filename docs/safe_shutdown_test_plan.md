# Safe Shutdown Test Plan

## Core Principle
Test one optional service at a time, validate immediately, rollback immediately on regression.

## Global Rules
- No mass shutdowns
- No launch agent removals
- No config rewrites during test window
- Keep a second remote access path available before each test

## Per-Service Test Sequence
1. Capture baseline:
   - running PID
   - current memory snapshot
   - current health check outcomes
2. Stop exactly one optional service (manual/supervised)
3. Run health validation checklist (`docs/service_health_validation.md`)
4. Observe for 15-30 minutes (or one scheduler cycle)
5. If any failure appears, execute rollback immediately
6. Record result and proceed to next candidate only if green

## Optional Service Candidate Playbooks

### 1) `ollama serve`
- Stop command: `launchctl stop com.nexus.ollama`
- Rollback command: `launchctl start com.nexus.ollama`
- Expected impact: local model features unavailable; core Telegram/admin should remain operational

### 2) `dashboard.py` (`127.0.0.1:3000`)
- Stop command: `launchctl stop com.raymonddavis.nexus.dashboard`
- Rollback command: `launchctl start com.raymonddavis.nexus.dashboard`
- Expected impact: legacy local dashboard unavailable; control center should remain available

### 3) `tradingview_router.py`
- Stop command: `launchctl stop com.nexus.signal-router`
- Rollback command: `launchctl start com.nexus.signal-router`
- Expected impact: trading signal ingestion paused

### 4) `auto_executor.py`
- Stop command: `launchctl stop com.nexus.auto-executor`
- Rollback command: `launchctl start com.nexus.auto-executor`
- Expected impact: execution helper path paused; aligns with safety posture

### 5) `tournament_service.py`
- Stop command: `launchctl stop com.nexus.tournament`
- Rollback command: `launchctl start com.nexus.tournament`
- Expected impact: tournament workflows paused

### 6) `research_signal_bridge.py`
- Stop command: `launchctl stop com.nexus.research-signal-bridge`
- Rollback command: `launchctl start com.nexus.research-signal-bridge`
- Expected impact: research signal bridge updates paused

## Exit Criteria
- Optional service is marked safe-to-pause only after two consecutive green validation cycles.
