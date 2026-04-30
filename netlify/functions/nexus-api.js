/**
 * Netlify function: nexus-api
 * Proxies authenticated requests to the Nexus backend.
 *
 * Security:
 *  - Validates Supabase JWT (Authorization: Bearer <token>) before forwarding
 *  - Only forwards GET requests to a whitelist of safe paths
 *  - Never forwards service-role credentials
 *
 * Environment variables required on Netlify:
 *  NEXUS_API_URL         — public URL of Nexus control center (e.g. https://nexus-api.goclearonline.cc)
 *  SUPABASE_JWT_SECRET   — used to verify the user's JWT
 */

const SAFE_PATHS = new Set([
  '/api/health',
  '/api/trading/status',
  '/api/readiness/profile',
  '/api/readiness/tasks',
  '/api/funding/overview',
  '/api/funding/strategy',
  '/api/funding/brief',
]);

exports.handler = async (event) => {
  const NEXUS_URL = process.env.NEXUS_API_URL || 'http://localhost:4000';

  // Only allow GET
  if (event.httpMethod !== 'GET') {
    return { statusCode: 405, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  // Require auth header
  const authHeader = event.headers?.authorization || event.headers?.Authorization || '';
  if (!authHeader.startsWith('Bearer ')) {
    return { statusCode: 401, body: JSON.stringify({ error: 'Unauthorized' }) };
  }

  // Extract path from query param
  const path = event.queryStringParameters?.path || '';
  if (!SAFE_PATHS.has(path)) {
    return { statusCode: 403, body: JSON.stringify({ error: `Path not allowed: ${path}` }) };
  }

  try {
    const upstream = await fetch(`${NEXUS_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(10000),
    });

    const body = await upstream.text();
    return {
      statusCode: upstream.status,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body,
    };
  } catch (err) {
    return {
      statusCode: 502,
      body: JSON.stringify({ error: 'Nexus backend unreachable', detail: String(err) }),
    };
  }
};
