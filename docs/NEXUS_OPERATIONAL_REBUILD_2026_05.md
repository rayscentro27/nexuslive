# Nexus Operational Rebuild — Architecture Document
# Status: IMPLEMENTED | Date: 2026-05-25
# Scope: Phase 3 Rebuild — Real Execution, Evidence-Based, Claw3D Integration

---

## WHAT CHANGED

The previous system was a cosmetic simulation. This rebuild replaces it with a real
operational AI workforce platform. Every component now produces verifiable outputs.

---

## PART 1 — CLAW3D INTEGRATION

**Repo:** https://github.com/iamlukethedev/Claw3D  
**Install:** `~/nexus-claw3d/` (cloned 2026-05-25)  
**Version:** 0.1.4  
**Tech:** Next.js 16 + React 19 + Three.js + WebSocket  

### How it connects to Nexus

```
Claw3D (localhost:3000)
    ↓ WebSocket (ws://localhost:18789)
Hermes Adapter (npm run hermes-adapter)
    ↓ HTTP
Hermes Gateway (http://127.0.0.1:8642)
    ↓
Supabase (worker_heartbeats, job_queue, agent_dispatch_tasks)
```

Agent movement and status in Claw3D reflects **real** Supabase state:
- `worker_heartbeats` → who is active/idle/stalled
- `job_queue` → what is being processed
- `agent_dispatch_tasks` → task history and progress
- `orchestrator_workflow_runs` → active workflow runs
- `provider_health` → provider availability

### To start

```bash
# Terminal 1 — Hermes adapter bridge
cd ~/nexus-claw3d && npm run hermes-adapter

# Terminal 2 — Claw3D app
cd ~/nexus-claw3d && npm run dev

# OR use the helper script:
bash scripts/start_claw3d.sh
```

Open: http://localhost:3000  
Connect to: `ws://localhost:18789` (Hermes adapter)

### Configuration

`~/nexus-claw3d/.env`:
```
NEXT_PUBLIC_GATEWAY_URL=ws://localhost:18789
CLAW3D_GATEWAY_ADAPTER_TYPE=hermes
HERMES_API_URL=http://127.0.0.1:8642
HERMES_ADAPTER_PORT=18789
```

---

## PART 2 — HERMES UPGRADE

Hermes internal-first routing now handles 11 topic categories before falling to LLM.

### Routing order (Phase priority)

1. **Phase 1** — Conversational patterns (greetings, acknowledgements)
2. **Phase 1.5** — Opportunity Intelligence (URLs, business ideas, SaaS)
3. **Phase 2** — Keyword topics:
   - opencode, funding, today, knowledge_email, marketing, travel
   - notebooklm, ai_providers, trading, circuit_breaker
   - **NEW:** workforce, ceo_briefing, claw3d, evidence, improvement

### New trigger phrases

| Topic | Trigger phrases |
|-------|----------------|
| `workforce` | "workforce status", "worker status", "which workers are active", "ai workforce" |
| `ceo_briefing` | "ceo briefing", "morning briefing", "daily briefing", "give me the briefing" |
| `claw3d` | "claw3d", "3d office", "virtual office", "office status" |
| `evidence` | "evidence guard", "false completions", "audit completions", "evidence status" |
| `improvement` | "improvement queue", "autonomous improvement", "what is nexus doing" |

### Internal-first principle

When Ray asks any operational question, Hermes:
1. Searches Nexus internal Supabase data FIRST
2. Uses operational memory and config
3. ONLY falls to LLM/OpenRouter as final fallback
4. Cites the data source in every reply (source field)

---

## PART 3 — EXECUTOR WORKFORCE

### Worker registry (WORKER_ROLES in worker_accountability.py)

| Worker ID | Role |
|-----------|------|
| opencode_codex | Implementation Operator |
| claude_code | Architecture Designer |
| openclaude | Review & Refinement |
| hermes_gateway | Chief of Staff / Intelligence |
| opportunity_worker | Opportunity Intelligence |
| research_worker | Research Intelligence |
| content_worker | Content Engine |
| provider_health_worker | Infrastructure Monitor |
| coordination_worker | Workflow Coordinator |
| optimization_worker | Optimization Engine |
| improvement_worker | Autonomous Improvement |
| user_intelligence_worker | User Intelligence |
| ceo_brief_worker | CEO Intelligence |

### Productivity scoring formula

```
score = (completion_rate × 40) + ((1 - failure_rate) × 20)
      + (evidence_ratio × 30) + ((1 - false_completion_rate) × 10)
```

Range: 0–100. A worker with:
- 100% completed, 100% evidence, 0 failures, 0 false completions = **100.0**
- Mostly planned tasks, no evidence = **< 20.0**

### New Supabase tables

| Table | Purpose |
|-------|---------|
| `worker_productivity_rollups` | Daily per-worker metrics (unique by report_date + worker_id) |
| `worker_daily_reports` | Generated markdown reports per worker |
| `worker_recommendations` | Autonomous improvement suggestions |
| `ceo_briefings` | Stored CEO briefings with delivery log |

### Evidence columns on agent_dispatch_tasks

```sql
evidence_type    TEXT  -- file_path | db_row_id | screenshot | commit_hash | url | execution_log | message_id
evidence_ref     TEXT  -- the actual value
evidence_notes   TEXT
false_completion BOOLEAN NOT NULL DEFAULT false
```

---

## PART 4 — CEO MORNING BRIEFING SYSTEM

**Module:** `lib/ceo_morning_briefing.py`

### Briefing sections

1. **System Health** — active/stalled workers, queue failed/pending, false completions
2. **Workforce Performance** — top workers, inactive count, failed tasks
3. **Business Growth** — open recommendations, top 3 opportunities
4. **Content Status** — drafts pending, YouTube scripts queued
5. **Infrastructure** — Oracle reachability, Supabase config, provider health
6. **Top 5 Actions** — priority-ordered, urgency-flagged action list

