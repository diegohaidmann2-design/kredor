import React from 'react';
import { Wallet, Calculator, Bell, BarChart3, FileText, Users } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const SistemaGestaoEmprestimos = () => (
  <CommercialLanding
    seo={{
      title: 'Sistema de empréstimos e cobranças online | Kredor',
      description: 'Sistema de empréstimos e cobranças para credores: controle de clientes, parcelas e juros, cobrança automática no PIX e WhatsApp e relatórios da carteira de crédito. Teste grátis por 7 dias.',
      path: '/sistema-gestao-emprestimos',
      image: '/og-sistema-gestao-emprestimos.jpg',
    }}
    eyebrow="Gestão de crédito profissional"
    h1="Sistema de empréstimos e cobranças para organizar sua carteira de crédito"
    subtitle="Controle clientes, parcelas e juros e automatize as cobranças no PIX e no WhatsApp. Um sistema de empréstimos e cobranças completo para substituir o caderninho e a planilha — com acompanhamento em tempo real."
    heroBullets={[
      'Cadastro de clientes e histórico de crédito',
      'Cálculo automático de juros e geração de parcelas',
      'Cobrança por PIX e régua no WhatsApp',
      'Dashboard financeiro e relatórios em PDF/Excel',
    ]}
    blocks={[
      { icon: Users, title: 'Carteira de clientes organizada', text: 'Centralize dados, contatos e o histórico de cada cliente. Consulte tudo em segundos e acompanhe quem está em dia e quem precisa de atenção.' },
      { icon: Calculator, title: 'Parcelas e juros sem erro', text: 'O sistema calcula juros simples, compostos, Tabela Price e SAC, gera todas as parcelas e aplica multa e juros de mora automaticamente em atrasos.' },
      { icon: Wallet, title: 'Recebíveis sob controle', text: 'Veja o total a receber, vencimentos do dia, valores em aberto e projeções de caixa. Decisões baseadas em dados, não em anotações soltas.' },
      { icon: Bell, title: 'Cobrança automatizada', text: 'Lembretes antes do vencimento e cobranças após o atraso são enviados automaticamente, reduzindo esquecimentos e melhorando a recuperação de crédito.' },
      { icon: FileText, title: 'Contratos e recibos', text: 'Gere contratos digitais (CCB) e recibos em PDF prontos para enviar, dando formalidade e segurança a cada operação.' },
      { icon: BarChart3, title: 'Relatórios que ajudam a decidir', text: 'Relatórios de inadimplência, faturamento e desempenho da carteira exportáveis para PDF e Excel.' },
    ]}
    differentials={[
      { title: 'PIX dinâmico com baixa automática', text: 'Cada cobrança gera um PIX próprio e o pagamento é reconhecido automaticamente, sem conferência manual.' },
      { title: 'Régua de cobrança no WhatsApp', text: 'Sequência de mensagens automáticas com proteção anti-spam — algo que planilhas e apps simples não oferecem.' },
      { title: 'Portal do cliente', text: 'Seu cliente acompanha as próprias parcelas e realiza pagamentos por autoatendimento.' },
      { title: 'Assistente com IA', text: 'Insights e apoio à operação com inteligência artificial integrada ao seu dia a dia.' },
    ]}
    faq={[
      { q: 'O que é um sistema de empréstimos e cobranças?', a: 'É um software que reúne em um só lugar o cadastro de clientes, o cálculo de juros, a geração de parcelas e a cobrança dos valores a receber. No Kredor, a cobrança ainda é automatizada por PIX e WhatsApp, reduzindo a inadimplência.' },
      { q: 'O sistema faz a cobrança automaticamente?', a: 'Sim. Você configura uma régua de cobrança e o Kredor envia lembretes antes do vencimento e avisos após o atraso por WhatsApp, além de gerar cobranças via PIX com baixa automática.' },
      { q: 'Dá para controlar juros, multa e mora por atraso?', a: 'Sim. Além de juros simples, compostos, Tabela Price e SAC, o sistema aplica multa e juros de mora automaticamente nas parcelas em atraso.' },
      { q: 'Preciso instalar algo?', a: 'Não. O Kredor é um sistema online (web). Você acessa pelo navegador, no computador ou no celular.' },
      { q: 'Serve para quem empresta como pessoa física?', a: 'Sim. É indicado para credores particulares e microcrédito que querem profissionalizar o controle da carteira, sem caderninho e sem planilha.' },
      { q: 'Consigo migrar meus dados atuais?', a: 'Você cadastra seus clientes e empréstimos ativos rapidamente e passa a acompanhar tudo pelo sistema a partir daí.' },
    ]}
    related={[
      { to: '/cobranca-pix', label: 'Cobrança por PIX' },
      { to: '/cobranca-whatsapp', label: 'Cobrança no WhatsApp' },
      { to: '/controle-de-parcelas-e-juros', label: 'Controle de parcelas e juros' },
      { to: '/gestao-de-clientes', label: 'Gestão de clientes' },
      { to: '/precos', label: 'Ver preços' },
    ]}
  >
    {({ isDark }) => (
      <p className={`text-base leading-relaxed ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
        O Kredor é um <strong>sistema de empréstimos e cobranças</strong> feito para credores
        particulares, microcrédito e escritórios de cobrança. Em um só lugar você cadastra clientes,
        calcula os juros, gera as parcelas e acompanha os recebíveis — enquanto as cobranças saem
        automaticamente por PIX e WhatsApp, reduzindo a inadimplência sem trabalho manual e sem a
        confusão do caderninho ou da planilha.
      </p>
    )}
  </CommercialLanding>
);

export default SistemaGestaoEmprestimos;
