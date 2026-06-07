/**
 * Netlify function: hermes-chat
 * Proxies chat requests to the Hermes gateway (OpenAI-compatible API).
 *
 * Required env vars (set in Netlify dashboard or local .env):
 *   HERMES_GATEWAY_URL  — e.g. http://localhost:8642 (local) or https://your-tunnel.ngrok.io
 *   HERMES_API_KEY      — API key from ~/.hermes/config.yaml extra.key
 *
 * Security:
 *   - Only POST requests accepted
 *   - Body is validated for required fields
 *   - Never forwards Supabase/Stripe credentials
 *   - No credentials stored or logged
 */

// Compact Nexus production system prompt (~350 tokens) — preserves voice, evidence
// behavior, and safety without sending full SOUL.md/skills through Netlify.
const COMPACT_SYSTEM = [
  "You are Hermes, Ray's Nexus OS chief of staff — a sharp, warm, human operating partner, not a status terminal.",
  'Talk like a real person having a conversation. Plain language, contractions, a little warmth. Match the energy of the message.',
  'Do NOT use rigid headers like "VERIFIED:" / "BLOCKERS:" or bullet dumps unless Ray explicitly asks for a status report or audit.',
  'For casual or open questions, just talk naturally and helpfully — answer first, then offer a useful next thought if relevant.',
  'When Ray asks what to do or for a recommendation: give one clear recommendation in prose, the quick why, the blocker if any, and whether approval is needed. Keep it conversational.',
  'Evidence: when a "NEXUS OS EVIDENCE" block is present, treat it as VERIFIED and answer from it; never invent numbers. If something is not in evidence, say so plainly without sounding like an error log.',
  'Safety: no live trading, publishing, email/outreach, ad spend, deploys, or credential changes without explicit approval. No earnings/results guarantees.',
].join(' ');

// Conversational nudge for casual/general chat (no evidence needed).
const CONVERSATIONAL_HINT = 'This is normal conversation — respond naturally and warmly, like a helpful partner. Do not produce a status report or VERIFIED/BLOCKERS format. Keep it short and human.';

// Short skill summaries (5–8 bullets) loaded ONLY for the detected intent —
// full skill files stay local to Hermes; we never send them all per request.
const SKILL_SUMMARIES = {
  revenue: 'Revenue focus: rank campaigns by readiness-to-revenue (closest to launch, fewest blockers, highest priority). Name the single best campaign, its blocker, and the exact next action. Affiliate CTA needs disclosure before publish. Never claim projected/guaranteed earnings.',
  content: 'Content focus: find the highest-priority campaign with the least content, or the item closest to approval. Recommend specific drafts/platforms. Disclosure required for affiliate content. No earnings claims or guarantees.',
  approvals: 'Approval focus: report what is pending and what to act on first (urgent first). If nothing pending, say so plainly — do not invent items. Applying to programs needs no approval; publishing/outreach does.',
  next_step: 'Next-step focus: weigh revenue campaigns, content state, and pending approvals. Recommend the single highest-impact next move: prioritize speed to revenue, safety, and clearing blockers.',
  graph: 'Graph focus: use entity/relationship summaries to explain how sources, campaigns, content, and approvals connect. Summarize; never dump raw rows.',
  trading_status: 'Trading focus: report paper/demo status only. Live trading is locked. Never recommend live execution or credential changes.',
  tool_repo: 'Tool/repo focus: classify as core-now / later / personal / reference-only / ignore. Recommend adapt/fork/wrap/reference. Weigh Nexus fit, risk, cost, timing. No installs without approval.',
};

// Output-token budget per intent — generation time is the main latency lever.
const MAX_TOKENS_BY_INTENT = {
  general: 500, status: 500, approvals: 550, revenue: 700, content: 650,
  graph: 600, trading_status: 500, next_step: 700, tool_repo: 700, design: 600,
};

