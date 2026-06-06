/**
 * Netlify function: approval-notify
 *
 * Creates a Supabase notification + optionally sends a Telegram message
 * when an approval item changes state.
 *
 * Required env vars (Netlify dashboard):
 *   SUPABASE_URL              — Supabase REST URL
 *   SUPABASE_SERVICE_ROLE_KEY — service role key (server-side only, never in frontend)
 *   TELEGRAM_BOT_TOKEN        — optional; if missing, Telegram step is skipped gracefully
 *   TELEGRAM_CHAT_ID          — optional; same
 *
 * Optional gates:
 *   TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED=true  — enables normal-priority approvals
 *   TELEGRAM_CRITICAL_ALERTS_ENABLED=true         — enables critical/urgent approvals (default true)
 *   NEXUS_DASHBOARD_URL                           — base URL for deep links in Telegram messages
 *
 * Dedup strategy:
 *   - SHA-256 hash of `approval_id::status` stored in hermes_aggregates
 *   - 5-minute cooldown window per approval+status combination
 *   - Prevents duplicate Telegram sends on rapid re-renders / retries
 *
 * Safety:
 *   - Only POST accepted
 *   - Validates required fields
 *   - Does NOT execute any action — only updates notification state
 *   - Live trading / publishing / outreach actions are NOT triggered here
 */

const crypto = require('crypto');

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

// Priority → Telegram gate mapping
// critical/urgent: respects TELEGRAM_CRITICAL_ALERTS_ENABLED (default true)
// normal: respects TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED (default false)
// low: no Telegram, Supabase notification only
function telegramAllowed(priority) {
  const flag = (name, def = 'false') =>
    (process.env[name] || def).toLowerCase() === 'true';
  if (priority === 'urgent' || priority === 'critical') {
    return flag('TELEGRAM_CRITICAL_ALERTS_ENABLED', 'true');
  }
  if (priority === 'normal') {
    return flag('TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED', 'false');
  }
  return false; // low → no Telegram
}

// Risk level from action_type
const ACTION_RISK = {
  bulk_outreach:    'critical',
  email_outreach:   'high',
  ad_spend:         'critical',
  live_trading:     'critical',
  credential_change: 'critical',
  rls_change:       'critical',
  schema_change:    'high',
  budget_change:    'high',
  content_publish:  'medium',
  deploy_code:      'medium',
  affiliate_activate: 'medium',
  client_message:   'medium',
};
function riskLevel(actionType) {
  return ACTION_RISK[actionType] || 'low';
}

// SHA-256 dedup hash
function dedupHash(approvalId, status) {
  return crypto.createHash('sha256')
    .update(`${approvalId}::${status}`)
    .digest('hex')
    .slice(0, 16);
}

// Supabase REST helpers
function sbHeaders(key) {
  return {
    'apikey': key,
    'Authorization': `Bearer ${key}`,
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal',
  };
}

async function sbPost(url, key, table, body) {
  const res = await fetch(`${url}/rest/v1/${table}`, {
    method: 'POST',
    headers: sbHeaders(key),
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(8000),
  });
  return res.ok;
}

async function sbGet(url, key, path) {
  const res = await fetch(`${url}/rest/v1/${path}`, {
    headers: { ...sbHeaders(key), 'Prefer': '' },
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) return [];
  return res.json().catch(() => []);
}

// Check dedup — returns true if this notification was recently sent
async function isDuplicate(sbUrl, sbKey, approvalId, status) {
  const hash = dedupHash(approvalId, status);
  const cutoff = new Date(Date.now() - 5 * 60 * 1000).toISOString(); // 5-minute window
  const rows = await sbGet(
    sbUrl, sbKey,
    `hermes_aggregates?event_source=eq.nexus_os_approval&classification=eq.${hash}&created_at=gt.${cutoff}&select=id&limit=1`,
  );
  return Array.isArray(rows) && rows.length > 0;
}

// Record send for dedup tracking
async function recordDedup(sbUrl, sbKey, approvalId, status, summary) {
  const hash = dedupHash(approvalId, status);
  await sbPost(sbUrl, sbKey, 'hermes_aggregates', {
    event_source: 'nexus_os_approval',
    event_type: `approval_${status}`,
    classification: hash,
    aggregated_summary: summary.slice(0, 500),
    alert_sent: true,
  });
}

// Telegram sendMessage
async function sendTelegram(token, chatId, text) {
  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text: text.slice(0, 4096),
      parse_mode: 'HTML',
    }),
    signal: AbortSignal.timeout(10000),
  });
  if (!res.ok) {
    // Fallback: try without parse_mode (in case of HTML entity issue)
    const fb = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text: text.slice(0, 4096) }),
      signal: AbortSignal.timeout(10000),
    });
    return fb.ok;
  }
  return true;
}

