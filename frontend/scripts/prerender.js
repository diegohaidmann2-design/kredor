/**
 * Prerender estático das rotas públicas (SEO / preview de link sem JS).
 *
 * Estratégia (mesma ideia do react-snap, porém controlada por nós):
 *  1. Sobe um servidor estático local servindo a pasta build/ (com fallback SPA).
 *  2. Abre cada rota pública num Chromium headless (puppeteer-core).
 *  3. Espera o conteúdo real montar, rola a página para disparar as animações
 *     `whileInView` (framer-motion) e captura o HTML final já renderizado.
 *  4. Grava o HTML em build/<rota>/index.html — servido pelo nginx sem JS.
 *
 * Falhas NÃO quebram o build (log de aviso + exit 0): se o Chromium não estiver
 * disponível, a SPA continua funcionando normalmente (apenas sem prerender).
 */
const fs = require('fs');
const path = require('path');
const http = require('http');
const puppeteer = require('puppeteer-core');

const BUILD_DIR = path.resolve(__dirname, '..', 'build');
const PORT = Number(process.env.PRERENDER_PORT || 45678);

// Rotas públicas que devem ser entregues com conteúdo real no HTML inicial.
const ROUTES = [
  '/',
  '/sistema-gestao-emprestimos',
  '/cobranca-whatsapp',
  '/cobranca-pix',
  '/controle-de-parcelas-e-juros',
  '/gestao-de-clientes',
];

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.map': 'application/json',
  '.txt': 'text/plain',
  '.webmanifest': 'application/manifest+json',
};

function findChrome() {
  const candidates = [
    process.env.PUPPETEER_EXECUTABLE_PATH,
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
    '/root/bin/chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
  ].filter(Boolean);
  for (const c of candidates) {
    try {
      if (fs.existsSync(c)) return c;
    } catch (_) {}
  }
  return null;
}

function startStaticServer() {
  const server = http.createServer((req, res) => {
    try {
      const urlPath = decodeURIComponent(req.url.split('?')[0]);
      let filePath = path.join(BUILD_DIR, urlPath);

      if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        const ext = path.extname(filePath).toLowerCase();
        res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
        fs.createReadStream(filePath).pipe(res);
        return;
      }
      // Fallback SPA: qualquer rota desconhecida serve o index.html base.
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      fs.createReadStream(path.join(BUILD_DIR, 'index.html')).pipe(res);
    } catch (e) {
      res.writeHead(500);
      res.end('prerender static server error');
    }
  });
  return new Promise((resolve) => server.listen(PORT, () => resolve(server)));
}

// Rola a página inteira em passos para acionar animações `whileInView`.
async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let total = 0;
      const step = Math.max(300, Math.floor(window.innerHeight * 0.8));
      const timer = setInterval(() => {
        window.scrollBy(0, step);
        total += step;
        if (total >= document.body.scrollHeight + window.innerHeight) {
          clearInterval(timer);
          window.scrollTo(0, 0);
          resolve();
        }
      }, 120);
    });
  });
}

async function run() {
  if (!fs.existsSync(path.join(BUILD_DIR, 'index.html'))) {
    console.warn('[prerender] build/index.html não encontrado — pulei o prerender.');
    return;
  }

  const executablePath = findChrome();
  if (!executablePath) {
    console.warn('[prerender] Chromium não encontrado — pulei o prerender (SPA segue normal).');
    return;
  }
  console.log(`[prerender] usando Chromium em ${executablePath}`);

  const server = await startStaticServer();
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath,
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
      ],
    });

    for (const route of ROUTES) {
      const page = await browser.newPage();
      await page.setViewport({ width: 1280, height: 900 });
      // Não deixa o Service Worker interceptar/rodar durante o prerender.
      await page.evaluateOnNewDocument(() => {
        try {
          Object.defineProperty(navigator, 'serviceWorker', { get: () => undefined });
        } catch (_) {}
      });

      const url = `http://localhost:${PORT}${route}`;
      try {
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 45000 });
        // Espera o conteúdo real (headings) aparecer.
        await page.waitForFunction(
          () => {
            const root = document.getElementById('root');
            if (!root) return false;
            const h1 = document.querySelector('h1');
            return !!h1 && root.innerText.trim().length > 400;
          },
          { timeout: 30000 }
        ).catch(() => {});

        await autoScroll(page);
        await new Promise((r) => setTimeout(r, 1200)); // deixa animações assentarem

        let html = await page.content();
        if (!html.startsWith('<!DOCTYPE') && !html.startsWith('<!doctype')) {
          html = '<!doctype html>\n' + html;
        }

        const outDir =
          route === '/' ? BUILD_DIR : path.join(BUILD_DIR, route.replace(/^\/+/, ''));
        fs.mkdirSync(outDir, { recursive: true });
        fs.writeFileSync(path.join(outDir, 'index.html'), html, 'utf8');
        console.log(`[prerender] OK  ${route}  (${(html.length / 1024).toFixed(0)} KB)`);
      } catch (e) {
        console.warn(`[prerender] FALHOU ${route}: ${e.message}`);
      } finally {
        await page.close().catch(() => {});
      }
    }
  } catch (e) {
    console.warn(`[prerender] erro ao iniciar o Chromium: ${e.message}`);
  } finally {
    if (browser) await browser.close().catch(() => {});
    server.close();
  }
}

run()
  .then(() => process.exit(0))
  .catch((e) => {
    console.warn(`[prerender] erro inesperado: ${e.message}`);
    process.exit(0);
  });
