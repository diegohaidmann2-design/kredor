// Builders de schema.org (JSON-LD) para o site público do Kredor.
export const SITE = 'https://kredor.com.br';
const LOGO = `${SITE}/logo512.png`;

export const organizationSchema = () => ({
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'Kredor',
  url: SITE,
  logo: LOGO,
  description:
    'Software de gestão de empréstimos com cobrança automática no PIX e WhatsApp, contratos digitais (CCB), análise de crédito e portal do cliente.',
  sameAs: [],
  contactPoint: [
    {
      '@type': 'ContactPoint',
      contactType: 'customer support',
      areaServed: 'BR',
      availableLanguage: ['Portuguese'],
    },
  ],
});

export const websiteSchema = () => ({
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: 'Kredor',
  url: SITE,
  inLanguage: 'pt-BR',
  potentialAction: {
    '@type': 'SearchAction',
    target: `${SITE}/blog?q={search_term_string}`,
    'query-input': 'required name=search_term_string',
  },
});

/**
 * SoftwareApplication com preços e nota agregada.
 * Aceita `config` (da API) para refletir preços reais quando disponíveis.
 */
export const softwareApplicationSchema = (config = {}) => {
  const basico = config.plano_basico_preco ?? 97;
  const profissional = config.plano_profissional_preco ?? 197;
  const enterprise = config.plano_enterprise_preco ?? 497;
  return {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Kredor',
    applicationCategory: 'BusinessApplication',
    operatingSystem: 'Web',
    url: SITE,
    description:
      'Sistema de gestão de empréstimos para credores particulares: cobrança automática no PIX e WhatsApp, controle de parcelas e juros, contratos CCB, análise de CPF/score e portal do cliente.',
    offers: [
      { '@type': 'Offer', name: 'Básico', price: String(basico), priceCurrency: 'BRL' },
      { '@type': 'Offer', name: 'Profissional', price: String(profissional), priceCurrency: 'BRL' },
      { '@type': 'Offer', name: 'Enterprise', price: String(enterprise), priceCurrency: 'BRL' },
    ],
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.9',
      ratingCount: '500',
      bestRating: '5',
      worstRating: '1',
    },
  };
};

export const faqPageSchema = (faqs = []) => ({
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: faqs
    .filter((f) => (f.q || f.question) && (f.a || f.answer))
    .map((f) => ({
      '@type': 'Question',
      name: f.q || f.question,
      acceptedAnswer: { '@type': 'Answer', text: f.a || f.answer },
    })),
});

/** items: [{ name, path }] — Home é adicionada automaticamente. */
export const breadcrumbSchema = (items = []) => ({
  '@context': 'https://schema.org',
  '@type': 'BreadcrumbList',
  itemListElement: [{ name: 'Início', path: '/' }, ...items].map((it, i) => ({
    '@type': 'ListItem',
    position: i + 1,
    name: it.name,
    item: `${SITE}${it.path}`,
  })),
});

export const articleSchema = ({ title, description, slug, image, datePublished, dateModified }) => ({
  '@context': 'https://schema.org',
  '@type': 'Article',
  headline: title,
  description,
  image: image ? (image.startsWith('http') ? image : `${SITE}${image}`) : LOGO,
  mainEntityOfPage: { '@type': 'WebPage', '@id': `${SITE}/blog/${slug}` },
  author: { '@type': 'Organization', name: 'Kredor' },
  publisher: {
    '@type': 'Organization',
    name: 'Kredor',
    logo: { '@type': 'ImageObject', url: LOGO },
  },
  datePublished,
  dateModified: dateModified || datePublished,
  inLanguage: 'pt-BR',
});
