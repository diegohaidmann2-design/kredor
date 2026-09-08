import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Download, RefreshCw, X, Sparkles, Share, Plus } from 'lucide-react';

// Quanto tempo esconder o banner de instalação após o usuário dispensar (7 dias)
const DISMISS_DURATION_MS = 7 * 24 * 60 * 60 * 1000;
const DISMISS_KEY = 'pwa_install_dismissed_until';
const IOS_DISMISS_KEY = 'pwa_ios_dismissed_until';

function isStandalone() {
  return (
    window.matchMedia?.('(display-mode: standalone)')?.matches ||
    window.navigator.standalone === true
  );
}

function isIOS() {
  const ua = window.navigator.userAgent || '';
  const iOSDevice = /iphone|ipad|ipod/i.test(ua);
  const iPadOS = window.navigator.platform === 'MacIntel' && window.navigator.maxTouchPoints > 1;
  return iOSDevice || iPadOS;
}

export default function PWAManager() {
  const [installEvent, setInstallEvent] = useState(null);
  const [showInstall, setShowInstall] = useState(false);
  const [updateReg, setUpdateReg] = useState(null);
  const [showUpdate, setShowUpdate] = useState(false);
  const [showIOS, setShowIOS] = useState(false);

  // ---------- Banner de Instalação ----------
  useEffect(() => {
    if (isStandalone()) return;

    const onBeforeInstall = (e) => {
      e.preventDefault();
      setInstallEvent(e);

      const dismissedUntil = Number(localStorage.getItem(DISMISS_KEY) || 0);
      if (Date.now() > dismissedUntil) {
        setShowInstall(true);
      }
    };

    const onInstalled = () => {
      setShowInstall(false);
      setInstallEvent(null);
      localStorage.removeItem(DISMISS_KEY);
    };

    window.addEventListener('beforeinstallprompt', onBeforeInstall);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (!installEvent) return;
    installEvent.prompt();
    try {
      await installEvent.userChoice;
    } catch (_) {}
    setShowInstall(false);
    setInstallEvent(null);
  };

  const dismissInstall = () => {
    setShowInstall(false);
    localStorage.setItem(DISMISS_KEY, String(Date.now() + DISMISS_DURATION_MS));
  };

  // ---------- Instruções para iPhone/iPad (Safari não tem beforeinstallprompt) ----------
  useEffect(() => {
    if (!isIOS() || isStandalone()) return;
    const dismissedUntil = Number(localStorage.getItem(IOS_DISMISS_KEY) || 0);
    if (Date.now() > dismissedUntil) {
      const t = setTimeout(() => setShowIOS(true), 1500);
      return () => clearTimeout(t);
    }
  }, []);

  const dismissIOS = () => {
    setShowIOS(false);
    localStorage.setItem(IOS_DISMISS_KEY, String(Date.now() + DISMISS_DURATION_MS));
  };

  // ---------- Aviso de Atualização ----------
  useEffect(() => {
    const onUpdate = (e) => {
      setUpdateReg(e.detail);
      setShowUpdate(true);
    };
    window.addEventListener('pwa-update-available', onUpdate);
    return () => window.removeEventListener('pwa-update-available', onUpdate);
  }, []);

  const handleUpdate = () => {
    const reg = updateReg;
    window.__PWA_UPDATE_ACCEPTED__ = true;
    const worker = reg?.waiting || reg?.installing;
    if (worker) {
      worker.postMessage({ type: 'SKIP_WAITING' });
    } else {
      window.location.reload();
    }
    setShowUpdate(false);
  };

  const dismissUpdate = () => setShowUpdate(false);

  return (
    <div className="fixed inset-x-0 bottom-0 z-[9999] flex flex-col items-center gap-3 p-4 pointer-events-none">
      <AnimatePresence>
        {/* Aviso de nova versão */}
        {showUpdate && (
          <motion.div
            key="pwa-update"
            initial={{ opacity: 0, y: 40, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 320, damping: 26 }}
            data-testid="pwa-update-banner"
            className="pointer-events-auto w-full max-w-md rounded-2xl border border-emerald-500/30 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-xl shadow-2xl shadow-emerald-900/20 px-4 py-3"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-500">
                <RefreshCw className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  Nova versão disponível
                </p>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate">
                  Atualize para obter as últimas melhorias.
                </p>
              </div>
              <button
                data-testid="pwa-update-button"
                onClick={handleUpdate}
                className="shrink-0 rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-600"
              >
                Atualizar
              </button>
              <button
                data-testid="pwa-update-dismiss"
                onClick={dismissUpdate}
                aria-label="Dispensar aviso de atualização"
                className="shrink-0 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}

        {/* Instruções de instalação para iPhone/iPad */}
        {showIOS && (
          <motion.div
            key="pwa-ios"
            initial={{ opacity: 0, y: 40, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 320, damping: 26 }}
            data-testid="pwa-ios-banner"
            className="pointer-events-auto w-full max-w-md rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-xl shadow-2xl shadow-black/10 px-4 py-4"
          >
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-500">
                <Sparkles className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  Instalar na Tela de Início
                </p>
                <p className="text-xs text-neutral-500 dark:text-neutral-400">
                  Use o GestorCred como app no seu iPhone em 3 passos:
                </p>
              </div>
              <button
                data-testid="pwa-ios-dismiss"
                onClick={dismissIOS}
                aria-label="Dispensar instruções do iPhone"
                className="shrink-0 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <ol className="mt-3 space-y-2">
              <li className="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-[11px] font-bold text-white">1</span>
                <span className="flex items-center gap-1">
                  Toque em <Share className="inline h-4 w-4 text-emerald-500" /> <strong>Compartilhar</strong>
                </span>
              </li>
              <li className="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-[11px] font-bold text-white">2</span>
                <span className="flex items-center gap-1">
                  Escolha <Plus className="inline h-4 w-4 text-emerald-500" /> <strong>Adicionar à Tela de Início</strong>
                </span>
              </li>
              <li className="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-[11px] font-bold text-white">3</span>
                <span>Toque em <strong>Adicionar</strong> no canto superior</span>
              </li>
            </ol>
          </motion.div>
        )}

        {/* Banner de instalação */}
        {showInstall && (
          <motion.div
            key="pwa-install"
            initial={{ opacity: 0, y: 40, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 320, damping: 26 }}
            data-testid="pwa-install-banner"
            className="pointer-events-auto w-full max-w-md rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-xl shadow-2xl shadow-black/10 px-4 py-3"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-500">
                <Sparkles className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  Instalar GestorCred
                </p>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate">
                  Acesso rápido, tela cheia e uso como app.
                </p>
              </div>
              <button
                data-testid="pwa-install-button"
                onClick={handleInstall}
                className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-600"
              >
                <Download className="h-4 w-4" />
                Instalar
              </button>
              <button
                data-testid="pwa-install-dismiss"
                onClick={dismissInstall}
                aria-label="Dispensar banner de instalação"
                className="shrink-0 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