### Delivery

```python
from lib.ceo_morning_briefing import generate_morning_briefing, deliver_briefing
briefing = generate_morning_briefing()
log = deliver_briefing(briefing)  # saves to Supabase, optionally Telegram
```

Telegram delivery: `TELEGRAM_AUTO_REPORTS_ENABLED=true` + `HERMES_BOT_TOKEN` + `TELEGRAM_CHAT_ID`

### CLI

```bash
python3 bin/nexus ceo briefing
```

---

## PART 5 — EVIDENCE-BASED EXECUTION (ANTI-DEMO)

**Module:** `lib/evidence_guard.py`

### Valid task statuses

| Status | Meaning |
|--------|---------|
| `planned` | Only a plan exists — no execution started |
| `received` | Initial state when task arrives |
| `running` | Transient — task is actively executing |
| `awaiting_approval` | Work done, waiting for human sign-off |
| `completed_with_evidence` | Done AND evidence verified |
| `failed` | Failed with reason |

### BANNED: `completed` without evidence

Any task marked `completed` with no `evidence_type` is flagged as a false completion.

### Evidence types

| Type | What it proves |
|------|---------------|
| `file_path` | Output file exists on disk (verified by guard) |
| `db_row_id` | Supabase row was created/updated |
| `screenshot` | Screenshot file exists on disk (verified) |
| `commit_hash` | Git commit SHA (validated as hex) |
| `url` | Published artifact URL (validated format) |
| `execution_log` | Log file exists on disk (verified) |
| `message_id` | Telegram/email message ID |

### Usage

```python
from lib.evidence_guard import Evidence, safe_complete_task

evidence = Evidence(
    evidence_type="file_path",
    evidence_ref="/Users/raymonddavis/nexus-ai/docs/NEXUS_CEO_DIGEST_2026_05_19.md",
)
safe_complete_task(task_id, evidence)
```

### Audit

```bash
python3 bin/nexus hermes audit  # shows false completions, routes, queue
```

---

## PART 6 — AUTONOMOUS IMPROVEMENT MODE

**Module:** `lib/autonomous_improvement_queue.py`

### Safe autonomous task types

| Type | Description |
|------|-------------|
| `doc_audit` | Scan docs for stale/duplicate files |
| `seo_improvement` | Generate SEO metadata for draft content |
| `draft_content` | Generate draft content |
| `opportunity_summary` | Summarize open recommendations |
| `doc_organization` | Organize docs directory |
| `recommendation_generation` | Generate monetization recommendations |
| `affiliate_audit` | Audit affiliate application status |
| `analytics_review` | Review research artifact trends |
| `stale_record_cleanup` | Flag stalled running tasks |
| `system_audit` | Audit agent_dispatch_tasks for false completions |
| `link_check` | Validate external URLs |
| `worker_report` | Generate daily productivity rollups |

### Unsafe (always require human approval)

- publish, billing, deploy, delete_records, auth_change, financial_action, send_email, send_telegram

### Worker loop

```python
from lib.autonomous_improvement_queue import seed_improvement_tasks, claim_idle_task
# When idle:
seed_improvement_tasks(limit=3)
task = claim_idle_task(worker_id="improvement_worker")
# Execute task, then:
safe_complete_task(task["id"], Evidence(evidence_type="db_row_id", evidence_ref=row_id))
```

---

## PART 7 — CLI COMMANDS

All commands:

```bash
python3 bin/nexus workforce status          # live worker status
python3 bin/nexus workforce productivity    # productivity scores (--days N)
python3 bin/nexus workforce assign <wid>    # assign task to worker --task '...'
python3 bin/nexus workforce report          # compute + print today's rollup

python3 bin/nexus ceo briefing             # generate + save CEO morning briefing

python3 bin/nexus claw3d status            # check Claw3D install + config
python3 bin/nexus claw3d start             # print startup instructions

python3 bin/nexus hermes audit             # evidence scan + routing test + queue status

# Existing commands still work:
python3 bin/nexus health
python3 bin/nexus report
python3 bin/nexus worker list
python3 bin/nexus dispatch "do X"
python3 bin/nexus approvals list
```

---

## LAUNCH CHECKLIST

### Immediate (today)

- [x] Claw3D cloned to ~/nexus-claw3d
- [x] Claw3D .env configured (Hermes gateway)
- [ ] `cd ~/nexus-claw3d && npm install` (running in background)
- [ ] `bash scripts/start_claw3d.sh` — launch 3D office

### Worker accountability

- [x] DB migration applied (worker_productivity_rollups, worker_daily_reports, worker_recommendations, ceo_briefings)
- [x] Evidence columns on agent_dispatch_tasks
- [x] 7 legacy false completions detected by audit
- [x] 3 autonomous improvement tasks seeded

### Daily operation

1. Morning: `python3 bin/nexus ceo briefing` (or ask Hermes: "give me the briefing")
2. Check: `python3 bin/nexus hermes audit`
3. Workforce: `python3 bin/nexus workforce status`
4. 3D view: `bash scripts/start_claw3d.sh` → http://localhost:3000

---

## WHAT IS NOT FAKE

Everything in this system now produces:
- A file path (verifiable)
- A DB row ID (queryable)
- A screenshot (viewable)
- A commit hash (auditable)
- A URL (clickable)
- A log entry (readable)
- A message ID (traceable)

If it doesn't have one of these, it is **status='planned'** — not completed.

---

*Nexus Operational Rebuild — 2026-05-25*  
*Evidence-based. Anti-demo. Real workforce. Real outputs.*
