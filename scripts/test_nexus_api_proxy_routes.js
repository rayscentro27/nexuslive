#!/usr/bin/env node
/**
 * Dry-run test: Netlify proxy SAFE_ROUTES matching logic.
 *
 * Simulates the route matching and method checks WITHOUT:
 *   - starting a server
 *   - making network calls
 *   - hitting any backend
 *
 * Run: node scripts/test_nexus_api_proxy_routes.js
 */

// Copy of the SAFE_ROUTES + matchRoute from nexus-api.js
const SAFE_ROUTES = [
  { pattern: '/api/health',                            methods: ['GET'] },
  { pattern: '/api/trading/status',                    methods: ['GET'] },
  { pattern: '/api/readiness/profile',                 methods: ['GET'] },
  { pattern: '/api/readiness/tasks',                   methods: ['GET'] },
  { pattern: '/api/funding/overview',                  methods: ['GET'] },
  { pattern: '/api/funding/strategy',                  methods: ['GET'] },
  { pattern: '/api/funding/brief',                     methods: ['GET'] },

  { pattern: '/api/showroom/packages',                 methods: ['GET'] },
  { pattern: '/api/showroom/assets',                   methods: ['GET'] },

  { pattern: /^\/api\/showroom\/packages\/[\w-]+$/,    methods: ['GET'] },
  { pattern: /^\/api\/showroom\/packages\/[\w-]+\/status$/, methods: ['PUT'] },
  { pattern: /^\/api\/showroom\/assets\/[\w-]+$/,      methods: ['GET'] },
  { pattern: /^\/api\/showroom\/assets\/[\w-]+\/review$/, methods: ['POST'] },
];

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

function test(label, path, method, expectedAllowed) {
  const matched = matchRoute(path);
  const allowed = matched ? matched.methods.includes(method) : false;
  const ok = allowed === expectedAllowed;
  const status = allowed ? (expectedAllowed ? '✓' : '✗ FAIL') : (expectedAllowed ? '✗ FAIL' : '✓');
  console.log(`  ${status} ${label.padEnd(65)} ${ok ? '' : `(expected ${expectedAllowed ? 'ALLOW' : 'DENY'}, got ${allowed ? 'ALLOW' : 'DENY'})`}`);
  return ok;
}

let passed = 0;
let failed = 0;

function check(label, path, method, expected) {
  if (test(label, path, method, expected)) passed++; else failed++;
}

console.log('\n─── Existing GET routes should still work ───\n');
check('GET /api/health',                         '/api/health', 'GET', true);
check('GET /api/trading/status',                   '/api/trading/status', 'GET', true);
check('GET /api/readiness/profile',                '/api/readiness/profile', 'GET', true);
check('GET /api/readiness/tasks',                  '/api/readiness/tasks', 'GET', true);
check('GET /api/funding/overview',                 '/api/funding/overview', 'GET', true);
check('GET /api/funding/strategy',                 '/api/funding/strategy', 'GET', true);
check('GET /api/funding/brief',                    '/api/funding/brief', 'GET', true);

console.log('\n─── Showroom static read paths (GET) ───\n');
check('GET /api/showroom/packages',                '/api/showroom/packages', 'GET', true);
check('GET /api/showroom/assets',                  '/api/showroom/assets', 'GET', true);

console.log('\n─── Showroom dynamic paths (GET) ───\n');
check('GET /api/showroom/packages/monetization_pack_v2',  '/api/showroom/packages/monetization_pack_v2', 'GET', true);
check('GET /api/showroom/packages/youtube_short',         '/api/showroom/packages/youtube_short', 'GET', true);
check('GET /api/showroom/assets/asset_15c19f49',          '/api/showroom/assets/asset_15c19f49', 'GET', true);
check('GET /api/showroom/assets/asset_0b594c89',          '/api/showroom/assets/asset_0b594c89', 'GET', true);

console.log('\n─── Showroom POST review ───\n');
check('POST /api/showroom/assets/asset_15c19f49/review',  '/api/showroom/assets/asset_15c19f49/review', 'POST', true);
check('POST /api/showroom/assets/asset_0b594c89/review',  '/api/showroom/assets/asset_0b594c89/review', 'POST', true);

console.log('\n─── Showroom PUT package status ───\n');
check('PUT /api/showroom/packages/monetization_pack_v2/status',   '/api/showroom/packages/monetization_pack_v2/status', 'PUT', true);
check('PUT /api/showroom/packages/youtube_short/status',          '/api/showroom/packages/youtube_short/status', 'PUT', true);

