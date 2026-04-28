/**
 * handlers/digest.js — daily_system_digest job handler.
 *
 * Collects data from existing Supabase tables, builds a structured JSON digest,
 * optionally refines the summary via Hermes (Hermes), stores in system_digests,
 * and optionally sends a concise Telegram summary.
 */

import { db }           from '../supabase.js';
import { config }       from '../config.js';
import { createLogger } from '../logger.js';
import { emitAlert }    from '../lib/alerts.js';
import { sendTelegram } from '../lib/telegram.js';

const logger = createLogger('digest');

// ── Data collection ────────────────────────────────────────────────────────

async function collectDigestData(windowHours) {
  const since          = new Date(Date.now() - windowHours * 3600_000).toISOString();
  const heartbeatCutoff = new Date(Date.now() - 90_000).toISOString(); // 90s = stale

  const [workflows, jobs, heartbeats, alerts, recentOutputs] = await Promise.all([
    db.from('orchestrator_workflow_runs')
      .select('id, workflow_type, status')
      .gte('created_at', since),

    db.from('job_queue')
      .select('id, job_type, status')
      .gte('created_at', since),

    db.from('worker_heartbeats')
      .select('worker_id, status, last_heartbeat_at'),

    db.from('monitoring_alerts')
      .select('id, severity, summary')
      .gte('created_at', since)
      .is('resolved_at', null)
      .limit(10),

    db.from('workflow_outputs')
      .select('workflow_type, summary, status')
      .gte('created_at', since)
      .order('created_at', { ascending: false })
      .limit(5),
  ]);

  return {
    workflows:      workflows.data      ?? [],
    jobs:           jobs.data           ?? [],
    heartbeats:     heartbeats.data     ?? [],
    alerts:         alerts.data         ?? [],
    recentOutputs:  recentOutputs.data  ?? [],
    heartbeatCutoff,
  };
}

// ── Digest builder ─────────────────────────────────────────────────────────

function buildDigest(data, windowHours) {
  const { workflows, jobs, heartbeats, alerts, recentOutputs, heartbeatCutoff } = data;

  const completedWorkflows = workflows.filter(w => w.status === 'completed').length;
  const blockedWorkflows   = workflows.filter(w => w.status === 'blocked').length;
  const failedJobs         = jobs.filter(j => j.status === 'failed').length;
  const queueDepth         = jobs.filter(j => j.status === 'pending').length;
  const activeWorkers      = heartbeats.filter(h =>
    h.status === 'running' && h.last_heartbeat_at >= heartbeatCutoff
  ).length;
  const workersInError     = heartbeats.filter(h =>
    h.status === 'error' || (h.status === 'running' && h.last_heartbeat_at < heartbeatCutoff)
  ).length;

  // Workflow breakdown by type (completed only)
  const workflowBreakdown = { research: 0, funding: 0, credit: 0, signals: 0 };
  for (const w of workflows.filter(wf => wf.status === 'completed')) {
    const t = w.workflow_type?.toLowerCase() ?? '';
    if      (t.includes('research')) workflowBreakdown.research++;
    else if (t.includes('funding'))  workflowBreakdown.funding++;
    else if (t.includes('credit'))   workflowBreakdown.credit++;
    else if (t.includes('signal'))   workflowBreakdown.signals++;
  }

  // Top issues
  const topIssues = [];
  if (failedJobs > 0)       topIssues.push(`${failedJobs} job(s) failed`);
  if (blockedWorkflows > 0) topIssues.push(`${blockedWorkflows} workflow(s) blocked`);
  if (workersInError > 0)   topIssues.push(`${workersInError} worker(s) with stale/error heartbeat`);
  if (alerts.length > 0)    topIssues.push(`${alerts.length} open alert(s) in window`);
  if (queueDepth > 5)       topIssues.push(`Queue depth elevated: ${queueDepth} pending`);

  const topRecentOutputs = recentOutputs.map(o => ({
    workflow_type: o.workflow_type,
    summary:       o.summary ?? 'No summary available',
  }));

  const summary =
    `Over the last ${windowHours}h: ${completedWorkflows} workflow(s) completed, ` +
    `${blockedWorkflows} blocked, ${failedJobs} job(s) failed. ` +
    `${activeWorkers} active worker(s). Queue depth: ${queueDepth}.` +
    (topIssues.length > 0
      ? ` Issues: ${topIssues.slice(0, 2).join('; ')}.`
      : ' System healthy.');

  return {
    window_hours:       windowHours,
    generated_at:       new Date().toISOString(),
    totals: {
      completed_workflows: completedWorkflows,
      blocked_workflows:   blockedWorkflows,
      failed_jobs:         failedJobs,
      active_workers:      activeWorkers,
      workers_in_error:    workersInError,
      queue_depth:         queueDepth,
      alerts_count:        alerts.length,
    },
    workflow_breakdown:  workflowBreakdown,
    top_issues:          topIssues,
    top_recent_outputs:  topRecentOutputs,
    summary,
  };
}

