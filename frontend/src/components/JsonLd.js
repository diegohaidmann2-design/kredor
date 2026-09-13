import { useEffect } from 'react';

/**
 * Injeta um bloco JSON-LD (schema.org) no <head>.
 * Cada bloco é identificado por `id` para evitar duplicação e é removido ao
 * desmontar. Como o prerender (puppeteer) captura o DOM final, o schema entra
 * no HTML estático servido para o Google e para as IAs.
 */
export default function JsonLd({ id, data }) {
  useEffect(() => {
    if (!data) return undefined;
    const scriptId = `jsonld-${id}`;
    let el = document.getElementById(scriptId);
    if (!el) {
      el = document.createElement('script');
      el.type = 'application/ld+json';
      el.id = scriptId;
      document.head.appendChild(el);
    }
    el.textContent = JSON.stringify(data);
    return () => {
      const existing = document.getElementById(scriptId);
      if (existing) existing.remove();
    };
  }, [id, data]);

  return null;
}
