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
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers: CORS_HEADERS, body: '' };
  }

  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers: CORS_HEADERS,
      body: JSON.stringify({ error: 'Method not allowed' }),
    };
  }

  const HERMES_URL = process.env.HERMES_GATEWAY_URL || '';
  const HERMES_KEY = process.env.HERMES_API_KEY || '';

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

  // Build OpenAI-compatible payload
  const payload = {
    model: model || 'meta-llama/llama-3.3-70b-instruct',
    messages: system
      ? [{ role: 'system', content: system }, ...messages]
      : messages,
    temperature: 0.7,
    max_tokens: 1024,
    stream: false,
  };

  try {
    const upstream = await fetch(`${HERMES_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(HERMES_KEY ? { Authorization: `Bearer ${HERMES_KEY}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(30000),
    });

    const responseText = await upstream.text();

    return {
      statusCode: upstream.status,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: responseText,
    };
  } catch (err) {
    const isTimeout = String(err).includes('TimeoutError') || String(err).includes('abort');
    return {
      statusCode: 503,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: isTimeout ? 'Hermes gateway timed out (30s)' : 'Hermes gateway unreachable',
        detail: String(err),
        setup: [
          '1. Start Hermes: launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist',
          '2. Set HERMES_GATEWAY_URL=http://localhost:8642 in .env',
          '3. Set HERMES_API_KEY=<key from ~/.hermes/config.yaml extra.key>',
        ],
      }),
    };
  }
};
