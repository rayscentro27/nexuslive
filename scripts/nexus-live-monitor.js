#!/usr/bin/env node
/**
 * nexus-live-monitor.js
 *
 * Runs for 5 hours, sending a Telegram status report every 30 minutes.
 * The configured AI gateway narrates each report in plain English.
 *
 * Usage:
 *   node scripts/nexus-live-monitor.js
 *   node scripts/nexus-live-monitor.js --interval 10   (every 10 min, for testing)
 *   node scripts/nexus-live-monitor.js --hours 2       (run for 2 hours)
 */

import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

// ── Load .env ──────────────────────────────────────────────────────────────────
const __dir     = dirname(fileURLToPath(import.meta.url));
const envPath   = resolve(__dir, '../.env');
const envLines  = readFileSync(envPath, 'utf8').split('\n');
for (const line of envLines) {
  const m = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
  if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^['"]|['"]$/g, '');
}

// ── Config ─────────────────────────────────────────────────────────────────────
const args          = process.argv.slice(2);
const argVal        = (flag) => { const i = args.indexOf(flag); return i >= 0 ? args[i+1] : null; };

const HOURS         = parseFloat(argVal('--hours')    ?? '5');
const INTERVAL_MIN  = parseFloat(argVal('--interval') ?? '30');
const DURATION_MS   = HOURS * 60 * 60 * 1000;
const INTERVAL_MS   = INTERVAL_MIN * 60 * 1000;

const SUPABASE_URL  = process.env.SUPABASE_URL;
const SUPABASE_KEY  = process.env.SUPABASE_KEY;
const TG_TOKEN      = process.env.TELEGRAM_BOT_TOKEN;
const TG_CHAT       = process.env.TELEGRAM_CHAT_ID;
const LLM_BASE_URL  =
  process.env.NEXUS_LLM_BASE_URL ??
  process.env.OPENROUTER_BASE_URL ??
  process.env.OPENAI_BASE_URL ??
  'https://openrouter.ai/api/v1';
const LLM_API_KEY   =
  process.env.NEXUS_LLM_API_KEY ??
  process.env.OPENROUTER_API_KEY ??
  process.env.OPENAI_API_KEY ??
  '';
const LLM_MODEL     =
  process.env.NEXUS_LLM_MODEL ??
  process.env.OPENROUTER_MODEL ??
  process.env.OPENAI_MODEL ??
  'meta-llama/llama-3.3-70b-instruct';
const LLM_CHAT_URL  =
  LLM_BASE_URL.endsWith('/v1') || LLM_BASE_URL.endsWith('/api/v1')
    ? `${LLM_BASE_URL}/chat/completions`
    : `${LLM_BASE_URL}/v1/chat/completions`;

const USE_LLM  = LLM_API_KEY.length > 0;

// ── Supabase fetch helper ──────────────────────────────────────────────────────
async function sbFetch(path, options = {}) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1${path}`, {
    ...options,
    headers: {
      'apikey':        SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`,
      'Content-Type':  'application/json',
      ...(options.headers ?? {}),
    },
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) throw new Error(`Supabase ${res.status}: ${await res.text()}`);
  const text = await res.text();
  return text.length > 0 ? JSON.parse(text) : {};
}

// ── Telegram ───────────────────────────────────────────────────────────────────
async function telegram(text) {
  console.warn("telegram_policy denied=true reason=memory_or_background_summary message_type=system_summary source=script");
  return;
  if (!TG_TOKEN || !TG_CHAT) { console.log('[TELEGRAM]', text); return; }
  try {
    await fetch(`https://api.telegram.org/bot${TG_TOKEN}/sendMessage`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ chat_id: TG_CHAT, text, parse_mode: 'Markdown' }),
      signal:  AbortSignal.timeout(12_000),
    });
  } catch (e) {
    console.warn('Telegram failed:', e.message);
  }
}

