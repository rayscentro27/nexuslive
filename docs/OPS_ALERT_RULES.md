# Ops Alert Rules

Complete reference for all detection rules in the Nexus Ops / Monitoring Worker.

---

## Rule: `stale_worker`

**File:** `ops_monitoring_worker/ops_rules.js` → `ruleStaleWorker()`

**What it detects:** A worker has not sent a heartbeat within the expected window.

| Condition | Severity |
|-----------|----------|
| Last heartbeat > 30 minutes | WARNING |
| Last heartbeat > 90 minutes | CRITICAL |

**Data source:** `worker_heartbeats` table — `last_heartbeat` column

**Example alert:**
```
🟡 [stale_worker] Worker research_worker_1 heartbeat is 45m old
🔴 [stale_worker] Worker has not sent a heartbeat in 120m
```

**Recommended action:** Check the worker process. Run `launchctl list | grep nexus` to see service status. Restart the service if needed.

---

## Rule: `queue_buildup`

**File:** `ops_monitoring_worker/ops_rules.js` → `ruleQueueBuildup()`

**What it detects:** The oldest pending job in the queue is waiting too long.

| Condition | Severity |
|-----------|----------|
| Oldest pending job > 15 minutes | WARNING |
| Oldest pending job > 60 minutes | CRITICAL |

**Data source:** `job_queue` table — oldest row with `status = 'pending'`

**Example alert:**
```
🟡 [queue_buildup] Oldest pending job is 22m old
🔴 [queue_buildup] Oldest pending job is 72m old — queue may be stalled
```

**Recommended action:** Check `job_queue` table for stuck jobs. Look for jobs with no consumer processing them.

---

## Rule: `dead_letter_growth`

**File:** `ops_monitoring_worker/ops_rules.js` → `ruleDeadLetterCount()`

**What it detects:** Too many jobs have failed and moved to dead-letter status.

| Condition | Severity |
|-----------|----------|
| Dead-letter count ≥ 5 | WARNING |
| Dead-letter count ≥ 20 | CRITICAL |

**Data source:** `job_queue` table — rows with `status = 'dead_letter'`

**Example alert:**
```
🟡 [dead_letter_growth] 7 jobs in dead-letter queue
🔴 [dead_letter_growth] 25 jobs in dead-letter queue — investigate failures
```

**Recommended action:** Query `job_queue WHERE status = 'dead_letter'` and examine `error_msg` for patterns. Fix root cause, then requeue or clear dead-letter entries.

---

## Rule: `repeated_failures`

**File:** `ops_monitoring_worker/ops_rules.js` → `ruleRepeatedFailures()`

**What it detects:** The same job type has failed multiple times — indicates a systematic issue.

| Condition | Severity |
|-----------|----------|
| Same job_type failed 3+ times | WARNING |
| Same job_type failed 10+ times | CRITICAL |

**Data source:** `job_queue` table — `job_type` grouped by failure count

**Example alert:**
```
🟡 [repeated_failures] Job type "grant_scan" has failed 4 time(s)
🔴 [repeated_failures] Job type "research_transcript" has failed 12 time(s)
```

**Recommended action:** Run the affected job manually with `--dry-run` to see the error. Check Supabase credentials, table existence, and source data availability.

---

## Rule: `queue_depth_spike`

**File:** `ops_monitoring_worker/ops_rules.js` → `ruleQueueDepth()`

**What it detects:** Total number of pending jobs is abnormally high.

| Condition | Severity |
|-----------|----------|
| Queue depth ≥ 50 | WARNING |
| Queue depth ≥ 200 | CRITICAL |

**Data source:** `job_queue` table — count of rows with `status = 'pending'`

**Example alert:**
```
🟡 [queue_depth_spike] Queue depth is 67
🔴 [queue_depth_spike] Queue depth is 215 — processing may be overwhelmed
```

**Recommended action:** Check if worker consumers are running. A depth spike usually means consumers stopped while producers kept adding jobs.

---

## Rule: `research_pipeline_stalled`

**File:** `ops_monitoring_worker/ops_rules.js` → `ruleResearchPipelineStalled()`

**What it detects:** No new research artifacts have been ingested in an extended period.

| Condition | Severity |
|-----------|----------|
| No new artifacts in 48+ hours | WARNING |

**Data source:** `research_artifacts` table — most recent `created_at`

**Example alert:**
```
🟡 [research_pipeline_stalled] No new research artifacts in 53h — research pipeline may be paused
```

**Recommended action:** Run `node workflows/autonomous_research_supernode/research_orchestrator.js --dry-run` to check for errors. Check yt-dlp availability and Supabase connectivity.

---

## Rule: `low_artifact_count`

**File:** `ops_monitoring_worker/ops_rules.js` → `ruleArtifactCount()`

**What it detects:** Total artifact count is very low — database may not be populated.

| Condition | Severity |
|-----------|----------|
| Total artifacts < 5 | INFO |

**Data source:** `research_artifacts` table — total row count

**Example alert:**
```
🔵 [low_artifact_count] Only 2 research artifact(s) in database — run research pipeline
```

**Recommended action:** Run the research pipeline to populate the database. This is normal on first setup.

---

## Severity Guide

| Severity | Action Required | Telegram |
|----------|-----------------|---------|
| CRITICAL | Immediate attention — system may be degraded | Always sent |
| WARNING | Investigate soon — threshold exceeded | Sent (default) |
| INFO | Informational — no immediate action needed | Only with `--threshold info` |

---

## Custom Thresholds

To modify thresholds, edit the constants in `ops_monitoring_worker/ops_rules.js`:

```js
// Example: tighten stale worker detection to 15 minutes
const WARNING_THRESHOLD_MS  = 15 * 60 * 1000;  // 15 minutes
const CRITICAL_THRESHOLD_MS = 45 * 60 * 1000;  // 45 minutes
```

---

## Adding New Rules

1. Add a new function to `ops_rules.js` following the pattern:
   ```js
   export function ruleMyNewCheck(metrics) {
     const alerts = [];
     if (/* condition */) {
       alerts.push({
         rule:     "my_check_name",
         severity: ALERT_SEVERITY.WARNING,
         message:  "Descriptive message",
         detail:   { /* relevant data */ },
       });
     }
     return alerts;
   }
   ```

2. Add it to the `ALL_RULES` array:
   ```js
   const ALL_RULES = [
     ...existing rules...,
     ruleMyNewCheck,
   ];
   ```

3. Document it in `OPS_ALERT_RULES.md` (this file).

Rules return an array (can return multiple alerts from one check) or null (not triggered).
