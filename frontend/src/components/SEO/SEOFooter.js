import React from 'react';

/**
 * COMPONENTE SEO FOOTER - GREY HAT KEYWORDS
 * 
 * AVISO: Uso excessivo pode resultar em penalização do Google
 * Densidade recomendada: 3-5% | Este componente: ~8-10%
 * 
 * Use por sua conta e risco
 */

const SEOFooter = () => {
  // Keywords primárias do negócio
  const baseKeywords = [
    'sistema gestão empréstimos',
    'software controle crédito',
    'gestão financeira empréstimos',
    'controle parcelas juros',
    'software credores particulares',
    'sistema microcrédito',
    'gestão empréstimos pessoais',
    'controle inadimplência',
    'software cobrança automática',
    'sistema agiotagem profissional'
  ];

  // Variações de ação (menos agressivo que Los Dados)
  const actions = [
    'gerenciar',
    'controlar',
    'administrar'
  ];

  // Entidades específicas
  const entities = [
    'empréstimos',
    'parcelas',
    'clientes',
    'pagamentos',
    'juros',
    'cobrança'
  ];

  // Gerar combinações (limitado a ~50 ao invés de 200)
  const generateKeywords = () => {
    const keywords = [...baseKeywords];
    
    actions.forEach(action => {
      entities.forEach(entity => {
        keywords.push(`${action} ${entity}`);
      });
    });

    return keywords;
  };

  const allKeywords = generateKeywords();

  return (
    <div className="w-full bg-muted/20 border-t border-border py-8 mt-20">
      <div className="container mx-auto px-6">
        <h3 className="text-lg font-bold text-foreground mb-4 text-center">
          Recursos e Funcionalidades do Sistema
        </h3>
        
        {/* Keywords com internal links (moderado) */}
        <div className="flex flex-wrap justify-center gap-2 max-w-6xl mx-auto mb-6">
          {allKeywords.slice(0, 30).map((keyword, index) => (
            <a
              key={index}
              href="/login"
              className="text-xs text-muted-foreground hover:text-primary hover:underline transition-colors bg-background/30 px-2 py-1 rounded-sm border border-transparent hover:border-border"
            >
              {keyword}
            </a>
          ))}
        </div>

        {/* Keywords sem link (cloaking parcial - menos agressivo) */}
        <div className="flex flex-wrap justify-center gap-2 max-w-6xl mx-auto opacity-60">
          {allKeywords.slice(30).map((keyword, index) => (
            <span
              key={index}
              className="text-xs text-muted-foreground px-1"
            >
              {keyword}
            </span>
          ))}
        </div>

        {/* Conteúdo contextual (para Google não considerar spam) */}
        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            O <strong>JuroFácil</strong> é a plataforma completa para <em>gestão profissional de empréstimos</em>. 
            Se você busca <strong>software de controle de crédito</strong>, precisa <strong>gerenciar empréstimos particulares</strong> 
            ou realizar <strong>cobrança automática via PIX</strong>, nossa plataforma oferece todas as ferramentas necessárias. 
            Sistema usado por <strong>credores particulares</strong>, <strong>microcrédito</strong> e profissionais que precisam 
            de <strong>controle de inadimplência</strong> eficiente.
          </p>
        </div>

        {/* Competitor targeting (mencionar alternativas) */}
        <div className="mt-4 text-center">
          <p className="text-xs text-muted-foreground/60">
            Alternativa aos sistemas: Emdias Software, Planilhas Manuais, Controle Básico de Empréstimos
          </p>
        </div>
      </div>
    </div>
  );
};

export default SEOFooter;
