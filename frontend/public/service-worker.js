// Service Worker para GestorCred PWA
const CACHE_NAME = 'gestorcred-v1.0.0';
const urlsToCache = [
  '/',
  '/manifest.json'
];

// Instalar service worker e fazer cache dos recursos básicos de forma resiliente
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        // Cachear cada recurso individualmente para evitar falhas gerais se um link falhar (ex: 404 ou rede)
        return Promise.all(
          urlsToCache.map((url) => {
            return cache.add(url).catch((err) => {
              // Silencia erros de itens específicos para não quebrar a instalação
            });
          })
        );
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
