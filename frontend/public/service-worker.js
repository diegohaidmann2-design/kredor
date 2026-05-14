// Service Worker para GestorCred PWA
const CACHE_NAME = 'gestorcred-v1.0.0';
const urlsToCache = [
  '/',
  '/manifest.json'
];

// Instalar service worker e fazer cache dos recursos básicos
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        // Tentamos cachear recursos básicos, mas não deixamos falhar o SW se algum falhar
        return cache.addAll(urlsToCache).catch(err => {
          // Erro silencioso para não quebrar a instalação
        });
      })
  );
  // Forçar o service worker a se tornar ativo imediatamente
  self.skipWaiting();
});

// Ativar service worker e limpar caches antigos
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  // Assumir controle de todas as páginas imediatamente
  return self.clients.claim();
});

// Interceptar requisições e servir do cache quando possível
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Retornar do cache se existir, senão buscar da rede
        return response || fetch(event.request);
      })
  );
});
