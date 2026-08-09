import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching';
import { clientsClaim } from 'workbox-core';
import { registerRoute } from 'workbox-routing';
import { NetworkFirst, CacheFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';

// --- FORZA AGGIORNAMENTO ---
self.skipWaiting();
clientsClaim();

// 1. Precache build (shell app)
cleanupOutdatedCaches();
precacheAndRoute(self.__WB_MANIFEST);

// 2. Navigazioni SPA: network-first con fallback cache (shell offline)
registerRoute(
  ({ request }) => request.mode === 'navigate',
  new NetworkFirst({
    cacheName: 'kor35-navigations',
    networkTimeoutSeconds: 4,
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 32, maxAgeSeconds: 7 * 24 * 60 * 60 }),
    ],
  })
);

// 3. Wiki API pubblica (A2): network-first — pagine già visitate restano leggibili offline
registerRoute(
  ({ url }) =>
    url.origin === self.location.origin &&
    (url.pathname.startsWith('/api/plot/api/wiki/') ||
      url.pathname.startsWith('/api/plot/api/public/wiki') ||
      url.pathname.startsWith('/api/plot/api/public/configurazione-sito')),
  new NetworkFirst({
    cacheName: 'kor35-wiki-api',
    networkTimeoutSeconds: 5,
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 80, maxAgeSeconds: 14 * 24 * 60 * 60 }),
    ],
  })
);

// 4. Immagini wiki / media: cache-first (rsync Edge)
registerRoute(
  ({ url, request }) =>
    url.origin === self.location.origin &&
    request.destination === 'image' &&
    (url.pathname.startsWith('/media/') ||
      url.pathname.startsWith('/api/plot/api/wiki/image/')),
  new CacheFirst({
    cacheName: 'kor35-wiki-media',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 120, maxAgeSeconds: 30 * 24 * 60 * 60 }),
    ],
  })
);

// 5. Asset statici residuali
registerRoute(
  ({ request }) =>
    request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'worker',
  new StaleWhileRevalidate({
    cacheName: 'kor35-static-runtime',
  })
);

// 6. Push notifications
self.addEventListener('push', function (event) {
  const eventData = event.data ? event.data.json() : {};

  const title = eventData.head || 'KOR-35';
  const options = {
    body: eventData.body || 'Nuovo messaggio ricevuto.',
    icon: '/pwa-192x192.png',
    badge: '/pwa-192x192.png',
    vibrate: [100, 50, 100],
    data: {
      url: eventData.url || '/',
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url));
});
