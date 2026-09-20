import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Clock, ArrowRight } from 'lucide-react';
import Footer from '../components/Footer';
import JsonLd from '../components/JsonLd';
import useSeo from '../hooks/useSeo';
import { breadcrumbSchema, SITE } from '../lib/seoSchema';
import { blogAPI, configuracoesAPI } from '../api/api';
import logomark from '../assets/logomark.png';

const Blog = () => {
  const [posts, setPosts] = useState(
    () => (typeof window !== 'undefined' && window.__PRERENDER__ && window.__PRERENDER__.blogList) || []
  );
  const [config, setConfig] = useState({});
  const [isDark, setIsDark] = useState(true);

  useSeo({
    title: 'Blog do Kredor — crédito, cobrança e gestão de empréstimos',
    description: 'Guias práticos para credores: como controlar empréstimos, cobrar pelo WhatsApp, calcular juros, formalizar contratos e reduzir a inadimplência.',
    path: '/blog',
  });

  useEffect(() => {
    setIsDark(localStorage.getItem('sgej-theme') !== 'light');
    window.scrollTo(0, 0);
    (async () => {
      try {
        const [pRes, cRes] = await Promise.all([
          blogAPI.listar(),
          configuracoesAPI.obterLanding().catch(() => ({ data: {} })),
        ]);
        setPosts(pRes.data || []);
        setConfig(cRes.data || {});
      } catch (e) {}
    })();
  }, []);

  const cardBg = isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200';

  // Agrupa os posts por categoria, preservando a ordem em que cada categoria aparece.
  const porCategoria = posts.reduce((acc, p) => {
    const cat = p.categoria || 'Geral';
    (acc[cat] = acc[cat] || []).push(p);
    return acc;
  }, {});
  const categorias = Object.keys(porCategoria);

  const blogSchema = {
    '@context': 'https://schema.org',
    '@type': 'Blog',
    name: 'Blog do Kredor',
    url: `${SITE}/blog`,
    inLanguage: 'pt-BR',
    blogPost: posts.slice(0, 30).map((p) => ({
      '@type': 'BlogPosting',
      headline: p.titulo,
      url: `${SITE}/blog/${p.slug}`,
      datePublished: p.data_publicacao,
      description: p.meta_description || p.resumo,
    })),
  };

  return (
    <div className={`min-h-screen ${isDark ? 'bg-slate-950 text-white' : 'bg-white text-slate-900'}`}>
      <JsonLd id="blog-breadcrumb" data={breadcrumbSchema([{ name: 'Blog', path: '/blog' }])} />
      {posts.length > 0 && <JsonLd id="blog-list" data={blogSchema} />}

      <header className={`sticky top-0 z-40 backdrop-blur-xl border-b ${isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white/80 border-slate-200'}`}>
        <nav className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <img src={logomark} alt="Kredor" className="w-9 h-9 object-contain" />
            <span className="text-lg font-display font-bold"><span className="text-primary">Kredor</span></span>
          </Link>
          <Link to="/" className={`flex items-center gap-2 text-sm ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>
            <ArrowLeft className="w-4 h-4" /> Voltar
          </Link>
        </nav>
      </header>

      <main className="container mx-auto px-4 py-14 max-w-5xl">
        <div className="mb-12 max-w-2xl">
          <span className="inline-block mb-4 text-xs font-semibold tracking-wide uppercase text-primary bg-primary/10 border border-primary/20 rounded-full px-3 py-1">Blog</span>
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-4">Conteúdo para quem empresta e quer receber</h1>
          <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Guias diretos sobre cobrança, juros, contratos e organização da sua carteira de crédito.</p>
        </div>

        <div className="space-y-14" data-testid="blog-list">
          {categorias.map((cat) => (
            <section key={cat} data-testid={`blog-cat-${cat}`}>
              <div className="flex items-center gap-3 mb-6">
                <h2 className="text-xl md:text-2xl font-display font-bold">{cat}</h2>
                <span className={`text-xs px-2 py-0.5 rounded-full ${isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-500'}`}>
                  {porCategoria[cat].length}
                </span>
                <span className={`flex-1 h-px ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`} />
              </div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {porCategoria[cat].map((p, i) => (
                  <motion.article
                    key={p.slug}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: (i % 3) * 0.05 }}
                    className={`rounded-xl border overflow-hidden flex flex-col ${cardBg}`}
                    data-testid={`blog-card-${p.slug}`}
                  >
                    <Link to={`/blog/${p.slug}`} className="block aspect-[1200/630] overflow-hidden bg-slate-900">
                      {p.capa && (
                        <img src={p.capa} alt={p.titulo} loading="lazy" className="w-full h-full object-cover" />
                      )}
                    </Link>
                    <div className="p-6 flex flex-col flex-1">
                      <span className="text-xs font-semibold uppercase tracking-wide text-primary mb-2">{p.categoria}</span>
                      <h3 className="text-lg font-display font-semibold mb-2 leading-snug">
                        <Link to={`/blog/${p.slug}`} className="hover:text-primary transition-colors">{p.titulo}</Link>
                      </h3>
                      <p className={`text-sm mb-4 flex-1 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{p.resumo}</p>
                      <div className="flex items-center justify-between">
                        <span className={`text-xs flex items-center gap-1 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
                          <Clock className="w-3 h-3" /> {p.lido_min || 5} min de leitura
                        </span>
                        <Link to={`/blog/${p.slug}`} className="text-sm text-primary font-medium inline-flex items-center gap-1 hover:gap-2 transition-all">
                          Ler <ArrowRight className="w-4 h-4" />
                        </Link>
                      </div>
                    </div>
                  </motion.article>
                ))}
              </div>
            </section>
          ))}
        </div>

        {posts.length === 0 && (
          <p className={`${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Em breve, novos artigos.</p>
        )}
      </main>

      <Footer config={config} isDark={isDark} />
    </div>
  );
};

export default Blog;
