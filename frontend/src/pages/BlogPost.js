import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, Clock } from 'lucide-react';
import { Button } from '../components/ui/button';
import Footer from '../components/Footer';
import JsonLd from '../components/JsonLd';
import useSeo from '../hooks/useSeo';
import { articleSchema, breadcrumbSchema } from '../lib/seoSchema';
import { blogAPI, configuracoesAPI } from '../api/api';
import logomark from '../assets/logomark.png';

const BlogPost = () => {
  const { slug } = useParams();
  const [post, setPost] = useState(
    () => (typeof window !== 'undefined' && window.__PRERENDER__ && window.__PRERENDER__.blogPost) || null
  );
  const [notFound, setNotFound] = useState(false);
  const [config, setConfig] = useState({});
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    setIsDark(localStorage.getItem('sgej-theme') !== 'light');
    window.scrollTo(0, 0);
    (async () => {
      try {
        const res = await blogAPI.obter(slug);
        setPost(res.data);
      } catch (e) {
        setNotFound(true);
      }
      configuracoesAPI.obterLanding().then((r) => setConfig(r.data || {})).catch(() => {});
    })();
  }, [slug]);

  useSeo({
    title: post ? `${post.titulo} | Blog Kredor` : 'Blog | Kredor',
    description: post ? (post.meta_description || post.resumo) : undefined,
    path: `/blog/${slug}`,
    image: post ? post.capa : undefined,
  });

  const cardBg = isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200';

  return (
    <div className={`min-h-screen ${isDark ? 'bg-slate-950 text-white' : 'bg-white text-slate-900'}`}>
      <header className={`sticky top-0 z-40 backdrop-blur-xl border-b ${isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white/80 border-slate-200'}`}>
        <nav className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <img src={logomark} alt="Kredor" className="w-9 h-9 object-contain" />
            <span className="text-lg font-display font-bold"><span className="text-primary">Kredor</span></span>
          </Link>
          <Link to="/blog" className={`flex items-center gap-2 text-sm ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>
            <ArrowLeft className="w-4 h-4" /> Todos os artigos
          </Link>
        </nav>
      </header>

      <main className="container mx-auto px-4 py-12 max-w-3xl">
        {notFound && (
          <div className="py-20 text-center">
            <h1 className="text-2xl font-display font-bold mb-4">Artigo não encontrado</h1>
            <Link to="/blog" className="text-primary hover:underline">Ver todos os artigos</Link>
          </div>
        )}

        {post && (
          <motion.article initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <JsonLd id="article" data={articleSchema({ title: post.titulo, description: post.meta_description || post.resumo, slug: post.slug, image: post.capa, datePublished: post.data_publicacao, dateModified: post.updated_at })} />
            <JsonLd id="article-breadcrumb" data={breadcrumbSchema([{ name: 'Blog', path: '/blog' }, { name: post.titulo, path: `/blog/${post.slug}` }])} />

            <span className="text-xs font-semibold uppercase tracking-wide text-primary">{post.categoria}</span>
            <h1 className="text-3xl md:text-4xl font-display font-bold mt-2 mb-4 leading-tight" data-testid="post-title">{post.titulo}</h1>
            <div className={`flex items-center gap-4 text-sm mb-8 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
              <span>{post.autor}</span>
              <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {post.lido_min || 5} min</span>
            </div>

            <div
              className={`blog-content ${isDark ? 'blog-content-dark' : ''}`}
              data-testid="post-content"
              dangerouslySetInnerHTML={{ __html: post.conteudo_html }}
            />

            {/* CTA para a LP relacionada */}
            <div className="mt-12 rounded-2xl border border-primary/30 bg-primary/10 p-8 text-center">
              <h2 className="text-xl md:text-2xl font-display font-bold mb-3">Pronto para profissionalizar sua operação?</h2>
              <p className={`mb-6 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Teste o Kredor por 7 dias, sem cartão de crédito.</p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                {post.cta_to && (
                  <Link to={post.cta_to}>
                    <Button size="lg" variant="outline" data-testid="post-cta-lp">{post.cta_label || 'Saiba mais'}</Button>
                  </Link>
                )}
                <Link to="/login">
                  <Button size="lg" className="bg-primary hover:bg-primary/90 text-white px-8" data-testid="post-cta-signup">
                    Começar grátis <ArrowRight className="ml-2 w-5 h-5" />
                  </Button>
                </Link>
              </div>
            </div>

            <div className={`mt-8 rounded-lg border p-5 ${cardBg}`}>
              <p className="text-xs mb-1 text-primary font-semibold uppercase tracking-wide">Aviso</p>
              <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>O Kredor é um software de gestão e cobrança. Não concede empréstimos nem realiza operações de crédito.</p>
            </div>
          </motion.article>
        )}
      </main>

      <Footer config={config} isDark={isDark} />
    </div>
  );
};

export default BlogPost;
