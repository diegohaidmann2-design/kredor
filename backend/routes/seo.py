"""
Rotas de SEO servidas pelo FastAPI.
- /api/sitemap.xml: sitemap dinâmico com lastmod real (data atual) e, quando
  existir a coleção `blog_posts`, inclui os artigos publicados.
"""
from fastapi import APIRouter, Response
from datetime import datetime, timezone

from config import db

router = APIRouter()

SITE = "https://kredor.com.br"

# (path, changefreq, priority) — apenas rotas públicas que existem de fato.
PUBLIC_ROUTES = [
    ("/", "weekly", "1.0"),
    ("/como-funciona", "monthly", "0.9"),
    ("/sistema-gestao-emprestimos", "monthly", "0.9"),
    ("/software-para-emprestimos", "monthly", "0.9"),
    ("/sistema-para-credores", "monthly", "0.9"),
    ("/sistema-microcredito", "monthly", "0.9"),
    ("/gestao-carteira-credito", "monthly", "0.9"),
    ("/contratos-digitais-ccb", "monthly", "0.9"),
    ("/emprestimo-particular-como-organizar", "monthly", "0.8"),
    ("/consulta-cpf-credito", "monthly", "0.7"),
    ("/cobranca-whatsapp", "monthly", "0.9"),
    ("/cobranca-pix", "monthly", "0.9"),
    ("/controle-de-parcelas-e-juros", "monthly", "0.9"),
    ("/gestao-de-clientes", "monthly", "0.9"),
    ("/calculadora-de-juros", "monthly", "0.8"),
    ("/blog", "weekly", "0.7"),
    ("/precos", "monthly", "0.8"),
    ("/faq", "monthly", "0.8"),
    ("/seguranca", "monthly", "0.6"),
    ("/sobre", "monthly", "0.6"),
    ("/contato", "monthly", "0.6"),
    ("/privacidade", "yearly", "0.4"),
    ("/termos", "yearly", "0.4"),
]


def _url_node(loc: str, lastmod: str, changefreq: str, priority: str) -> str:
    return (
        "  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>"
    )


async def gerar_sitemap_xml() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    nodes = [_url_node(f"{SITE}{path}", today, cf, pr) for path, cf, pr in PUBLIC_ROUTES]

    # Artigos de blog (quando a coleção existir e houver posts publicados).
    try:
        cursor = db.blog_posts.find({"publicado": True}, {"_id": 0, "slug": 1, "updated_at": 1})
        async for post in cursor:
            slug = post.get("slug")
            if not slug:
                continue
            lm = post.get("updated_at") or today
            if isinstance(lm, datetime):
                lm = lm.strftime("%Y-%m-%d")
            else:
                lm = str(lm)[:10]
            nodes.append(_url_node(f"{SITE}/blog/{slug}", lm, "monthly", "0.7"))
    except Exception:
        pass

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(nodes)
        + "\n</urlset>\n"
    )


@router.get("/sitemap.xml")
async def sitemap():
    xml = await gerar_sitemap_xml()
    return Response(content=xml, media_type="application/xml")