console.log('\n─── Showroom paths with WRONG methods (should DENY) ───\n');
check('POST /api/showroom/packages (no POST)',       '/api/showroom/packages', 'POST', false);
check('PUT /api/showroom/packages (no PUT)',          '/api/showroom/packages', 'PUT', false);
check('DELETE /api/showroom/packages (no DELETE)',    '/api/showroom/packages', 'DELETE', false);
check('POST /api/showroom/assets (no POST)',          '/api/showroom/assets', 'POST', false);
check('PUT /api/showroom/assets (no PUT)',            '/api/showroom/assets', 'PUT', false);
check('DELETE /api/showroom/assets (no DELETE)',      '/api/showroom/assets', 'DELETE', false);
check('PUT /api/showroom/assets/foo (no PUT)',        '/api/showroom/assets/asset_1', 'PUT', false);
check('DELETE /api/showroom/assets/foo (no DELETE)',  '/api/showroom/assets/asset_1', 'DELETE', false);
check('POST /api/showroom/packages/monetization_pack_v2 (no POST)',
  '/api/showroom/packages/monetization_pack_v2', 'POST', false);
check('DELETE /api/showroom/packages/monetization_pack_v2 (no DELETE)',
  '/api/showroom/packages/monetization_pack_v2', 'DELETE', false);
check('PATCH /api/showroom/packages/monetization_pack_v2 (no PATCH)',
  '/api/showroom/packages/monetization_pack_v2', 'PATCH', false);
check('PUT /api/showroom/packages (no PUT)',
  '/api/showroom/packages', 'PUT', false);
check('PUT /api/showroom/packages/id (no PUT — use /status)',
  '/api/showroom/packages/monetization_pack_v2', 'PUT', false);

console.log('\n─── Arbitrary /api/* paths (should DENY) ───\n');
check('GET /api/admin/users',                      '/api/admin/users', 'GET', false);
check('POST /api/admin/users',                     '/api/admin/users', 'POST', false);
check('GET /api/trading/orders',                   '/api/trading/orders', 'GET', false);
check('GET /api/anything/unsafe',                  '/api/anything/unsafe', 'GET', false);
check('POST /api/anything/unsafe',                 '/api/anything/unsafe', 'POST', false);

console.log('\n─── Path traversal / injection (should DENY) ───\n');
check('GET /api/showroom/packages/../admin/users',
  '/api/showroom/packages/../admin/users', 'GET', false);
check('GET /api/showroom/packages/..%2Fadmin',
  '/api/showroom/packages/..%2Fadmin', 'GET', false);
check('POST with path traversal',
  '/api/showroom/assets/../admin/evil/review', 'POST', false);

console.log('\n─── Existing paths with wrong methods (should DENY) ───\n');
check('POST /api/health (no POST)',                '/api/health', 'POST', false);
check('PUT /api/health (no PUT)',                   '/api/health', 'PUT', false);
check('DELETE /api/health (no DELETE)',             '/api/health', 'DELETE', false);
check('PATCH /api/trading/status (no PATCH)',       '/api/trading/status', 'PATCH', false);

console.log('\n─── Unusual / edge cases ───\n');
check('Empty path', '', 'GET', false);
check('Non-API path', '/something-else', 'GET', false);
check('Nested showroom (GET /api/showroom/packages/x/y)',
  '/api/showroom/packages/a/b', 'GET', false);
check('Nested showroom (GET /api/showroom/assets/x/y)',
  '/api/showroom/assets/a/b', 'GET', false);
check('Malformed asset review (GET not POST)',
  '/api/showroom/assets/foo/review', 'GET', false);
check('Deep nested review',
  '/api/showroom/assets/foo/review/extra', 'POST', false);
check('PUT on showroom assets/<id> (should be GET only)',
  '/api/showroom/assets/asset_1', 'PUT', false);
check('POST on showroom packages/<id>/status (should be PUT only)',
  '/api/showroom/packages/x/status', 'POST', false);

console.log('\n─── Results ───');
console.log(`  Passed: ${passed}`);
console.log(`  Failed: ${failed}`);
if (failed === 0) {
  console.log('\n  ✓ ALL TESTS PASSED\n');
  process.exit(0);
} else {
  console.log(`\n  ✗ ${failed} TEST(S) FAILED\n`);
  process.exit(1);
}
