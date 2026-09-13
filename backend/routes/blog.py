"""
Blog público (SEO). Somente leitura para o site; a criação dos artigos é feita
por seed (scripts/seed_blog.py). Coleção: blog_posts.
"""
from fastapi import APIRouter, HTTPException

from config import db

router = APIRouter()


@router.get("/posts")
async def listar_posts():
    """Lista os artigos publicados (sem o corpo, para a listagem)."""
    posts = await db.blog_posts.find(
        {"publicado": True},
        {"_id": 0, "conteudo_html": 0},
    ).sort("data_publicacao", -1).to_list(200)
    return posts


@router.get("/posts/{slug}")
async def obter_post(slug: str):
    post = await db.blog_posts.find_one({"slug": slug, "publicado": True}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")
    return post