// Format Telegram message
function formatTelegramMessage(item) {
  const {
    approval_id, action_type, description, priority, status,
    requested_by, risk, review_notes, created_at,
  } = item;

  const dashboardUrl = process.env.NEXUS_DASHBOARD_URL || '';
  const deepLink = dashboardUrl ? `${dashboardUrl}/app/nexus-os` : '';

  const statusEmoji = {
    pending:      '⏳',
    approved:     '✅',
    rejected:     '❌',
    needs_edits:  '📝',
  }[status] || '📋';

  const priorityEmoji = {
    urgent:   '🔴',
    critical: '🔴',
    normal:   '🟡',
    low:      '🟢',
  }[priority] || '⚪';

  const riskLabel = {
    critical: '🚨 CRITICAL',
    high:     '⚠️ HIGH',
    medium:   '🔸 MEDIUM',
    low:      '🟢 LOW',
  }[risk] || '—';

  const shortId = (approval_id || '').slice(0, 8);

  let msg = `${statusEmoji} <b>Approval ${status.toUpperCase()}</b>\n`;
  msg += `${priorityEmoji} Priority: ${priority} | Risk: ${riskLabel}\n`;
  msg += `\n<b>Action:</b> ${escapeHtml(action_type)}`;
  msg += `\n<b>Description:</b> ${escapeHtml(description)}`;
  if (requested_by) msg += `\n<b>Requested by:</b> ${escapeHtml(requested_by)}`;
  if (review_notes) msg += `\n<b>Review note:</b> ${escapeHtml(review_notes)}`;
  msg += `\n<b>ID:</b> <code>${shortId}</code>`;

  if (status === 'pending') {
    msg += `\n\n📋 <i>Action required in Nexus OS.</i>`;
    if (deepLink) msg += `\n👉 <a href="${deepLink}">Open Approval Center</a>`;
    msg += `\n\nReply with:\n• /approve ${shortId} — to approve\n• /reject ${shortId} — to reject`;
  } else {
    msg += `\n\n<i>Status updated. No further action needed.</i>`;
    if (deepLink) msg += `\n👉 <a href="${deepLink}">View in Nexus OS</a>`;
  }

  return msg;
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Main handler ───────────────────────────────────────────────────────────────

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers: CORS, body: '' };
  }

  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers: { ...CORS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Method not allowed' }),
    };
  }

  // ── Parse body ──────────────────────────────────────────────────────────────
  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return {
      statusCode: 400,
      headers: { ...CORS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Invalid JSON' }),
    };
  }

  const {
    approval_id,
    action_type,
    description,
    priority = 'normal',
    status,
    requested_by,
    review_notes,
    user_id,       // Supabase user_id for notifications table
  } = body;

  if (!approval_id || !status || !action_type) {
    return {
      statusCode: 400,
      headers: { ...CORS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'approval_id, status, and action_type are required' }),
    };
  }

  // VITE_SUPABASE_URL is available in Netlify function runtime even without SUPABASE_URL
  const sbUrl = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '';
  const sbKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY || process.env.VITE_SUPABASE_ANON_KEY || '';
  const tgToken = process.env.TELEGRAM_BOT_TOKEN || '';
  const tgChat  = process.env.TELEGRAM_CHAT_ID || '';

  const risk = riskLevel(action_type);
  const result = {
    approval_id,
    status,
    notification_created: false,
    telegram_sent: false,
    telegram_skipped_reason: '',
    dedup_hit: false,
    event_logged: false,
  };

  // ── Dedup check ─────────────────────────────────────────────────────────────
  let isDup = false;
  if (sbUrl && sbKey) {
    isDup = await isDuplicate(sbUrl, sbKey, approval_id, status);
    if (isDup) {
      result.dedup_hit = true;
      // Still write a notification if user_id provided (idempotent UI state)
    }
  }

  // ── Write Supabase notification ─────────────────────────────────────────────
  if (sbUrl && sbKey && user_id) {
    const notifType = status === 'pending' ? 'action' : 'system';
    const notifPriority = priority === 'urgent' ? 3 : priority === 'normal' ? 2 : 1;
    const notifTitle =
      status === 'pending'
        ? `Approval needed: ${action_type}`
        : `Approval ${status}: ${action_type}`;

    const created = await sbPost(sbUrl, sbKey, 'notifications', {
      user_id,
      type: notifType,
      title: notifTitle,
      body: description || null,
      action_url: '/app/nexus-os',
      action_label: 'Open Nexus OS',
      priority: notifPriority,
    });
    result.notification_created = created;
  }

  // ── Log approval history event ───────────────────────────────────────────────
  if (sbUrl && sbKey && !isDup) {
    const logged = await sbPost(sbUrl, sbKey, 'nexus_os_approval_events', {
      approval_id,
      event_type: status === 'pending' ? 'created' : status,
      changed_by: requested_by || 'system',
      comment: review_notes || null,
      telegram_sent: false,
    });
    result.event_logged = logged;
  }

  // ── Telegram send ────────────────────────────────────────────────────────────
  if (!tgToken || !tgChat) {
    result.telegram_skipped_reason = 'TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured';
  } else if (isDup && status !== 'pending') {
    result.telegram_skipped_reason = 'dedup: same approval+status sent within 5 minutes';
  } else if (!telegramAllowed(priority)) {
    result.telegram_skipped_reason =
      priority === 'low'
        ? 'low priority: Telegram suppressed by policy'
        : 'TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED=false';
  } else {
    const msg = formatTelegramMessage({
      approval_id, action_type, description, priority, status,
      requested_by, risk, review_notes,
    });
    try {
      const sent = await sendTelegram(tgToken, tgChat, msg);
      result.telegram_sent = sent;
      if (sent && sbUrl && sbKey) {
        await recordDedup(sbUrl, sbKey, approval_id, status, `${action_type}: ${description}`);
        // Update event record with telegram_sent=true
        if (result.event_logged) {
          await sbPost(sbUrl, sbKey, 'nexus_os_approval_events', {
            approval_id,
            event_type: 'notified',
            changed_by: 'telegram_gate',
            comment: 'Telegram notification sent',
            telegram_sent: true,
          });
        }
      }
      if (!sent) {
        result.telegram_skipped_reason = 'Telegram API returned error';
      }
    } catch (err) {
      result.telegram_skipped_reason = `Telegram error: ${String(err)}`;
    }
  }

  return {
    statusCode: 200,
    headers: { ...CORS, 'Content-Type': 'application/json' },
    body: JSON.stringify(result),
  };
};
