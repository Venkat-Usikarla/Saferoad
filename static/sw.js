// SafeRoad PWA Service Worker
const CACHE_NAME = 'saferoad-cache-v1';
const PRECACHE_ASSETS = [
  '/',
  '/routes',
  '/petitions',
  '/static/css/style.css',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Only cache GET requests, skip API and admin routes
  if (event.request.method !== 'GET' || event.request.url.includes('/api/') || event.request.url.includes('/admin/')) {
    return;
  }
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
