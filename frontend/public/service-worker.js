// Service Worker para Kredor PWA
const CACHE_NAME = 'kredor-v1.0.0';
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
});

// Permitir que a página solicite a ativação imediata da nova versão (fluxo de atualização com 1 clique)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
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

// Interceptar requisições:
// - Navegações (HTML): network-first, com fallback para o cache (evita conteúdo obsoleto no dev/hot-reload)
// - Demais recursos: cache-first com fallback para a rede
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Não interferir em métodos não-GET nem em chamadas de API
  if (request.method !== 'GET' || request.url.includes('/api/')) {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(request).then((r) => r || caches.match('/')))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((response) => response || fetch(request))
  );
});
