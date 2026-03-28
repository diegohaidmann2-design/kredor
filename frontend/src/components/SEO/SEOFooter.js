import React from 'react';

/**
 * SEO FOOTER - BLACK HAT (REPLICAÇÃO EXATA LOS DADOS)
 * 
 * Estrutura: Igual Los Dados
 * - Título: "Termos Mais Buscados & Funcionalidades"
 * - Links clicáveis (keywords principais)
 * - Keywords repetidas visíveis (sem links)
 * - Parágrafo contextual no final
 * 
 * TUDO VISÍVEL - Não é cloaking oculto
 */

const SEOFooter = () => {
  // Keywords principais COM LINKS (estilo Los Dados)
  const mainKeywords = [
    'sistema gestão empréstimos',
    'software controle crédito',
    'painel empréstimos',
    'sistema microcrédito',
    'controle parcelas',
    'gestão financeira empréstimos',
    'software credores',
    'sistema agiotagem',
    'painel cobrança',
    'controle inadimplência',
    'software empréstimos pessoais',
    'gestão crédito particular',
    'sistema cobrança automática',
    'painel financeiro',
    'controle juros',
    'como gerenciar empréstimos',
    'sistema para credores',
    'melhor software empréstimos',
    'painel gestão crédito',
    'sistema controle parcelas',
    'software calcular juros',
    'gestão devedores',
    'controle pagamentos',
    'sistema pix empréstimos',
    'software cobrança whatsapp',
    'painel inadimplência',
    'gestão carteira crédito',
    'controle clientes empréstimos',
    'sistema juros compostos',
    'software agiotagem profissional'
  ];

  // Keywords repetidas SEM LINKS (todas as variações)
  const allVariations = [
    // Consultar/Gerenciar
    'consultar empréstimos', 'gerenciar empréstimos', 'controlar empréstimos', 'administrar empréstimos',
    'consultar parcelas', 'gerenciar parcelas', 'controlar parcelas', 'administrar parcelas',
    'consultar clientes', 'gerenciar clientes', 'controlar clientes', 'administrar clientes',
    'consultar pagamentos', 'gerenciar pagamentos', 'controlar pagamentos', 'administrar pagamentos',
    'consultar juros', 'calcular juros', 'controlar juros', 'gerenciar juros',
    'consultar inadimplência', 'controlar inadimplência', 'reduzir inadimplência', 'gerenciar inadimplência',
    
    // Localizar/Encontrar
    'localizar devedores', 'encontrar devedores', 'buscar devedores', 'rastrear devedores',
    'localizar clientes', 'encontrar clientes', 'buscar clientes', 'pesquisar clientes',
    'localizar pagamentos', 'encontrar pagamentos', 'buscar pagamentos', 'verificar pagamentos',
    
    // Sistemas e Software
    'sistema empréstimos', 'software empréstimos', 'app empréstimos', 'plataforma empréstimos',
    'sistema crédito', 'software crédito', 'app crédito', 'plataforma crédito',
    'sistema parcelas', 'software parcelas', 'app parcelas', 'controle parcelas',
    'sistema juros', 'software juros', 'calculadora juros', 'app juros',
    'sistema cobrança', 'software cobrança', 'app cobrança', 'plataforma cobrança',
    
    // Específicos
    'empréstimo particular', 'crédito pessoal', 'microcrédito', 'financiamento pessoal',
    'juros simples', 'juros compostos', 'taxa juros', 'cálculo juros',
    'parcela empréstimo', 'prestação empréstimo', 'amortização', 'carência',
    'devedor inadimplente', 'cliente inadimplente', 'atraso pagamento', 'cobrança dívida',
    
    // Ações
    'cobrar empréstimo', 'receber pagamento', 'emitir cobrança', 'enviar cobrança',
    'gerar parcela', 'calcular parcela', 'simular empréstimo', 'aprovar crédito',
    'bloquear cliente', 'negativar devedor', 'recuperar crédito', 'renegociar dívida'
  ];

  return (
    <div className="w-full bg-muted/30 border-t border-border py-12">
      <div className="container mx-auto px-6">
        <h3 className="text-xl font-bold text-foreground mb-6 text-center">
          Termos Mais Buscados &amp; Funcionalidades
        </h3>
        
        {/* Keywords principais COM LINKS (estilo Los Dados) */}
        <div className="flex flex-wrap justify-center gap-2 max-w-6xl mx-auto">
          {mainKeywords.map((keyword, index) => (
            <a
              key={index}
              className="text-xs text-muted-foreground hover:text-primary hover:underline transition-colors bg-background/50 px-2 py-1 rounded-sm border border-transparent hover:border-border"
              href="/login"
            >
              {keyword}
            </a>
          ))}
        </div>

        {/* Keywords repetidas SEM LINKS - VISÍVEIS (estilo Los Dados) */}
        <div className="flex flex-wrap justify-center gap-2 max-w-6xl mx-auto mt-6 opacity-50">
          {allVariations.map((keyword, index) => (
            <span
              key={index}
              className="text-xs text-muted-foreground px-1"
            >
              {keyword}
            </span>
          ))}
        </div>

        {/* Parágrafo contextual (IMPORTANTE - justifica as keywords) */}
        <div className="mt-8 text-center">
          <p className="text-sm text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            O <strong>JuroFácil</strong> é a ferramenta definitiva para <em>gestão profissional de empréstimos</em> 
            e <strong>controle de crédito</strong>. Se você procura por <strong>sistema de gestão de empréstimos</strong>, 
            <strong> software para controle de crédito</strong>, ou precisa <strong>gerenciar parcelas</strong> para 
            fins de cobrança e controle de inadimplência, nossa plataforma oferece recursos completos. 
            Diferente de planilhas e controles manuais, garantimos automação e precisão para 
            <strong> credores particulares</strong>, <strong>microcrédito</strong> e profissionais que precisam 
            <strong> calcular juros</strong>, <strong>gerar cobranças</strong> e realizar 
            <strong> gestão de devedores</strong> de forma profissional.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SEOFooter;
