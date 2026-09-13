import React from 'react';
import { PieChart, Wallet, BarChart3, Bell, ShieldCheck, TrendingUp } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const GestaoCarteiraCredito = () => (
  <CommercialLanding
    seo={{
      title: 'Gestão de carteira de crédito e recebíveis | Kredor',
      description: 'Gestão de carteira de crédito: acompanhe recebíveis, inadimplência e fluxo de caixa em tempo real, com cobrança automática no PIX e WhatsApp. Teste 7 dias grátis.',
      path: '/gestao-carteira-credito',
      image: '/og-image-kredor.jpg',
    }}
    eyebrow="Carteira sob controle"
    h1="Gestão de carteira de crédito: recebíveis e inadimplência em tempo real"
    subtitle="Enxergue a saúde da sua operação de ponta a ponta: quanto tem a receber, o que vence, quem atrasou e como está a inadimplência — com cobrança automática para manter o caixa girando."
    heroBullets={[
      'Total a receber e projeção de caixa',
      'Inadimplência da carteira em tempo real',
      'Baixa automática de pagamentos via PIX',
      'Cobrança automática para reduzir atrasos',
    ]}
    blocks={[
      { icon: PieChart, title: 'Visão completa da carteira', text: 'Todos os contratos, parcelas e recebíveis em um painel único. Filtre por situação, período e cliente e entenda onde está o seu dinheiro.' },
      { icon: Wallet, title: 'Recebíveis previsíveis', text: 'Veja vencimentos do dia, valores em aberto e projeções de caixa para planejar novas liberações com segurança.' },
      { icon: TrendingUp, title: 'Inadimplência que você acompanha', text: 'Indicadores de atraso e recuperação atualizados automaticamente, para agir antes de o problema crescer.' },
      { icon: Bell, title: 'Cobrança que mantém o caixa girando', text: 'Régua automática no WhatsApp com PIX na mensagem acelera o recebimento e reduz o valor parado em aberto.' },
      { icon: BarChart3, title: 'Relatórios para decidir', text: 'Faturamento, inadimplência e desempenho por período, exportáveis em PDF e Excel.' },
      { icon: ShieldCheck, title: 'Rastreável e seguro', text: 'Auditoria de ações, permissões por perfil e criptografia de dados sensíveis.' },
    ]}
    differentials={[
      { title: 'Do contrato ao caixa', text: 'A mesma plataforma controla a operação e mostra o impacto no seu fluxo de caixa.' },
      { title: 'PIX com baixa automática', text: 'Menos conciliação manual, mais tempo para gerir a carteira.' },
      { title: 'Alertas de vencimento', text: 'Nada passa batido: o sistema avisa o que vence e o que atrasou.' },
      { title: 'Exportação para conciliação', text: 'Leve os dados para a contabilidade em poucos cliques.' },
    ]}
    faq={[
      { q: 'Consigo ver quanto tenho a receber hoje?', a: 'Sim. O painel mostra vencimentos do dia, total em aberto e projeção de recebíveis em tempo real.' },
      { q: 'Como o sistema ajuda a reduzir a inadimplência?', a: 'Com cobrança automática (PIX e WhatsApp), alertas de vencimento e indicadores que permitem agir cedo nos atrasos.' },
      { q: 'Dá para exportar os dados?', a: 'Sim, relatórios em PDF e Excel para conciliação e prestação de contas.' },
      { q: 'Tem teste grátis?', a: 'Sim, 7 dias grátis, sem cartão de crédito.' },
    ]}
    related={[
      { to: '/sistema-microcredito', label: 'Sistema para microcrédito' },
      { to: '/sistema-gestao-emprestimos', label: 'Sistema de gestão de empréstimos' },
      { to: '/controle-de-parcelas-e-juros', label: 'Controle de parcelas e juros' },
      { to: '/cobranca-pix', label: 'Cobrança por PIX' },
      { to: '/precos', label: 'Ver preços' },
    ]}
  />
);

export default GestaoCarteiraCredito;
