import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// Suprimir erros específicos do axios no dev mode
if (process.env.NODE_ENV === 'development') {
  const originalError = console.error;
  console.error = (...args) => {
    // Ignorar erros de CORS e status 403/401 que são tratados pelo app
    if (
      args[0]?.includes?.('Script error') ||
      args[0]?.includes?.('Network Error') ||
      args[0]?.includes?.('403') ||
      args[0]?.includes?.('401')
    ) {
      return;
    }
    originalError.apply(console, args);
  };
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Registrar Service Worker para PWA (necessário para instalabilidade em dev e produção)
if ('serviceWorker' in navigator) {
  window.__PWA_UPDATE_ACCEPTED__ = false;

  // Recarrega a página apenas quando o usuário aceitou a atualização (evita reload no 1º install)
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (window.__PWA_UPDATE_ACCEPTED__) {
      window.location.reload();
    }
  });

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/service-worker.js')
      .then((registration) => {
        // Se já existe uma versão aguardando, avisa imediatamente
        if (registration.waiting && navigator.serviceWorker.controller) {
          window.dispatchEvent(new CustomEvent('pwa-update-available', { detail: registration }));
        }

        // Detecta novas versões instaladas em background
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (!newWorker) return;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              window.dispatchEvent(new CustomEvent('pwa-update-available', { detail: registration }));
            }
          });
        });

        // Verifica atualizações periodicamente (a cada 1h)
        setInterval(() => {
          registration.update().catch(() => {});
        }, 60 * 60 * 1000);
      })
      .catch((error) => {
        console.log('Falha ao registrar Service Worker:', error);
      });
  });
}
