/**
 * handlers/sweeper.js — stale_state_sweep job handler.
 *
 * Detects and alerts on:
 *   1. Stale jobs stuck in claimed/running
 *   2. Stale workflows stuck in running/active/pending
 *   3. Workers with missing/stale heartbeats
 *   4. Completed workflows missing a workflow_outputs row
 *
 * Never throws. Alerts are emitted via lib/alerts.js.
 * Conservative: only auto-requeues stale jobs when they are well past threshold
 * and the owning worker heartbeat is missing/stale. Only marks workflows blocked
 * if they've been stuck for 2× the stale threshold.
 */

import { db }           from '../supabase.js';
import { config }       from '../config.js';
import { createLogger } from '../logger.js';
import { emitAlert }    from '../lib/alerts.js';
import { sendTelegram } from '../lib/telegram.js';

const logger = createLogger('sweeper');

function minutesSince(iso) {
  if (!iso) return null;
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return null;
  return Math.round((Date.now() - ts) / 60_000);
}

function buildHeartbeatMap(rows) {
  return new Map((rows ?? []).map((row) => [row.worker_id, row]));
}

function isHeartbeatMissingOrStale(heartbeat, staleMinutes) {
  if (!heartbeat?.last_heartbeat_at) return true;
  const age = minutesSince(heartbeat.last_heartbeat_at);
  return age == null || age > staleMinutes;
}

async function safeRequeueJob(job, detail) {
  const availableAt = new Date(Date.now() + config.staleJobRecoveryDelaySeconds * 1000).toISOString();
  const recoveryNote = `[auto-requeued ${new Date().toISOString()}] ${detail}`;
  const nextLastError = job.last_error ? `${job.last_error}\n${recoveryNote}` : recoveryNote;

  const { data, error } = await db
    .from('job_queue')
    .update({
      status: 'pending',
      worker_id: null,
      leased_at: null,
      lease_expires_at: null,
      available_at: availableAt,
      last_error: nextLastError,
    })
    .eq('id', job.id)
    .eq('status', job.status)
    .select('id');

  if (error) throw error;
  return Boolean(data?.length);
}

// ── 1. Stale jobs ──────────────────────────────────────────────────────────

async function sweepStaleJobs(staleMinutes) {
  const cutoff = new Date(Date.now() - staleMinutes * 60_000).toISOString();
  const issues = [];
  let autoRequeued = 0;

  const { data: heartbeatRows } = await db
    .from('worker_heartbeats')
    .select('worker_id, status, last_heartbeat_at');
  const heartbeatMap = buildHeartbeatMap(heartbeatRows);

  const { data: staleJobs } = await db
    .from('job_queue')
    .select('id, job_type, status, worker_id, leased_at, lease_expires_at, workflow_id, last_error')
    .in('status', ['claimed', 'running'])
    .lt('leased_at', cutoff);

  for (const job of staleJobs ?? []) {
    const stuckMins = Math.round((Date.now() - new Date(job.leased_at).getTime()) / 60_000);
    const heartbeat = job.worker_id ? heartbeatMap.get(job.worker_id) : null;
    const heartbeatAge = heartbeat?.last_heartbeat_at ? minutesSince(heartbeat.last_heartbeat_at) : null;
    const leaseExpired = Boolean(job.lease_expires_at && new Date(job.lease_expires_at).getTime() < Date.now());
    const workerGone = isHeartbeatMissingOrStale(heartbeat, staleMinutes);
    const eligibleForAutoRequeue = Boolean(
      config.autoRequeueStaleJobs
      && stuckMins > staleMinutes * 2
      && (leaseExpired || workerGone || !job.worker_id),
    );

    let autoRecovery = 'none';
    if (eligibleForAutoRequeue) {
      const detail = leaseExpired
        ? `lease expired and worker heartbeat unavailable for ${job.worker_id ?? 'unknown worker'}`
        : `worker heartbeat stale for ${heartbeatAge ?? '?'}m`;
      const requeued = await safeRequeueJob(job, detail);
      if (requeued) {
        autoRequeued += 1;
        autoRecovery = 'requeued';
        logger.warn('stale_job_auto_requeued', {
          job_id: job.id,
          job_type: job.job_type,
          stuck_minutes: stuckMins,
          worker_id: job.worker_id,
          heartbeat_age_minutes: heartbeatAge,
          lease_expired: leaseExpired,
        });
      } else {
        autoRecovery = 'skipped_race';
      }
    }

    issues.push({
      type:                 'stale_job',
      job_id:               job.id,
      job_type:             job.job_type,
      body:                 `Job \`${job.job_type}\` stuck in \`${job.status}\` for ${stuckMins}m`,
      recommended_recovery: autoRecovery === 'requeued'
        ? 'Job was automatically re-queued after stale-worker detection.'
        : 'Check worker health. If worker is confirmed dead, reset job status to pending manually.',
      auto_recovery:        autoRecovery,
    });

    await emitAlert({
      alert_type:     'stale_job_detected',
      severity:       stuckMins > staleMinutes * 2 ? 'critical' : 'warning',
      title:          `Stale job: ${job.job_type} stuck in ${job.status} (${stuckMins}m)`,
      body:           `Job ${job.id} (${job.job_type}) has been in \`${job.status}\` for ${stuckMins} minutes. Worker: ${job.worker_id ?? 'unknown'}.`,
      alert_key:      `stale_job_detected:${job.id}`,
      source_service: config.workerId,
      worker_id:      job.worker_id,
      workflow_id:    job.workflow_id,
      job_id:         job.id,
      metadata: {
        job_type:             job.job_type,
        stuck_minutes:        stuckMins,
        leased_at:            job.leased_at,
        recommended_recovery: autoRecovery === 'requeued'
          ? 'Job was automatically re-queued after stale-worker detection.'
          : 'Check worker health. Reset job to pending if worker is confirmed dead.',
        operator_action:      autoRecovery === 'requeued' ? 'observe' : 'manual',
        auto_recovery:        autoRecovery,
        worker_heartbeat_age_minutes: heartbeatAge,
        lease_expired:        leaseExpired,
      },
    });
  }

  return { issues, auto_requeued: autoRequeued };
}

