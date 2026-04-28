# Ops / Monitoring Worker

## Overview

The Ops / Monitoring Worker reads Nexus system health and queue metrics, evaluates detection rules, and sends Telegram alerts when thresholds are exceeded.

**This worker:**
- Reads Supabase tables (counts and metadata only — never full content)
- Evaluates configured detection rules
- Sends structured Telegram alerts and health summaries
- Runs on schedule or on-demand

**This worker never:**
- Writes to any business table
- Restarts services automatically
- Modifies system configuration
- Accesses client data or trading data

---

## Data Sources

| Source | Table / Endpoint | What It Reads |
|--------|-----------------|---------------|
| Research artifacts | `research_artifacts` | Total count, most recent created_at |
| Worker heartbeats | `worker_heartbeats` | worker_id, last_heartbeat, status |
| Job queue | `job_queue` | Pending jobs count, oldest pending, dead-letter count |
| System errors | `system_errors` | Recent error count by type |
| System mode | `NODE_ENV` env var | production / development |

All sources are **read-only**. If a table doesn't exist (e.g., `worker_heartbeats` not yet created), the worker silently skips it and defaults to null metrics.

**Not yet wired (future):**
- Oracle VM `/api/system/health` endpoint
- Oracle VM `/api/system/workers` endpoint
- Oracle VM `/api/system/jobs` endpoint

---

## Detection Rules

All rules are defined in `ops_rules.js`:

| Rule | Severity | Threshold |
|------|----------|-----------|
| Stale worker | WARNING | Last heartbeat > 30 minutes ago |
| Stale worker | CRITICAL | Last heartbeat > 90 minutes ago |
| Queue buildup | WARNING | Oldest pending job > 15 minutes |
| Queue buildup | CRITICAL | Oldest pending job > 60 minutes |
| Dead-letter growth | WARNING | Dead-letter count ≥ 5 |
| Dead-letter growth | CRITICAL | Dead-letter count ≥ 20 |
| Repeated failures | WARNING | Same job_type failed 3+ times |
| Repeated failures | CRITICAL | Same job_type failed 10+ times |
| Queue depth spike | WARNING | Total queue depth ≥ 50 |
| Queue depth spike | CRITICAL | Total queue depth ≥ 200 |
| Research pipeline stalled | WARNING | No new artifacts in 48+ hours |
| Low artifact count | INFO | Total artifacts < 5 |

---

## Alert Formats

### Critical Alert (Telegram)

```
🔴 NEXUS OPS — CRITICAL ALERT

🔴 Status: Needs attention
📦 Queue depth: 47
🔬 Artifacts: 82
⚙️  Workers: 3

🔴 Queue buildup: Oldest pending job is 72m old — queue may be stalled
🟡 Repeated failures: Job type "grant_scan" has failed 3 time(s)

💡 Check Supabase queue tables and worker heartbeats.
```

### Warning Alert (Telegram)

```
🟡 NEXUS OPS — WARNING

🟡 Worker heartbeat is 35m old
🟡 5 jobs in dead-letter queue

2026-03-13, 10:45 AM
```

### Healthy Summary (Telegram — `--summary` flag)

```
✅ NEXUS OPS SUMMARY

✅ Status: Healthy
📦 Queue depth: 3
🔬 Artifacts: 156
⚙️  Workers: 4

All checks passed.
```

### Console Health Report

```
╔═══════════════════════════════════════════════════════════╗
║  NEXUS OPS HEALTH REPORT                                  ║
╚═══════════════════════════════════════════════════════════╝
  Generated : 3/13/2026, 10:45:22 AM
  System    : production
  Artifacts : 156 total
  Queue     : 3 pending
  Workers   : 4 tracked

  ✅ All checks passed — no alerts.
```

---

## Direct Run Commands

```bash
cd ~/nexus-ai/workflows/ai_workforce

# Dry run — collect metrics, evaluate rules, no Telegram
node ops_monitoring_worker/ops_monitoring_worker.js --dry-run

# Standard run — alert only if thresholds exceeded
node ops_monitoring_worker/ops_monitoring_worker.js

# Always send full summary to Telegram
node ops_monitoring_worker/ops_monitoring_worker.js --summary

# Alert on critical only (suppress warnings)
node ops_monitoring_worker/ops_monitoring_worker.js --threshold critical

# Alert on everything including info
node ops_monitoring_worker/ops_monitoring_worker.js --threshold info

# Quiet mode (no console output)
node ops_monitoring_worker/ops_monitoring_worker.js --quiet

# Via dispatcher
node workforce_dispatcher.js --role ops_monitoring_worker --job ops_health_check --dry-run
```

---

## Queue Mode

```js
import { runOpsMonitoringWorker } from "./ops_monitoring_worker/ops_monitoring_worker.js";

// Health check — alert if warnings
const summary = await runOpsMonitoringWorker({
  dry_run: false,
  quiet: true,
  alert_threshold: "warning",
});

// Daily summary — always send
const summary = await runOpsMonitoringWorker({
  dry_run: false,
  summary_only: true,
  quiet: true,
});

// summary.overall_status = "healthy" | "warning" | "critical"
// summary.alerts = Array of triggered alerts
// summary.alert_count = { critical, warning, info }
```

---

## Scheduling (Cron Suggestion)

```bash
# Health check every 15 minutes (alert on warnings)
# launchd plist or cron:
# */15 * * * * node ~/nexus-ai/workflows/ai_workforce/ops_monitoring_worker/ops_monitoring_worker.js --quiet

# Daily summary at 8am
# 0 8 * * * node ~/nexus-ai/workflows/ai_workforce/ops_monitoring_worker/ops_monitoring_worker.js --summary --quiet
```

---

## Prerequisites

- `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in `.env`
- `research_artifacts` table must exist (standard prerequisite)
- `worker_heartbeats` table (optional — skipped gracefully if missing)
- `job_queue` table (optional — skipped gracefully if missing)
- `system_errors` table (optional — skipped gracefully if missing)

---

## Supabase Tables to Create (Optional)

For full monitoring capability, create these tables:

```sql
-- Worker heartbeats
CREATE TABLE worker_heartbeats (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  worker_id   TEXT NOT NULL,
  status      TEXT DEFAULT 'active',
  last_heartbeat TIMESTAMPTZ DEFAULT now(),
  metadata    JSONB
);

-- Job queue (if not already exists)
CREATE TABLE job_queue (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  job_type   TEXT NOT NULL,
  status     TEXT DEFAULT 'pending',  -- pending | running | completed | failed | dead_letter
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  payload    JSONB,
  error_msg  TEXT
);

-- System errors
CREATE TABLE system_errors (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  error_type TEXT NOT NULL,
  message    TEXT,
  context    JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```