// ── Optional Hermes refinement ─────────────────────────────────────────────

async function refineDigestSummary(digest) {
  if (!config.enableHermesDigestSynthesis) return null;
  try {
    const prompt =
      `You are the Nexus operations analyst. Refine this system digest into a concise ` +
      `executive summary (2–4 sentences). Focus on health status, blockers, and any ` +
      `recommended action for the operator.\n\n` +
      `Totals: ${JSON.stringify(digest.totals)}\n` +
      `Issues: ${digest.top_issues.join(', ') || 'none'}\n` +
      `Recent outputs: ${digest.top_recent_outputs.map(o => o.summary).join('; ') || 'none'}`;

    const res = await fetch(`${config.hermesUrl}/v1/chat/completions`, {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${config.hermesToken}`,
      },
      body: JSON.stringify({
        model:       config.hermesModel,
        messages:    [
          { role: 'system', content: 'You are a Nexus operations analyst. Be concise and direct.' },
          { role: 'user',   content: prompt },
        ],
        max_tokens:  200,
        temperature: 0.2,
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!res.ok) throw new Error(`Hermes ${res.status}`);
    const data = await res.json();
    return data?.choices?.[0]?.message?.content?.trim() ?? null;
  } catch (e) {
    logger.warn('hermes_digest_skipped', { error: e?.message });
    return null;
  }
}

// ── Main handler ───────────────────────────────────────────────────────────

export async function runDailySystemDigest(payload) {
  const windowHours = payload.window_hours ?? config.digestWindowHours;

  logger.info('digest_started', { window_hours: windowHours });

  let digest;
  try {
    const data = await collectDigestData(windowHours);
    digest = buildDigest(data, windowHours);
  } catch (err) {
    await emitAlert({
      alert_type: 'digest_generation_failure',
      severity:   'warning',
      title:      'Daily digest data collection failed',
      body:       err?.message,
      alert_key:  'digest_generation_failure:daily',
      metadata:   { error: err?.message },
    });
    throw err;
  }

  // Optional Hermes refinement
  const refined = await refineDigestSummary(digest);
  if (refined) {
    digest.summary        = refined;
    digest.hermes_refined = true;
  }

  // Store in system_digests
  try {
    await db.from('system_digests').insert({
      digest_type:  'daily',
      window_hours: windowHours,
      summary:      digest.summary,
      payload:      digest,
    });
  } catch (err) {
    logger.warn('digest_store_failed', { error: err?.message });
  }

  // Optional Telegram summary
  const tgText =
    `📊 *Nexus Daily Digest* (${windowHours}h)\n` +
    `✅ Completed: ${digest.totals.completed_workflows} workflows\n` +
    `⚠️ Blocked: ${digest.totals.blocked_workflows}  |  Failed jobs: ${digest.totals.failed_jobs}\n` +
    `👷 Workers active: ${digest.totals.active_workers}\n` +
    (digest.top_issues.length > 0
      ? `🔍 ${digest.top_issues.slice(0, 2).join(' | ')}\n`
      : `🟢 No issues\n`) +
    `\n_${digest.summary}_`;

  await sendTelegram(tgText, { enabled: config.enableTelegramDigests });

  logger.info('digest_complete', {
    window_hours:        windowHours,
    completed_workflows: digest.totals.completed_workflows,
    failed_jobs:         digest.totals.failed_jobs,
    hermes_refined:      !!refined,
  });

  return digest;
}
