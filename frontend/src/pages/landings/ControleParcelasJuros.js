import React from 'react';
import { Calculator, Percent, CalendarClock, TrendingDown, FileText, RefreshCw } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';
import JurosCalculator from '../../components/JurosCalculator';

const ControleParcelasJuros = () => (
  <CommercialLanding
    seo={{
      title: 'Controle de parcelas e cálculo de juros (Price, SAC) | GestorCred',
      description: 'Calcule juros simples, compostos, Tabela Price e SAC e controle todas as parcelas automaticamente, com multa e juros de mora em atrasos. Use a calculadora grátis.',
      path: '/controle-de-parcelas-e-juros',
    }}
    eyebrow="Parcelas e juros automáticos"
    h1="Controle de parcelas e cálculo de juros sem erro"
    subtitle="Escolha o método de cálculo (simples, composto, Tabela Price ou SAC), gere todas as parcelas automaticamente e acompanhe cada vencimento. Multa e juros de mora aplicados sozinhos."
    heroBullets={[
      'Juros simples, compostos, Tabela Price e SAC',
      'Geração automática de todas as parcelas',
      'Multa e juros de mora em atrasos',
      'Prorrogação com recálculo do saldo devedor',
    ]}
    blocks={[
      { icon: Calculator, title: 'Quatro métodos de cálculo', text: 'Trabalhe do jeito que faz sentido para você: juros simples, compostos, Tabela Price (parcela fixa) ou SAC (amortização constante).' },
      { icon: CalendarClock, title: 'Parcelas e vencimentos', text: 'O sistema cria o cronograma completo de parcelas com datas de vencimento e mostra o que vence hoje, o que está em aberto e o que já foi pago.' },
      { icon: Percent, title: 'Multa e mora automáticas', text: 'Em atrasos, o sistema aplica multa e juros de mora conforme a sua configuração, sem cálculo manual.' },
      { icon: RefreshCw, title: 'Prorrogação inteligente', text: 'Precisou estender o prazo? A prorrogação mantém as parcelas pagas e re-amortiza o saldo devedor nas novas parcelas, com prévia antes de confirmar.' },
      { icon: FileText, title: 'Recibos e comprovantes', text: 'Gere recibos em PDF de pagamentos e de prorrogação, prontos para enviar ao cliente.' },
      { icon: TrendingDown, title: 'Visão do saldo', text: 'Acompanhe o saldo devedor de cada operação e o total a receber da carteira em tempo real.' },
    ]}
    differentials={[
      { title: 'SAC e Price nativos', text: 'Métodos que apps simples não oferecem, calculados corretamente e com cronograma completo.' },
      { title: 'Prorrogação com prévia', text: 'Veja o novo valor de cada parcela e o total antes de confirmar a prorrogação.' },
      { title: 'Automação de multa/mora', text: 'Nada de recalcular no papel: o sistema cuida dos encargos de atraso.' },
      { title: 'Histórico por parcela', text: 'Cada parcela guarda pagamentos, encargos e status, com trilha completa.' },
    ]}
    faq={[
      { q: 'Qual a diferença entre Price e SAC?', a: 'Na Tabela Price a parcela é fixa do início ao fim. No SAC a amortização é constante e a parcela começa maior e diminui ao longo do tempo.' },
      { q: 'O sistema calcula multa e juros de mora?', a: 'Sim. Você define as taxas e o GestorCred aplica automaticamente sobre parcelas em atraso.' },
      { q: 'A calculadora acima serve para quê?', a: 'É uma simulação educativa. Dentro do sistema, o cálculo é feito automaticamente e já gera todas as parcelas da operação.' },
    ]}
    related={[
      { to: '/sistema-gestao-emprestimos', label: 'Sistema de gestão de empréstimos' },
      { to: '/cobranca-pix', label: 'Cobrança por PIX' },
      { to: '/cobranca-whatsapp', label: 'Cobrança no WhatsApp' },
      { to: '/precos', label: 'Ver preços' },
    ]}
    ctaTitle="Pare de calcular juros na mão"
    ctaText="Deixe o sistema gerar as parcelas e os encargos. Teste grátis por 7 dias."
  >
    {({ isDark }) => <JurosCalculator isDark={isDark} />}
  </CommercialLanding>
);

export default ControleParcelasJuros;