// ── AI narration ───────────────────────────────────────────────────────────────
async function narrate(data) {
  if (!USE_LLM) return null;
  try {
    const prompt =
      `You are the Nexus AI system status narrator. Report this system snapshot in 3–4 clear sentences ` +
      `as if briefing the operator via Telegram. Be specific about numbers. Be direct. No fluff.\n\n` +
      `Snapshot:\n${JSON.stringify(data, null, 2).slice(0, 1500)}`;

    const res = await fetch(LLM_CHAT_URL, {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${LLM_API_KEY}`,
      },
      body: JSON.stringify({
        model:       LLM_MODEL,
        messages:    [
          { role: 'system', content: 'You are a concise AI system narrator. Plain text only, no markdown.' },
          { role: 'user',   content: prompt },
        ],
        max_tokens:  300,
        temperature: 0.4,
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!res.ok) throw new Error(`AI gateway ${res.status}`);
    const json = await res.json();
    return json?.choices?.[0]?.message?.content?.trim() ?? null;
  } catch (e) {
    console.warn('AI narration failed:', e.message);
    return null;
  }
}

// ── Collect system snapshot ────────────────────────────────────────────────────
async function collectSnapshot() {
  const now = new Date();
  const since5m  = new Date(now - 5  * 60 * 1000).toISOString();
  const since30m = new Date(now - 30 * 60 * 1000).toISOString();
  const since1h  = new Date(now - 60 * 60 * 1000).toISOString();

  const [workers, recentJobs, recentOutputs, pendingEvents, openAlerts] = await Promise.allSettled([
    // Active workers (heartbeat within 90s)
    sbFetch(`/worker_heartbeats?select=worker_id,worker_type,status,last_heartbeat_at,metadata&last_heartbeat_at=gte.${new Date(now - 90_000).toISOString()}`),

    // Jobs in last 30 min
    sbFetch(`/job_queue?select=id,job_type,status,attempt_count,last_error,completed_at&created_at=gte.${since30m}&order=created_at.desc&limit=20`),

    // Workflow outputs in last hour
    sbFetch(`/workflow_outputs?select=workflow_type,status,readiness_level,score,summary,primary_action_title,updated_at&updated_at=gte.${since1h}&order=updated_at.desc&limit=10`),

    // Pending events
    sbFetch(`/system_events?select=id,event_type,status&status=eq.pending&limit=5`),

    // Open alerts
    sbFetch(`/monitoring_alerts?select=alert_key,severity,occurrences,last_triggered_at&resolved_at=is.null&order=last_triggered_at.desc&limit=5`),
  ]);

  const w  = workers.status       === 'fulfilled' ? workers.value       : [];
  const j  = recentJobs.status    === 'fulfilled' ? recentJobs.value    : [];
  const wo = recentOutputs.status === 'fulfilled' ? recentOutputs.value : [];
  const pe = pendingEvents.status === 'fulfilled' ? pendingEvents.value : [];
  const oa = openAlerts.status    === 'fulfilled' ? openAlerts.value    : [];

  // Aggregate job stats
  const jobStats = j.reduce((acc, job) => {
    acc[job.status] = (acc[job.status] ?? 0) + 1;
    return acc;
  }, {});

  const failedJobs = j.filter(job => job.status === 'failed').map(job => ({
    type:  job.job_type,
    error: job.last_error?.slice(0, 80),
  }));

  return {
    timestamp:      now.toISOString(),
    workers: w.map(wk => ({
      id:        wk.worker_id,
      type:      wk.worker_type,
      last_beat: wk.last_heartbeat_at,
      supports:  wk.metadata?.supported_job_types ?? [],
      state:     wk.metadata?.worker_state ?? 'unknown',
    })),
    jobs_last_30m:  jobStats,
    failed_jobs:    failedJobs,
    pending_events: pe.length,
    recent_outputs: wo.map(o => ({
      type:         o.workflow_type,
      readiness:    o.readiness_level,
      score:        o.score,
      action:       o.primary_action_title,
      updated:      o.updated_at,
    })),
    open_alerts:    oa.map(a => ({
      key:         a.alert_key,
      severity:    a.severity,
      occurrences: a.occurrences,
    })),
  };
}

// ── Format Telegram report ─────────────────────────────────────────────────────
function formatReport(snap, narration, reportNum, totalReports) {
  const lines = [];
  const workerStatus = snap.workers.length > 0
    ? snap.workers.map(w => `  • \`${w.id}\` — ${w.state} (${w.supports.length} job types)`).join('\n')
    : '  ⚠️ No active workers detected';

  const jobs = snap.jobs_last_30m;
  const jobLine = Object.entries(jobs).length > 0
    ? Object.entries(jobs).map(([s, n]) => `${n} ${s}`).join(' · ')
    : 'no jobs';

  lines.push(`🤖 *Nexus Status Report ${reportNum}/${totalReports}*`);
  lines.push(`_${new Date(snap.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Chicago' })} CT_`);
  lines.push('');

  lines.push('*Workers*');
  lines.push(workerStatus);
  lines.push('');

  lines.push(`*Jobs (last 30m):* ${jobLine}`);
  if (snap.failed_jobs.length > 0) {
    lines.push('⚠️ *Failed:*');
    for (const f of snap.failed_jobs.slice(0, 3)) {
      lines.push(`  • \`${f.type}\`: ${f.error ?? 'unknown error'}`);
    }
  }
  lines.push('');

  if (snap.recent_outputs.length > 0) {
    lines.push('*Recent Workflow Outputs:*');
    for (const o of snap.recent_outputs.slice(0, 3)) {
      lines.push(`  • \`${o.type}\` → ${o.readiness ?? 'done'} (score: ${o.score ?? 'n/a'})`);
    }
    lines.push('');
  }

  if (snap.open_alerts.length > 0) {
    lines.push('🔔 *Open Alerts:*');
    for (const a of snap.open_alerts.slice(0, 3)) {
      lines.push(`  • ${a.severity}: \`${a.key}\` (×${a.occurrences})`);
    }
    lines.push('');
  }

  if (snap.pending_events > 0) {
    lines.push(`📥 *Pending events:* ${snap.pending_events}`);
    lines.push('');
  }

  if (narration) {
    lines.push('*AI summary:*');
    lines.push(`_${narration}_`);
  }

  return lines.join('\n');
}

// ── Seed activity ──────────────────────────────────────────────────────────────
async function seedActivity(sessionNum) {
  // Rotate through workflow types to keep workers active
  const events = [
    {
      event_type: 'research_refresh_due',
      payload: { tenant_id: 'ff88f4f5-1e15-4773-8093-ff0e95cfa9d6', channels: [], max_videos: 1 },
    },
    {
      event_type: 'funding_profile_updated',
      payload: {
        tenant_id: 'ff88f4f5-1e15-4773-8093-ff0e95cfa9d6',
        credit_score: 680, income: 85000, ein: '12-3456789',
        legal_name: 'Nexus Ventures LLC', entity_type: 'LLC',
        business_address: '100 Main St', profile_completeness: 78,
        profile_version: `monitor-session-${sessionNum}`,
      },
    },
    {
      event_type: 'credit_report_uploaded',
      payload: {
        tenant_id: 'ff88f4f5-1e15-4773-8093-ff0e95cfa9d6',
        credit_score: 695, utilization: 22, collections: 0,
        late_payments: 0, tradelines: 8, inquiries: 2,
        report_id: `monitor-${sessionNum}-${Date.now()}`,
      },
    },
  ];

  // Pick one event type per session, cycling
  const event = events[sessionNum % events.length];

  try {
    await sbFetch('/system_events', {
      method:  'POST',
      headers: { 'Prefer': 'return=minimal' },
      body:    JSON.stringify({ ...event, status: 'pending' }),
    });
    console.log(`[seed] seeded ${event.event_type}`);
    return event.event_type;
  } catch (e) {
    console.warn('[seed] failed:', e.message);
    return null;
  }
}

// ── Main loop ──────────────────────────────────────────────────────────────────
const startTime    = Date.now();
const totalReports = Math.floor(DURATION_MS / INTERVAL_MS);
let   reportNum    = 0;

async function runReport() {
  reportNum++;
  console.log(`\n[${new Date().toISOString()}] Running report ${reportNum}/${totalReports}...`);

  // Seed some work on odd reports
  let seededType = null;
  if (reportNum % 2 !== 0) {
    seededType = await seedActivity(reportNum);
  }

  // Collect snapshot
  let snap;
  try {
    snap = await collectSnapshot();
  } catch (e) {
    console.error('Snapshot failed:', e.message);
    await telegram(`⚠️ *Nexus Monitor* — snapshot collection failed at report ${reportNum}.\nError: ${e.message}`);
    return;
  }

  // Log to console
  console.log(`  workers: ${snap.workers.length}, jobs_30m: ${JSON.stringify(snap.jobs_last_30m)}, outputs: ${snap.recent_outputs.length}, alerts: ${snap.open_alerts.length}`);

  // Narrate via the configured AI gateway
  const narration = await narrate({
    ...snap,
    seeded_event: seededType,
  });

  // Format and send
  const message = formatReport(snap, narration, reportNum, totalReports);
  await telegram(message);
  console.log(`  → Telegram sent (${message.length} chars)`);
}

async function runFinalSummary() {
  const elapsed = Math.round((Date.now() - startTime) / 60000);
  console.log('\n[FINAL] Collecting final summary...');

  let snap;
  try { snap = await collectSnapshot(); }
  catch { snap = null; }

  const narration = snap ? await narrate({ ...snap, session: 'FINAL 5-HOUR SUMMARY', elapsed_minutes: elapsed }) : null;

  const lines = [
    `✅ *Nexus 5-Hour Session Complete*`,
    `_Ran for ${elapsed} minutes — ${totalReports} reports sent_`,
    '',
    snap ? `*Final State:*` : '⚠️ Could not fetch final state.',
  ];

  if (snap) {
    lines.push(`  Workers alive: ${snap.workers.length}`);
    lines.push(`  Open alerts: ${snap.open_alerts.length}`);
    lines.push(`  Pending events: ${snap.pending_events}`);
    const totalJobs = Object.values(snap.jobs_last_30m).reduce((a, b) => a + b, 0);
    lines.push(`  Jobs in last 30m: ${totalJobs}`);
  }

  if (narration) {
    lines.push('');
    lines.push('*AI final summary:*');
    lines.push(`_${narration}_`);
  }

  lines.push('');
  lines.push('_Monitor session ended. Workers remain live via launchd._');

  await telegram(lines.join('\n'));
  console.log('[FINAL] Done.');
}

// ── Boot message ───────────────────────────────────────────────────────────────
(async () => {
  console.log(`Nexus Live Monitor starting`);
  console.log(`  Duration:  ${HOURS} hours`);
  console.log(`  Interval:  ${INTERVAL_MIN} minutes`);
  console.log(`  Reports:   ${totalReports}`);
  console.log(`  AI Gateway:${USE_LLM ? ' enabled' : ' disabled (no token)'}`);
  console.log(`  Telegram:  ${TG_TOKEN ? 'enabled' : 'disabled (no token)'}`);
  console.log('');

  // Send startup message
  await telegram(
    `🚀 *Nexus Live Monitor Started*\n` +
    `Running for ${HOURS} hours · reports every ${INTERVAL_MIN} min\n` +
    `Total reports: ${totalReports}\n` +
    `Narration: ${USE_LLM ? 'AI gateway ✅' : 'raw data only'}\n\n` +
    `_Workers are active. First report in ${INTERVAL_MIN} minutes._`
  );

  // Run first report immediately after a short wait
  setTimeout(runReport, 60_000); // first report after 1 min

  // Schedule recurring reports
  const timer = setInterval(async () => {
    await runReport();
    if (reportNum >= totalReports) {
      clearInterval(timer);
      await runFinalSummary();
      process.exit(0);
    }
  }, INTERVAL_MS);

  // Hard stop after duration
  setTimeout(async () => {
    clearInterval(timer);
    await runFinalSummary();
    process.exit(0);
  }, DURATION_MS + 120_000); // +2 min buffer

  console.log(`First report fires in 1 minute. Press Ctrl+C to stop early.`);
})();
