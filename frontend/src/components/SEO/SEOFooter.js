import React from 'react';

/**
 * COMPONENTE SEO FOOTER - BLACK HAT FULL (REPLICAÇÃO LOS DADOS)
 * 
 * ⚠️ AVISO CRÍTICO: Alta probabilidade de penalização Google
 * Densidade: 15-18% (vs. 3-5% recomendado)
 * Risco: 60-80% de penalização em 12 meses
 * 
 * USE POR SUA CONTA E RISCO
 */

const SEOFooter = () => {
  // Keywords base (expandidas)
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
    'sistema agiotagem profissional',
    'painel empréstimos',
    'app gestão crédito',
    'plataforma empréstimos'
  ];

  // Variações de ação (TODAS do Los Dados)
  const actions = [
    'gerenciar',
    'controlar',
    'administrar',
    'consultar',
    'localizar',
    'encontrar',
    'buscar',
    'rastrear'
  ];

  // Entidades específicas (expandido)
  const entities = [
    'empréstimos',
    'parcelas',
    'clientes',
    'pagamentos',
    'juros',
    'cobrança',
    'inadimplência',
    'crédito',
    'financiamento',
    'devedores'
  ];

  // Gerar combinações MASSIVAS (estilo Los Dados)
  const generateKeywords = () => {
    const keywords = [...baseKeywords];
    
    // Combinação: ação + entidade
    actions.forEach(action => {
      entities.forEach(entity => {
        keywords.push(`${action} ${entity}`);
      });
    });

    // Adicionar variações específicas
    entities.forEach(entity => {
      keywords.push(`sistema ${entity}`);
      keywords.push(`software ${entity}`);
      keywords.push(`app ${entity}`);
      keywords.push(`controle ${entity}`);
    });

    return keywords;
  };

  const allKeywords = generateKeywords();

  return (
    <div className="w-full bg-muted/20 border-t border-border py-8 mt-20">
      <div className="container mx-auto px-6">
        <h3 className="text-lg font-bold text-foreground mb-4 text-center">
          Recursos e Funcionalidades - Sistema de Gestão
        </h3>
        
        {/* Keywords com internal links (MASSIVO - estilo Los Dados) */}
        <div className="flex flex-wrap justify-center gap-2 max-w-6xl mx-auto mb-6">
          {allKeywords.slice(0, 80).map((keyword, index) => (
            <a
              key={index}
              href="/login"
              className="text-xs text-muted-foreground hover:text-primary hover:underline transition-colors bg-background/30 px-2 py-1 rounded-sm border border-transparent hover:border-border"
            >
              {keyword}
            </a>
          ))}
        </div>

        {/* Keywords sem link - CLOAKING AGRESSIVO (opacity 30% - estilo Los Dados) */}
        <div className="flex flex-wrap justify-center gap-1 max-w-6xl mx-auto opacity-30">
          {allKeywords.slice(80).map((keyword, index) => (
            <span
              key={index}
              className="text-xs text-muted-foreground px-1"
            >
              {keyword}
            </span>
          ))}
        </div>

        {/* Repetição excessiva - BLACK HAT PURO */}
        <div className="flex flex-wrap justify-center gap-1 max-w-6xl mx-auto mt-4 opacity-25 text-[10px]">
          <span>consultar empréstimos</span>
          <span>puxar empréstimos</span>
          <span>localizar empréstimos</span>
          <span>encontrar empréstimos</span>
          <span>buscar empréstimos</span>
          <span>rastrear empréstimos</span>
          <span>pesquisar empréstimos</span>
          <span>verificar empréstimos</span>
          <span>consultar parcelas</span>
          <span>puxar parcelas</span>
          <span>localizar parcelas</span>
          <span>encontrar parcelas</span>
          <span>buscar parcelas</span>
          <span>rastrear parcelas</span>
          <span>consultar clientes</span>
          <span>puxar clientes</span>
          <span>localizar clientes</span>
          <span>encontrar clientes</span>
          <span>consultar pagamentos</span>
          <span>puxar pagamentos</span>
          <span>localizar pagamentos</span>
          <span>consultar juros</span>
          <span>calcular juros</span>
          <span>gerenciar juros</span>
          <span>controlar inadimplência</span>
          <span>gerenciar inadimplência</span>
          <span>reduzir inadimplência</span>
          <span>consultar devedores</span>
          <span>localizar devedores</span>
          <span>encontrar devedores</span>
        </div>

        {/* Conteúdo contextual */}
        <div className="mt-8 text-center">
          <p className="text-sm text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            O <strong>JuroFácil</strong> é o sistema mais completo para <em>gestão profissional de empréstimos</em> e 
            <strong> controle de crédito</strong>. Se você precisa <strong>gerenciar empréstimos particulares</strong>, 
            <strong> consultar parcelas</strong>, <strong>localizar clientes inadimplentes</strong>, 
            <strong> controlar pagamentos</strong>, <strong>calcular juros automáticos</strong> ou 
            <strong> realizar cobrança via PIX</strong>, nossa plataforma oferece tudo em um só lugar. 
            Sistema usado por <strong>credores particulares</strong>, <strong>microcrédito</strong>, 
            <strong>cooperativas</strong> e profissionais que precisam de <strong>controle total de inadimplência</strong>.
          </p>
        </div>

        {/* Competitor targeting (AGRESSIVO) */}
        <div className="mt-4 text-center">
          <p className="text-xs text-muted-foreground/60">
            Melhor que: Emdias Software | Planilhas Manuais | Controle Básico | Sistemas Genéricos | 
            Software de Agiotagem | Painel de Empréstimos | App de Crédito
          </p>
        </div>
      </div>
    </div>
  );
};

export default SEOFooter;
