import React from 'react';
import { Layers, Bell, Calculator, BarChart3, ShieldCheck, Repeat } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const SistemaMicrocredito = () => (
  <CommercialLanding
    seo={{
      title: 'Sistema para microcrédito e operações de crédito | Kredor',
      description: 'Sistema para microcrédito: gerencie muitos contratos de baixo valor, automatize a cobrança no PIX e WhatsApp e controle a inadimplência em escala. Teste 7 dias grátis.',
      path: '/sistema-microcredito',
      image: '/og-image-kredor.jpg',
    }}
    eyebrow="Microcrédito em escala"
    h1="Sistema para microcrédito: muitos contratos, cobrança automática e inadimplência sob controle"
    subtitle="Operações de microcrédito têm muitos contratos de valor baixo e alto volume de cobrança. O Kredor automatiza tudo para você crescer sem perder o controle."
    heroBullets={[
      'Alto volume de contratos organizados',
      'Cobrança recorrente automática no PIX e WhatsApp',
      'Indicadores de inadimplência da carteira',
      'Régua de cobrança padronizada e anti-spam',
    ]}
    blocks={[
      { icon: Layers, title: 'Volume não vira bagunça', text: 'Centenas de contratos ativos, cada um com suas parcelas e vencimentos, organizados em um painel único com filtros e busca rápida.' },
      { icon: Bell, title: 'Cobrança em escala', text: 'A régua dispara lembretes e cobranças para toda a carteira automaticamente, com o PIX na mensagem — sem equipe ligando cliente por cliente.' },
      { icon: Calculator, title: 'Cálculo padronizado', text: 'Defina o modelo de juros e o sistema gera as parcelas de forma consistente, aplicando encargos de atraso automaticamente.' },
      { icon: BarChart3, title: 'Visão da operação', text: 'Acompanhe inadimplência, recebimentos e desempenho por período para tomar decisões de crédito com dados.' },
      { icon: Repeat, title: 'Recorrência sem esforço', text: 'Clientes recorrentes são reaproveitados com histórico completo, agilizando novas liberações.' },
      { icon: ShieldCheck, title: 'Controle e segurança', text: 'Perfis de acesso, auditoria de ações e criptografia para operar em equipe com rastreabilidade.' },
    ]}
    differentials={[
      { title: 'Automação que segura o custo', text: 'Quanto mais contratos, mais a cobrança automática economiza tempo e reduz a necessidade de equipe.' },
      { title: 'Anti-spam nativo', text: 'Cadência de mensagens protegida para preservar o número de WhatsApp da operação.' },
      { title: 'Portal do cliente', text: 'Autoatendimento reduz o volume de contato e acelera o pagamento.' },
      { title: 'Relatórios exportáveis', text: 'PDF e Excel para conciliação e prestação de contas.' },
    ]}
    faq={[
      { q: 'O Kredor aguenta muitos contratos?', a: 'Sim. Ele foi pensado para carteiras com alto volume de contratos de baixo valor, típicas de microcrédito.' },
      { q: 'Dá para padronizar a cobrança de toda a carteira?', a: 'Sim. Você configura uma régua única e ela é aplicada automaticamente a todos os contratos elegíveis.' },
      { q: 'Consigo acompanhar a inadimplência geral?', a: 'Sim. O dashboard e os relatórios mostram inadimplência, recebimentos e desempenho por período.' },
      { q: 'Tem teste grátis?', a: 'Sim, 7 dias grátis e sem cartão de crédito.' },
    ]}
    related={[
      { to: '/gestao-carteira-credito', label: 'Gestão de carteira de crédito' },
      { to: '/software-para-emprestimos', label: 'Software para empréstimos' },
      { to: '/cobranca-whatsapp', label: 'Cobrança no WhatsApp' },
      { to: '/controle-de-parcelas-e-juros', label: 'Controle de parcelas e juros' },
      { to: '/precos', label: 'Ver preços' },
    ]}
  />
);

export default SistemaMicrocredito;