// ── 2. Stale workflows ─────────────────────────────────────────────────────

async function sweepStaleWorkflows(staleMinutes) {
  const cutoff = new Date(Date.now() - staleMinutes * 60_000).toISOString();
  const issues = [];

  const { data: staleWorkflows } = await db
    .from('orchestrator_workflow_runs')
    .select('id, workflow_type, status, tenant_id, created_at')
    .in('status', ['running', 'active', 'pending'])
    .lt('created_at', cutoff);

  for (const wf of staleWorkflows ?? []) {
    const stuckMins = Math.round((Date.now() - new Date(wf.created_at).getTime()) / 60_000);
    issues.push({
      type:                 'stale_workflow',
      workflow_id:          wf.id,
      workflow_type:        wf.workflow_type,
      body:                 `Workflow \`${wf.workflow_type}\` stuck in \`${wf.status}\` for ${stuckMins}m`,
      recommended_recovery: 'Check job_queue for this workflow_id. Worker may be stale or job was never enqueued.',
    });

    // Safe block: only mark blocked if stuck for 2× threshold
    if (stuckMins > staleMinutes * 2) {
      await db.from('orchestrator_workflow_runs')
        .update({ status: 'blocked' })
        .eq('id', wf.id)
        .eq('status', wf.status); // guard: only update if status unchanged
    }

    await emitAlert({
      alert_type:     'stale_workflow_detected',
      severity:       stuckMins > staleMinutes * 2 ? 'critical' : 'warning',
      title:          `Stale workflow: ${wf.workflow_type} (${wf.status}, ${stuckMins}m)`,
      body:           `Workflow ${wf.id} (${wf.workflow_type}) has been in \`${wf.status}\` for ${stuckMins} minutes.`,
      alert_key:      `stale_workflow_detected:${wf.id}`,
      source_service: config.workerId,
      workflow_id:    wf.id,
      tenant_id:      wf.tenant_id,
      metadata: {
        workflow_type:        wf.workflow_type,
        stuck_minutes:        stuckMins,
        recommended_recovery: 'Investigate job_queue for this workflow_id. Check worker heartbeats.',
        operator_action:      'review',
      },
    });
  }

  return issues;
}

// ── 3. Missing heartbeats ──────────────────────────────────────────────────

async function sweepMissingHeartbeats(staleMinutes) {
  const cutoff = new Date(Date.now() - staleMinutes * 60_000).toISOString();
  const issues = [];

  const { data: workers } = await db
    .from('worker_heartbeats')
    .select('worker_id, worker_type, status, last_heartbeat_at');

  for (const w of workers ?? []) {
    if (!w.last_heartbeat_at || w.last_heartbeat_at < cutoff) {
      const staleMin = w.last_heartbeat_at
        ? Math.round((Date.now() - new Date(w.last_heartbeat_at).getTime()) / 60_000)
        : null;

      issues.push({
        type:                 'missing_heartbeat',
        worker_id:            w.worker_id,
        body:                 `Worker \`${w.worker_id}\` last seen ${staleMin != null ? staleMin + 'm ago' : 'never'}`,
        recommended_recovery: 'Run: launchctl list | grep nexus — check worker service. Restart if offline.',
      });

      await emitAlert({
        alert_type:     'heartbeat_missing',
        severity:       staleMin != null && staleMin > staleMinutes * 3 ? 'critical' : 'warning',
        title:          `Worker \`${w.worker_id}\` heartbeat stale (${staleMin ?? '?'}m)`,
        body:           `Last heartbeat: ${w.last_heartbeat_at ?? 'never'}. Worker may be offline or stuck.`,
        alert_key:      `heartbeat_missing:${w.worker_id}`,
        source_service: config.workerId,
        worker_id:      w.worker_id,
        metadata: {
          worker_type:          w.worker_type,
          last_heartbeat_at:    w.last_heartbeat_at ?? 'never',
          stale_minutes:        staleMin,
          recommended_recovery: 'launchctl list | grep nexus — check worker launchd service',
          operator_action:      'check-launchd',
        },
      });
    }
  }

  return issues;
}

