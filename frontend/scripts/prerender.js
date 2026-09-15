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
const https = require('https');
const puppeteer = require('puppeteer-core');

const BUILD_DIR = path.resolve(__dirname, '..', 'build');
const PORT = Number(process.env.PRERENDER_PORT || 45678);

// Rotas públicas que devem ser entregues com conteúdo real no HTML inicial.
const ROUTES = [
  '/',
  '/sistema-gestao-emprestimos',
  '/software-para-emprestimos',
  '/sistema-para-credores',
  '/sistema-microcredito',
  '/gestao-carteira-credito',
  '/contratos-digitais-ccb',
  '/emprestimo-particular-como-organizar',
  '/consulta-cpf-credito',
  '/cobranca-whatsapp',
  '/cobranca-pix',
  '/controle-de-parcelas-e-juros',
  '/gestao-de-clientes',
  '/calculadora-de-juros',
  '/blog',
  // Institucionais: estão no sitemap, então precisam do HTML pronto como as demais.
  '/como-funciona',
  '/precos',
  '/faq',
  '/seguranca',
  '/sobre',
  '/contato',
  '/privacidade',
  '/termos',
];

// Busca JSON do backend e injeta no HTML (evita CORS e deixa o conteúdo no HTML inicial).
//
// O padrão é o site público, e não localhost:8001, porque durante `docker compose build` não
// existe backend no container de build: o fetch falhava calado e o HTML saía com os valores
// padrão do CÓDIGO. Era assim que /precos ia para o ar anunciando R$ 197 e R$ 497 depois de
// os preços já estarem 100 e 200 no banco — e por isso nenhum post do blog era
// prerenderizado. Sobrescreva com PRERENDER_API_URL em ambiente sem acesso à internet.
function fetchJson(apiPath) {
  const base = process.env.PRERENDER_API_URL || 'https://kredor.com.br';
  const cliente = base.startsWith('https:') ? https : http;
  return new Promise((resolve) => {
    try {
      cliente
        .get(`${base}${apiPath}`, (res) => {
          let data = '';
          res.on('data', (c) => (data += c));
          res.on('end', () => {
            try {
              resolve(JSON.parse(data));
            } catch (_) {
              resolve(null);
            }
          });
        })
        .on('error', () => resolve(null));
    } catch (_) {
      resolve(null);
    }
  });
}

// Slugs de artigos publicados para prerenderizar cada /blog/<slug>.
async function fetchBlogRoutes() {
  const posts = await fetchJson('/api/blog/posts');
  return (posts || []).map((p) => `/blog/${p.slug}`);
}

// Configuração da landing (nome, preços, dias de trial). Buscada UMA vez e injetada em
// todas as rotas: sem ela o HTML estático mostra os defaults do código, que são uma cópia
// desatualizada do que está no banco — preço errado no HTML que o Google indexa.
let configLanding = null;

async function carregarConfigLanding() {
  configLanding = await fetchJson('/api/configuracoes/landing');
  if (configLanding) {
    console.log(`[prerender] config da landing carregada (trial ${configLanding.plano_trial_dias} dias)`);
  } else {
    console.warn('[prerender] config da landing indisponível — o HTML usará os padrões do código');
  }
}

// Planos com os ciclos de cobrança, para a página de preços sair pronta.
let planos = null;

async function carregarPlanos() {
  planos = await fetchJson('/api/assinaturas/planos');
}

// Dados a injetar em window.__PRERENDER__ conforme a rota (blog depende de API).
async function prerenderDataFor(route) {
  const comum = {};
  if (configLanding) comum.landingConfig = configLanding;
  if (planos) comum.planos = planos;

  if (route === '/blog') {
    return { ...comum, blogList: (await fetchJson('/api/blog/posts')) || [] };
  }
  if (route.startsWith('/blog/')) {
    const slug = route.slice('/blog/'.length);
    return { ...comum, blogPost: await fetchJson(`/api/blog/posts/${slug}`) };
  }
  return comum;
}

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
  // Captura o index.html base UMA vez. O fallback SPA deve sempre servir este
  // shell original — nunca o build/index.html que é sobrescrito quando a rota
  // '/' é prerenderizada (senão o schema do Home vaza para as outras rotas).
  const baseIndexPath = path.join(BUILD_DIR, 'index.html');
  const BASE_HTML = fs.readFileSync(baseIndexPath);

  const server = http.createServer((req, res) => {
    try {
      const urlPath = decodeURIComponent(req.url.split('?')[0]);
      let filePath = path.join(BUILD_DIR, urlPath);

      // O index.html base é sempre servido a partir da cópia em memória.
      if (urlPath === '/' || urlPath === '/index.html') {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(BASE_HTML);
        return;
      }

      if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
        const ext = path.extname(filePath).toLowerCase();
        res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
        fs.createReadStream(filePath).pipe(res);
        return;
      }
      // Fallback SPA: qualquer rota desconhecida serve o index.html base original.
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(BASE_HTML);
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

    await carregarConfigLanding();
    await carregarPlanos();

    const blogRoutes = await fetchBlogRoutes();
    const allRoutes = [...ROUTES, ...blogRoutes];
    for (const route of allRoutes) {
      const page = await browser.newPage();
      await page.setViewport({ width: 1280, height: 900 });
      // Injeta dados dependentes de API (blog) para o React montar sem depender
      // de fetch cross-origin (que o CORS bloqueia a partir do localhost do prerender).
      const preData = await prerenderDataFor(route);
      // Não deixa o Service Worker interceptar/rodar durante o prerender.
      await page.evaluateOnNewDocument((d) => {
        try {
          Object.defineProperty(navigator, 'serviceWorker', { get: () => undefined });
        } catch (_) {}
        try {
          window.__PRERENDER__ = d;
        } catch (_) {}
      }, preData || {});

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
