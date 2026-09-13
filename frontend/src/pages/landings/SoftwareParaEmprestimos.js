import React from 'react';
import { Wallet, Calculator, Bell, BarChart3, FileText, ShieldCheck } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const SoftwareParaEmprestimos = () => (
  <CommercialLanding
    seo={{
      title: 'Software para empréstimos: cobrança PIX e WhatsApp | Kredor',
      description: 'Software para empréstimos com cobrança automática no PIX e WhatsApp, contratos CCB e controle de parcelas e juros. Reduza a inadimplência. Teste 7 dias grátis.',
      path: '/software-para-emprestimos',
      image: '/og-image-kredor.jpg',
    }}
    eyebrow="Software de crédito"
    h1="Software para empréstimos que cobra sozinho e reduz a inadimplência"
    subtitle="Troque o caderninho e a planilha por um software completo: controle de parcelas e juros, cobrança automática no PIX e WhatsApp, contratos digitais e portal do cliente — tudo em um só lugar."
    heroBullets={[
      'Baixa automática de pagamentos via PIX dinâmico',
      'Régua de cobrança no WhatsApp com anti-spam',
      'Cálculo de juros Price, SAC, simples e composto',
      'Contratos CCB e recibos em PDF automáticos',
    ]}
    blocks={[
      { icon: Wallet, title: 'Toda a carteira em um lugar', text: 'Clientes, empréstimos, parcelas e recebíveis organizados. Veja o que vence hoje, o que está em aberto e quanto você tem a receber, em tempo real.' },
      { icon: Bell, title: 'Cobrança no piloto automático', text: 'O software envia lembretes antes do vencimento e cobranças após o atraso pelo WhatsApp, com o PIX dentro da mensagem — você recupera crédito sem ligar para ninguém.' },
      { icon: Calculator, title: 'Juros e parcelas sem erro', text: 'Escolha o método de cálculo, defina taxa e prazo e o software gera todas as parcelas, aplicando multa e juros de mora automaticamente em atrasos.' },
      { icon: FileText, title: 'Formalização em segundos', text: 'Gere contratos digitais (CCB) e recibos em PDF prontos para enviar, dando segurança jurídica a cada operação.' },
      { icon: BarChart3, title: 'Decisões baseadas em dados', text: 'Dashboard financeiro e relatórios de inadimplência, faturamento e desempenho da carteira exportáveis em PDF e Excel.' },
      { icon: ShieldCheck, title: 'Seguro e multiusuário', text: 'Login com 2FA, criptografia de dados sensíveis e permissões por perfil para operar em equipe com controle.' },
    ]}
    differentials={[
      { title: 'PIX dinâmico com baixa automática', text: 'Cada cobrança gera um PIX próprio e o pagamento é reconhecido sozinho, sem conferência manual.' },
      { title: 'Régua de cobrança no WhatsApp', text: 'Sequência de mensagens automáticas com proteção anti-spam que apps simples e planilhas não têm.' },
      { title: 'Portal do cliente', text: 'O cliente consulta parcelas e paga por autoatendimento 24h, reduzindo ligações e atrito.' },
      { title: 'Análise de CPF e score', text: 'Valide dados e avalie o risco antes de aprovar, com tratamento conforme a LGPD.' },
    ]}
    faq={[
      { q: 'Preciso instalar algum programa?', a: 'Não. É um software 100% online (web): você acessa pelo navegador no computador ou no celular.' },
      { q: 'O Kredor empresta dinheiro?', a: 'Não. É uma ferramenta de gestão e cobrança. Quem empresta é você; o software organiza a carteira e automatiza a cobrança.' },
      { q: 'Serve para quem empresta como pessoa física?', a: 'Sim. É ideal para credores particulares e microcrédito que querem profissionalizar o controle sem planilha.' },
      { q: 'Tem teste grátis?', a: 'Sim, 7 dias grátis e sem cartão de crédito, com acesso às funcionalidades essenciais.' },
    ]}
    related={[
      { to: '/sistema-gestao-emprestimos', label: 'Sistema de gestão de empréstimos' },
      { to: '/sistema-para-credores', label: 'Sistema para credores' },
      { to: '/cobranca-pix', label: 'Cobrança por PIX' },
      { to: '/controle-de-parcelas-e-juros', label: 'Controle de parcelas e juros' },
      { to: '/precos', label: 'Ver preços' },
    ]}
  />
);

export default SoftwareParaEmprestimos;
