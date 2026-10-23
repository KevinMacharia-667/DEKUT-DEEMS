/**
 * Tukio Service Worker
 * Precaches app shell (including hashed Vite production chunks),
 * serves assets cache-first / stale-while-revalidate,
 * and handles network-first caching for API event queries with offline fallback.
 */

const CACHE_NAME = 'tukio-v1';

// Origin of the backend when it is not this site (set by pwa.js: /sw.js?api=https://...)
const API_ORIGIN = new URL(self.location.href).searchParams.get('api') || '';

const STATIC_PRECACHE = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
  '/favicon-32.png',
  '/apple-touch-icon.png',
  '/icon-192.png',
  '/icon-512.png',
];

// Install: Pre-cache app shell assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        return cache.addAll(STATIC_PRECACHE).catch((err) => {
          console.warn('[SW] Pre-cache warning:', err);
        });
      })
      .then(() => self.skipWaiting())
  );
});

// Activate: Clean up legacy caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => {
        return Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch handler
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Skip non-GET requests (e.g. POST / PUT / DELETE)
  if (request.method !== 'GET') {
    return;
  }

  // Skip browser extensions or cross-origin external URLs (e.g. wa.me)
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // In production the API lives on its own origin, passed in at registration (?api=)
  const isApiOrigin = API_ORIGIN !== '' && url.origin === API_ORIGIN;

  // Any other cross-origin request (fonts, share links): let the browser handle it
  if (url.origin !== self.location.origin && !isApiOrigin) {
    return;
  }

  // 1. API Calls: Network-first for public events, NO-CACHE for authenticated/personalized endpoints
  if (isApiOrigin || url.pathname.startsWith('/api') || url.port === '8000') {
    const isAuthRequest =
      request.headers.has('Authorization') ||
      url.pathname.includes('/recommendations') ||
      url.pathname.includes('/rsvps') ||
      url.pathname.includes('/users') ||
      url.pathname.includes('/auth') ||
      url.pathname.includes('/feedback') ||
      url.pathname.includes('/interactions');

    if (isAuthRequest) {
      // Authenticated/personalized data must never be cached in the service worker
      event.respondWith(fetch(request));
      return;
    }

    // Public event catalog queries: network-first with cache fallback
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, clone);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            return new Response(
              JSON.stringify({
                events: [],
                error: 'Offline',
                message: "You're currently offline. Please reconnect to load new events.",
              }),
              {
                headers: { 'Content-Type': 'application/json' },
                status: 503,
              }
            );
          });
        })
    );
    return;
  }

  // 2. Navigation Requests (HTML App Shell): Network-first with offline fallback to /index.html
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return networkResponse;
        })
        .catch(() => {
          return caches.match('/index.html').then((cachedHtml) => {
            return cachedHtml || caches.match('/');
          });
        })
    );
    return;
  }

  // 3. Static Assets & Hashed Bundles (/assets/*, icons, manifest): Cache-first with network fallback
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return networkResponse;
      });
    })
  );
});
