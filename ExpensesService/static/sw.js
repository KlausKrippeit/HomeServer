const CACHE_NAME = 'expenses-static-v2';
const STATIC_ASSETS = [
  '/static/style.css',
  '/static/manifest.webmanifest',
  '/static/icon-180.png',
  '/static/icon-192.png',
  '/static/icon-512.png'
];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', event => {
  const request_url = new URL(event.request.url);
  if (event.request.method === 'GET' && request_url.origin === self.location.origin && request_url.pathname.startsWith('/static/')) {
    event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
  }
});
