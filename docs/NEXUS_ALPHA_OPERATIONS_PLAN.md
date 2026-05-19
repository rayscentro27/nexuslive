# Nexus Alpha Operations Plan

**Created:** 2026-05-18  
**Status:** ACTIVE — Dispatch Task `f0bac469-4260-462b-bf57-221c75e1357a`  
**Safety:** NEXUS_DRY_RUN=true | LIVE_TRADING=false | REAL_MONEY=false

---

## Mission

Wake up the Nexus AI Workforce system and prove it can receive operational goals,
route them through the dispatcher, break them into subtasks, assign agents, track
progress in Supabase, and produce actionable outputs — all within safety rails.

---

## Four Active Lanes

| Lane | Subtasks | Lead Agent | Status |
|------|----------|------------|--------|
| Monetization | 5 | nexus_launch_engine + research_worker | queued |
| Opportunity Engine | 3 | research_worker + hermes_orchestrator | queued |
| Trading Research Lab | 7 | research_worker (paper-only) | queued, approval pending |
| Visual Trust | 3 | claude_code + qa_worker | queued |
| Operations | 1 | hermes_orchestrator | queued |

Total subtasks: **19 queued in Supabase**

---

## Dispatch Task IDs

| Resource | ID |
|----------|----|
| Parent task | `f0bac469-4260-462b-bf57-221c75e1357a` |
| Trading research approval | `674ac406-b3e8-446a-aa3d-c31bd61c83a9` |
| Activation event | `2225ab40-0547-4f98-9214-90f81ebe6608` |

---

## System Health at Activation

- Workers: 10/10 enabled
- Providers: 3/7 healthy (groq ✅, notebooklm ✅, openrouter ✅)
- Offline: claude_cli, codex, ollama, opencode
- Approval queue: 1 pending (trading research activation)
- Safety tests: 10/10 correct (blocks + allows)

---

## Priority Execution Order

**Immediate (this week):**
1. Monetization subtasks → define offers and pricing
2. Opportunity research → scored opportunity board
3. Visual trust audit → quick wins for homepage

**Requires approval first:**
4. Trading Research Lab subtasks → approve `674ac406` first

**Ongoing:**
5. Daily CEO digest format setup
6. Telegram status update cadence

---

## Safety Rules (Hard-Enforced)

The `lib/agent_dispatcher/risk.py` hard-blocks:
- Any prompt containing live trading, live forex, live broker, real money
- deploy to production, prod deploy, force push
- expose api key, expose secrets
- email blast, send to all clients, mass email
- drop table, delete all data, truncate table

These blocks cannot be overridden by approval — they require changing the code.

---

## How to Resume / Continue

```bash
# Check live task board
python3 bin/nexus health
python3 bin/nexus approvals list

# Approve the trading research gate
python3 bin/nexus approvals approve 674ac406-b3e8-446a-aa3d-c31bd61c83a9

# Dispatch new work
python3 bin/nexus dispatch "research top 5 affiliate programs for funding niche"

# View Supabase task board
# Admin → ⚡ Command → Dispatch Inbox
```

---

## Next Single Command

```bash
python3 bin/nexus approvals list
```
Then approve the trading research if ready.
