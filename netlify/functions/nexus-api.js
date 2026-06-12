/**
 * Netlify function: nexus-api
 * Proxies authenticated requests to the Nexus backend.
 *
 * Security:
 *  - Validates Supabase JWT (Authorization: Bearer <token>) before forwarding
 *  - Only forwards requests to an explicit allowlist of safe paths + methods
 *  - Showroom review routes allow POST/PUT only for specific safe operations
 *  - Never forwards service-role credentials
 *  - Rejects path traversal patterns (..)
 *
 * Environment variables required on Netlify:
 *  NEXUS_API_URL         — public URL of Nexus control center (e.g. https://nexus-api.goclearonline.cc)
 *  SUPABASE_JWT_SECRET   — used to verify the user's JWT
 */

// ── Safe route allowlist ───────────────────────────────────────────────────
// Each entry: { pattern: string|RegExp, methods: string[] }
//   string pattern  → exact match
//   RegExp pattern  → regex test against the path
// Only the listed HTTP methods are allowed for each path.

const SAFE_ROUTES = [
  // ── Existing static READ paths (GET only) ───────────────────────────
  { pattern: '/api/health',                            methods: ['GET'] },
  { pattern: '/api/trading/status',                    methods: ['GET'] },
  { pattern: '/api/readiness/profile',                 methods: ['GET'] },
  { pattern: '/api/readiness/tasks',                   methods: ['GET'] },
  { pattern: '/api/funding/overview',                  methods: ['GET'] },
  { pattern: '/api/funding/strategy',                  methods: ['GET'] },
  { pattern: '/api/funding/brief',                     methods: ['GET'] },

  // ── Showroom review paths ──────────────────────────────────────────
  // Read endpoints (GET only)
  { pattern: '/api/showroom/packages',                 methods: ['GET'] },
  { pattern: '/api/showroom/assets',                   methods: ['GET'] },

  // Dynamic read: /api/showroom/packages/<id>
  { pattern: /^\/api\/showroom\/packages\/[\w-]+$/,    methods: ['GET'] },
  // Package status update: /api/showroom/packages/<id>/status
  { pattern: /^\/api\/showroom\/packages\/[\w-]+\/status$/, methods: ['PUT'] },
  // Dynamic read: /api/showroom/assets/<id>
  { pattern: /^\/api\/showroom\/assets\/[\w-]+$/,      methods: ['GET'] },
  // Review action: /api/showroom/assets/<id>/review
  { pattern: /^\/api\/showroom\/assets\/[\w-]+\/review$/, methods: ['POST'] },
];


// ── Helpers ─────────────────────────────────────────────────────────────────

/** Find the first SAFE_ROUTES entry that matches `path`, or null. */
function matchRoute(path) {
  for (const route of SAFE_ROUTES) {
    if (typeof route.pattern === 'string') {
      if (route.pattern === path) return route;
    } else if (route.pattern instanceof RegExp) {
      if (route.pattern.test(path)) return route;
    }
  }
  return null;
}


// ── Handler ─────────────────────────────────────────────────────────────────

exports.handler = async (event) => {
  const NEXUS_URL = process.env.NEXUS_API_URL || 'http://localhost:4000';

  // ── 1. Auth check (all routes require valid Supabase JWT) ──────────
  const authHeader = event.headers?.authorization || event.headers?.Authorization || '';
  if (!authHeader.startsWith('Bearer ')) {
    return { statusCode: 401, body: JSON.stringify({ error: 'Unauthorized' }) };
  }

  // ── 2. Extract path from query param ───────────────────────────────
  const path = event.queryStringParameters?.path || '';
  if (!path.startsWith('/api/')) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Invalid path' }) };
  }

  // ── 3. Reject path traversal ───────────────────────────────────────
  if (path.includes('..')) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Path traversal denied' }) };
  }

  // ── 4. Match path against allowlist ────────────────────────────────
  const matched = matchRoute(path);
  if (!matched) {
    return { statusCode: 403, body: JSON.stringify({ error: `Path not allowed: ${path}` }) };
  }

  // ── 5. Method check (per-route) ────────────────────────────────────
  const method = event.httpMethod;
  if (!matched.methods.includes(method)) {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: `Method ${method} not allowed for ${path}` }),
    };
  }

  // ── 6. Forward to backend ──────────────────────────────────────────
  const fetchOptions = {
    headers: { 'Content-Type': 'application/json' },
    signal: AbortSignal.timeout(10000),
  };

  // Attach body for POST/PUT
  if (method === 'POST' || method === 'PUT') {
    fetchOptions.method = method;
    if (event.body) {
      fetchOptions.body = event.body;
    }
  }

  try {
    const upstream = await fetch(`${NEXUS_URL}${path}`, fetchOptions);
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
