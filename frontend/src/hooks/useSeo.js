import { useEffect } from 'react';

const SITE = 'https://kredor.com.br';

function setMeta(attr, key, content) {
  if (!content) return;
  let el = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}

function setCanonical(href) {
  let el = document.head.querySelector('link[rel="canonical"]');
  if (!el) {
    el = document.createElement('link');
    el.setAttribute('rel', 'canonical');
    document.head.appendChild(el);
  }
  el.setAttribute('href', href);
}

/**
 * Define título, descrição, canonical e tags sociais por página (client-side).
 * Observação: para preview de link sem JS (WhatsApp/Facebook) é necessário
 * prerender/edge no deploy — este hook cobre Google e navegadores.
 */
export default function useSeo({ title, description, path, image }) {
  useEffect(() => {
    const url = path ? `${SITE}${path}` : `${SITE}/`;
    if (title) document.title = title;
    if (description) setMeta('name', 'description', description);
    setCanonical(url);

    setMeta('property', 'og:title', title);
    setMeta('property', 'og:description', description);
    setMeta('property', 'og:url', url);
    setMeta('name', 'twitter:title', title);
    setMeta('name', 'twitter:description', description);
    setMeta('name', 'twitter:url', url);

    if (image) {
      const abs = image.startsWith('http') ? image : `${SITE}${image}`;
      setMeta('property', 'og:image', abs);
      setMeta('property', 'og:image:width', '1200');
      setMeta('property', 'og:image:height', '630');
      setMeta('name', 'twitter:image', abs);
      setMeta('name', 'twitter:card', 'summary_large_image');
    }
  }, [title, description, path, image]);
}