exports.handler = async (event) => {
  const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  };
  const JSON_HEADERS = { ...CORS_HEADERS, 'Content-Type': 'application/json' };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers: CORS_HEADERS, body: '' };
  }

  const HERMES_URL = process.env.HERMES_GATEWAY_URL || '';
  const HERMES_KEY = process.env.HERMES_API_KEY || '';

  // ── GET = fast health check (sub-second). Drives the UI status pill. ──
  // Returns an accurate, specific reason so the UI never shows a misleading
  // "set env vars" message when env is actually present.
  if (event.httpMethod === 'GET') {
    if (!HERMES_URL) {
      return { statusCode: 200, headers: JSON_HEADERS,
        body: JSON.stringify({ status: 'offline', reason: 'netlify_env_missing', detail: 'HERMES_GATEWAY_URL not set on Netlify.' }) };
    }
    if (!HERMES_KEY) {
      return { statusCode: 200, headers: JSON_HEADERS,
        body: JSON.stringify({ status: 'degraded', reason: 'auth_key_missing', detail: 'HERMES_API_KEY not set; chat will fail auth.' }) };
    }
    try {
      const r = await fetch(`${HERMES_URL}/health`, { signal: AbortSignal.timeout(6000) });
      if (r.ok) {
        return { statusCode: 200, headers: JSON_HEADERS,
          body: JSON.stringify({ status: 'live', reason: 'ok', detail: 'Hermes gateway reachable.' }) };
      }
      return { statusCode: 200, headers: JSON_HEADERS,
        body: JSON.stringify({ status: 'degraded', reason: 'origin_unhealthy', detail: `Gateway returned ${r.status}.` }) };
    } catch (err) {
      const isTimeout = String(err).includes('Timeout') || String(err).includes('abort');
      return { statusCode: 200, headers: JSON_HEADERS,
        body: JSON.stringify({
          status: 'offline',
          reason: isTimeout ? 'tunnel_timeout' : 'tunnel_unreachable',
          detail: isTimeout ? 'Tunnel/origin did not respond in time.' : 'Tunnel or local Hermes process is unreachable.',
        }) };
    }
  }

  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers: CORS_HEADERS,
      body: JSON.stringify({ error: 'Method not allowed' }),
    };
  }

  if (!HERMES_URL) {
    return {
      statusCode: 503,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Hermes gateway not configured',
        detail: 'Set HERMES_GATEWAY_URL env var to the gateway URL (e.g. http://localhost:8642)',
      }),
    };
  }

  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return {
      statusCode: 400,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'Invalid JSON body' }),
    };
  }

  const { messages, system, model, intent } = body;
  if (!messages || !Array.isArray(messages)) {
    return {
      statusCode: 400,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'messages array required' }),
    };
  }

  // ── Intent routing: compact prompt + only the relevant skill summary ──
  const norm = String(intent || 'general').toLowerCase();
  const skillSummary = SKILL_SUMMARIES[norm] || '';
  // Function owns the compact prompt; client may still override with `system`.
  // General/casual chat gets a conversational nudge; evidence intents get a skill focus.
  const modeAddon = skillSummary
    ? `\n\nFocus for this request: ${skillSummary}`
    : `\n\n${CONVERSATIONAL_HINT}`;
  const composedSystem = (system && system.length < 400 ? system : COMPACT_SYSTEM) + modeAddon;
  const maxTokens = Math.min(Number(body.max_tokens) || MAX_TOKENS_BY_INTENT[norm] || 600, 900);

  // Rough server-side context estimate (logged, no secrets).
  const approxContextChars = composedSystem.length + messages.reduce((n, m) => n + String(m.content || '').length, 0);
  console.log(`hermes-chat intent=${norm} approx_ctx_chars=${approxContextChars} max_tokens=${maxTokens}`);

  // Build OpenAI-compatible payload.
  // Hermes injects a large (~20K-token) system context per call, so keep our
  // generation budget tight to stay under Netlify's ~10s function timeout.
  const payload = {
    model: model || 'gpt-5.5',
    messages: [{ role: 'system', content: composedSystem }, ...messages],
    temperature: 0.6,
    max_tokens: maxTokens,
    stream: false,
  };

  // Non-secret metadata headers for the client (intent, budget, evidence flag).
  const META_HEADERS = {
    'X-Nexus-Intent': norm,
    'X-Nexus-Max-Tokens': String(maxTokens),
    'X-Nexus-Evidence-Used': String(messages.some(m => String(m.content || '').includes('NEXUS OS EVIDENCE'))),
  };

  try {
    // Cap our own wait at 24s; Netlify may cut sooner, in which case the browser
    // sees a 504 and the UI shows an accurate "origin timed out" message.
    const upstream = await fetch(`${HERMES_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(HERMES_KEY ? { Authorization: `Bearer ${HERMES_KEY}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(24000),
    });

    const responseText = await upstream.text();

    // Surface auth failures specifically so the UI can say "gateway auth failed".
    if (upstream.status === 401 || upstream.status === 403) {
      return { statusCode: 502, headers: JSON_HEADERS,
        body: JSON.stringify({ error: 'gateway_auth_failed', reason: 'auth_failed',
          detail: 'Hermes rejected the API key. Check HERMES_API_KEY matches the gateway api_server key.' }) };
    }

    return {
      statusCode: upstream.status,
      headers: { ...JSON_HEADERS, ...META_HEADERS },
      body: responseText,
    };
  } catch (err) {
    const isTimeout = String(err).includes('Timeout') || String(err).includes('abort');
    return {
      statusCode: 504,
      headers: JSON_HEADERS,
      body: JSON.stringify({
        error: isTimeout ? 'hermes_origin_timeout' : 'hermes_origin_unreachable',
        reason: isTimeout ? 'model_timeout' : 'tunnel_unreachable',
        detail: isTimeout
          ? 'Hermes origin timed out. It carries a large context (~20K tokens) so replies can be slow. Retry, or ask a shorter question.'
          : 'Hermes origin/tunnel is unreachable. The local Hermes process or Cloudflare tunnel may be down.',
      }),
    };
  }
};
