/**
 * Netlify function: hermes-chat
 *
 * The Nexus OS Hermes Chat UI calls this endpoint. Before it existed the path
 * 404'd, which the UI surfaced as "Hermes offline / function unreachable".
 *
 * Behaviour:
 *  - GET  → health probe. Returns a structured { status, reason, detail } the UI
 *           already knows how to render. Never 404s.
 *  - POST → if the live Hermes gateway is configured, proxy the chat request to it.
 *           If it is NOT configured (or unreachable), return HTTP 200 with a useful
 *           OFFLINE FALLBACK briefing (approvals / social queue / connectors / next
 *           actions / trading) built from a bundled, non-secret snapshot — clearly
 *           flagged as a snapshot, not a live reply.
 *
 * Environment variables (optional, set on Netlify to enable live AI):
 *   HERMES_GATEWAY_URL  — base URL of the Hermes gateway (via Cloudflare tunnel)
 *   HERMES_API_KEY      — bearer key the gateway expects
 *
 * No secrets are ever returned to the client.
 */

let SNAPSHOT = {};
try {
  // Bundled at build time by scripts/build_hermes_fallback_snapshot.py
  SNAPSHOT = require('./hermes-fallback-snapshot.json');
} catch {
  SNAPSHOT = {};
}

const JSON_HEADERS = {
  'Content-Type': 'application/json',
  'Access-Control-Allow-Origin': '*',
};

function gatewayConfig() {
  const url = process.env.HERMES_GATEWAY_URL || '';
  const key = process.env.HERMES_API_KEY || '';
  return { url: url.replace(/\/+$/, ''), key };
}

// ── Offline fallback briefing (real snapshot data, plainly labelled) ──────────
function fallbackBriefing(reasonDetail) {
  const s = SNAPSHOT || {};
  const q = s.social_queue || {};
  const fb = (s.connectors && s.connectors.facebook) || {};
  const ig = (s.connectors && s.connectors.instagram) || {};
  const lines = [];
  lines.push('⚠️ Hermes live AI is offline, so this is a **system snapshot**, not a live reply.');
  if (reasonDetail) lines.push(`(${reasonDetail})`);
  if (s.generated_at) lines.push(`Snapshot taken: ${s.generated_at}`);
  lines.push('');
  lines.push(`Overall status: ${s.overall_status ?? 'unknown'}`);
  lines.push('');
  lines.push('Social queue:');
  lines.push(`• Published: ${q.published ?? '—'}  ·  Queued for review: ${q.queued_for_review ?? '—'}  ·  Approved: ${q.approved ?? '—'}  ·  Dry-run ready: ${q.dry_run_ready ?? '—'}  ·  Failed: ${q.failed ?? '—'}`);
  lines.push('');
  lines.push('Connectors:');
  lines.push(`• Facebook — connected: ${fb.account_connected ?? '?'}, publishing ready: ${fb.publishing_ready ?? '?'}`);
  lines.push(`• Instagram — connected: ${ig.account_connected ?? '?'}, publishing ready: ${ig.publishing_ready ?? '?'} (needs hosted media for real publish)`);
  lines.push('');
  if (s.approvals_pending != null) lines.push(`Pending your approval: ${s.approvals_pending} item(s).`);
  if (s.next_social_action) lines.push(`Next social action: ${s.next_social_action}`);
  if (Array.isArray(s.next_actions) && s.next_actions.length) {
    lines.push('');
    lines.push('Top next actions:');
    s.next_actions.slice(0, 3).forEach((a) => {
      const t = typeof a === 'string' ? a : (a.action || a.title || JSON.stringify(a));
      lines.push(`• ${t}`);
    });
  }
  if (Array.isArray(s.blockers) && s.blockers.length) {
    lines.push('');
    lines.push('Open blockers:');
    s.blockers.slice(0, 4).forEach((b) => lines.push(`• [${b.area ?? '—'}] ${b.blocker ?? ''}${b.fix ? ` → fix: ${b.fix}` : ''}`));
  }
  lines.push('');
  lines.push('Trading: paper/demo only — no live or funded trading.');
  lines.push('');
  lines.push('To get live Hermes back, the local gateway + Cloudflare tunnel must be up and HERMES_GATEWAY_URL / HERMES_API_KEY set on Netlify.');
  return lines.join('\n');
}

