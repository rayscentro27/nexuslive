// Nexus PWA Service Worker
// Safe caching: static shell only.
// NEVER cached: Supabase, auth endpoints, Stripe, API routes, Netlify functions.

const CACHE_VERSION = 'nexus-v1';

const NEVER_CACHE = [
  'supabase.co',
  'supabase.io',
  'stripe.com',
  'netlify/functions',
  '/.netlify/',
  '/api/',
  '/auth/',
];

function shouldSkipCache(url) {
  return NEVER_CACHE.some(pattern => url.includes(pattern));
}

// Install: cache the app shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(cache =>
      cache.addAll([
        '/',
        '/manifest.json',
        '/icons/icon-192.png',
        '/icons/icon-512.png',
        '/icons/apple-touch-icon.png',
      ])
    ).then(() => self.skipWaiting())
  );
});

// Activate: purge old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch strategy:
// - Auth/API/Supabase/Stripe → network only, no caching
// - HTML navigation → network first, fall back to cached /
// - Static assets (JS/CSS/fonts/images) → stale-while-revalidate
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = request.url;

  // Skip non-GET and non-http(s) requests
  if (request.method !== 'GET' || !url.startsWith('http')) return;

  // Never cache sensitive endpoints
  if (shouldSkipCache(url)) {
    event.respondWith(fetch(request));
    return;
  }

  const isNavigation = request.mode === 'navigate';

  if (isNavigation) {
    // Network first for HTML — fall back to cached root for offline SPA support
    event.respondWith(
      fetch(request).catch(() =>
        caches.match('/').then(r => r || new Response('Offline', { status: 503 }))
      )
    );
    return;
  }

  // Stale-while-revalidate for static assets
  event.respondWith(
    caches.open(CACHE_VERSION).then(cache =>
      cache.match(request).then(cached => {
        const networkFetch = fetch(request).then(response => {
          if (response && response.status === 200 && response.type !== 'opaque') {
            cache.put(request, response.clone());
          }
          return response;
        }).catch(() => cached);
        return cached || networkFetch;
      })
    )
  );
});
