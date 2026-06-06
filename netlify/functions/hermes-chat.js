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

  const { messages, system, model } = body;
  if (!messages || !Array.isArray(messages)) {
    return {
      statusCode: 400,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'messages array required' }),
    };
  }

  // Build OpenAI-compatible payload.
  // Hermes injects a large (~20K-token) system context per call, so keep our
  // generation budget tight to stay under Netlify's ~10s function timeout.
  const payload = {
    model: model || 'gpt-5.5',
    messages: system
      ? [{ role: 'system', content: system }, ...messages]
      : messages,
    temperature: 0.6,
    max_tokens: Math.min(Number(body.max_tokens) || 640, 900),
    stream: false,
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
      headers: JSON_HEADERS,
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