// Shape the fallback like an OpenAI chat completion so the UI renders it as a message.
function fallbackResponse(reason, detail) {
  return {
    statusCode: 200,
    headers: JSON_HEADERS,
    body: JSON.stringify({
      fallback: true,
      live: false,
      reason,
      detail,
      choices: [{ message: { role: 'assistant', content: fallbackBriefing(detail) } }],
    }),
  };
}

async function handleHealth() {
  const { url, key } = gatewayConfig();
  if (!url) {
    return { statusCode: 200, headers: JSON_HEADERS, body: JSON.stringify({ status: 'offline', reason: 'netlify_env_missing', detail: 'HERMES_GATEWAY_URL is not set on Netlify.' }) };
  }
  if (!key) {
    return { statusCode: 200, headers: JSON_HEADERS, body: JSON.stringify({ status: 'offline', reason: 'auth_key_missing', detail: 'HERMES_API_KEY is not set on Netlify.' }) };
  }
  try {
    const res = await fetch(`${url}/health`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${key}` },
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      return { statusCode: 200, headers: JSON_HEADERS, body: JSON.stringify({ status: 'live', reason: 'ok', detail: 'Hermes gateway live.' }) };
    }
    return { statusCode: 200, headers: JSON_HEADERS, body: JSON.stringify({ status: 'degraded', reason: 'origin_unhealthy', detail: `Gateway responded ${res.status}.` }) };
  } catch (err) {
    const timeout = String(err).toLowerCase().includes('timeout') || String(err).toLowerCase().includes('abort');
    return { statusCode: 200, headers: JSON_HEADERS, body: JSON.stringify({ status: 'offline', reason: timeout ? 'tunnel_timeout' : 'tunnel_unreachable', detail: timeout ? 'Tunnel/origin timed out.' : 'Tunnel or local Hermes offline.' }) };
  }
}

async function handleChat(event) {
  const { url, key } = gatewayConfig();
  if (!url) return fallbackResponse('netlify_env_missing', 'HERMES_GATEWAY_URL is not set on Netlify.');
  if (!key) return fallbackResponse('auth_key_missing', 'HERMES_API_KEY is not set on Netlify.');

  let payload;
  try {
    payload = JSON.parse(event.body || '{}');
  } catch {
    return { statusCode: 400, headers: JSON_HEADERS, body: JSON.stringify({ error: 'invalid JSON body' }) };
  }

  try {
    const res = await fetch(`${url}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${key}` },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(45000),
    });
    const text = await res.text();
    if (!res.ok) {
      // Live gateway reachable but errored → still give Ray something useful.
      if (res.status === 401 || res.status === 403) return fallbackResponse('auth_failed', 'Gateway rejected the API key.');
      if (res.status === 504) return { statusCode: 504, headers: JSON_HEADERS, body: JSON.stringify({ reason: 'model_timeout', detail: 'Hermes origin timed out.' }) };
      return fallbackResponse('origin_unhealthy', `Gateway responded ${res.status}.`);
    }
    return { statusCode: 200, headers: JSON_HEADERS, body: text };
  } catch (err) {
    const timeout = String(err).toLowerCase().includes('timeout') || String(err).toLowerCase().includes('abort');
    return fallbackResponse(timeout ? 'tunnel_timeout' : 'tunnel_unreachable', timeout ? 'Tunnel/origin timed out.' : 'Hermes origin/tunnel is unreachable.');
  }
}

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: { ...JSON_HEADERS, 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' }, body: '' };
  }
  if (event.httpMethod === 'GET') return handleHealth();
  if (event.httpMethod === 'POST') return handleChat(event);
  return { statusCode: 405, headers: JSON_HEADERS, body: JSON.stringify({ error: 'Method not allowed' }) };
};
