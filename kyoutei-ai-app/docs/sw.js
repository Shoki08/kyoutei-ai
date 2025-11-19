const CACHE_NAME = 'kyotei-pwa-v1';
const STATIC_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './icons/icon-192.png'
];

self.addEventListener('install', (evt) => {
    evt.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)));
});

self.addEventListener('fetch', (evt) => {
    const url = new URL(evt.request.url);
    // JSONデータはネットワーク優先
    if (url.pathname.endsWith('.json')) {
        evt.respondWith(
            fetch(evt.request).catch(() => caches.match(evt.request))
        );
        return;
    }
    // その他（HTML/CSS）はキャッシュ優先
    evt.respondWith(
        caches.match(evt.request).then(cacheRes => {
            return cacheRes || fetch(evt.request);
        })
    );
});