// ── 4. Missing workflow outputs ────────────────────────────────────────────

async function sweepMissingOutputs() {
  const issues = [];

  const { data: completedWorkflows } = await db
    .from('orchestrator_workflow_runs')
    .select('id, workflow_type, tenant_id, completed_at')
    .eq('status', 'completed')
    .order('completed_at', { ascending: false })
    .limit(50);

  if (!completedWorkflows?.length) return issues;

  const ids = completedWorkflows.map(w => w.id);
  const { data: outputs } = await db
    .from('workflow_outputs')
    .select('workflow_id')
    .in('workflow_id', ids);

  const outputIds = new Set((outputs ?? []).map(o => o.workflow_id));

  for (const wf of completedWorkflows) {
    if (!outputIds.has(wf.id)) {
      issues.push({
        type:                 'missing_workflow_output',
        workflow_id:          wf.id,
        workflow_type:        wf.workflow_type,
        body:                 `Completed workflow \`${wf.workflow_type}\` has no workflow_outputs row`,
        recommended_recovery: 'Check job_queue.payload.result for the associated job. Worker may have failed to call writeWorkflowOutput.',
      });

      await emitAlert({
        alert_type:     'missing_workflow_output',
        severity:       'info',
        title:          `Missing output: ${wf.workflow_type} completed without workflow_outputs`,
        body:           `Workflow ${wf.id} (${wf.workflow_type}) completed but has no workflow_outputs record.`,
        alert_key:      `missing_workflow_output:${wf.id}`,
        source_service: config.workerId,
        workflow_id:    wf.id,
        tenant_id:      wf.tenant_id,
        metadata: {
          workflow_type:        wf.workflow_type,
          completed_at:         wf.completed_at,
          recommended_recovery: 'Check job_queue.payload.result. Re-run writeWorkflowOutput if possible.',
          operator_action:      'review',
        },
      });
    }
  }

  return issues;
}

// ── Main handler ───────────────────────────────────────────────────────────

export async function runStaleStateSweep(payload) {
  const staleJobMins       = payload.stale_job_minutes       ?? config.staleJobMinutes;
  const staleWorkflowMins  = payload.stale_workflow_minutes  ?? config.staleWorkflowMinutes;
  const staleHeartbeatMins = payload.stale_heartbeat_minutes ?? config.staleHeartbeatMinutes;

  logger.info('sweep_started', { staleJobMins, staleWorkflowMins, staleHeartbeatMins });

  const [jobSweep, workflowIssues, heartbeatIssues, outputIssues] = await Promise.all([
    sweepStaleJobs(staleJobMins)
      .catch(e => { logger.error('sweep_jobs_err',       { error: e?.message }); return { issues: [], auto_requeued: 0 }; }),
    sweepStaleWorkflows(staleWorkflowMins)
      .catch(e => { logger.error('sweep_workflows_err',  { error: e?.message }); return []; }),
    sweepMissingHeartbeats(staleHeartbeatMins)
      .catch(e => { logger.error('sweep_heartbeats_err', { error: e?.message }); return []; }),
    sweepMissingOutputs()
      .catch(e => { logger.error('sweep_outputs_err',    { error: e?.message }); return []; }),
  ]);

  const jobIssues = jobSweep.issues;
  const autoRequeuedJobs = jobSweep.auto_requeued;
  const allIssues = [...jobIssues, ...workflowIssues, ...heartbeatIssues, ...outputIssues];

  // Telegram — only if there are issues (avoid noise on clean sweeps)
  if (allIssues.length > 0) {
    const tgText =
      `🧹 *Nexus Sweep Report*\n` +
      `🔴 Stale jobs: ${jobIssues.length}\n` +
      `♻️ Auto-requeued jobs: ${autoRequeuedJobs}\n` +
      `🟡 Stale workflows: ${workflowIssues.length}\n` +
      `💔 Missing heartbeats: ${heartbeatIssues.length}\n` +
      `📋 Missing outputs: ${outputIssues.length}\n` +
      (allIssues[0] ? `\n_${allIssues[0].body}_` : '');

    await sendTelegram(tgText, { enabled: config.enableTelegramSweepAlerts });
  }

  const result = {
    stale_jobs:          jobIssues.length,
    auto_requeued_jobs:  autoRequeuedJobs,
    stale_workflows:     workflowIssues.length,
    missing_heartbeats:  heartbeatIssues.length,
    missing_outputs:     outputIssues.length,
    total_issues:        allIssues.length,
    issues:              allIssues,
  };

  logger.info('sweep_complete', {
    stale_jobs:         jobIssues.length,
    auto_requeued_jobs: autoRequeuedJobs,
    stale_workflows:    workflowIssues.length,
    missing_heartbeats: heartbeatIssues.length,
    missing_outputs:    outputIssues.length,
    total_issues:       allIssues.length,
  });

  return result;
}
