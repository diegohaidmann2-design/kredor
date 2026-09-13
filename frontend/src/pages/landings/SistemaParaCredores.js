import React from 'react';
import { Users, Bell, Wallet, ShieldCheck, Smartphone, Gauge } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const SistemaParaCredores = () => (
  <CommercialLanding
    seo={{
      title: 'Sistema para credores particulares | Kredor',
      description: 'Sistema para credores particulares organizarem a carteira, cobrarem no automático (PIX e WhatsApp) e reduzirem o calote. Contratos CCB e portal do cliente. Teste grátis.',
      path: '/sistema-para-credores',
      image: '/og-image-kredor.jpg',
    }}
    eyebrow="Feito para quem empresta"
    h1="Sistema para credores que querem emprestar com segurança e receber em dia"
    subtitle="Se você empresta dinheiro por conta própria, o Kredor organiza sua carteira, cobra sozinho e formaliza cada operação — para você parar de perder dinheiro com calote e desorganização."
    heroBullets={[
      'Controle de quem deve, quanto e quando vence',
      'Cobrança automática no PIX e WhatsApp',
      'Contratos digitais (CCB) e recibos em PDF',
      'Análise de CPF e score antes de liberar',
    ]}
    blocks={[
      { icon: Users, title: 'Cada cliente sob controle', text: 'Cadastro completo com histórico, contatos e situação. Saiba na hora quem está em dia, quem atrasou e quem merece um novo empréstimo.' },
      { icon: Bell, title: 'Cobre sem constrangimento', text: 'A régua envia lembretes e cobranças educadas pelo WhatsApp, com o PIX na mensagem. Você recupera crédito sem desgaste e sem ficar ligando.' },
      { icon: Wallet, title: 'Receba mais rápido', text: 'PIX dinâmico com baixa automática: o pagamento cai e a parcela é quitada sozinha, sem você conferir extrato.' },
      { icon: ShieldCheck, title: 'Empreste formalizado', text: 'Gere contratos (CCB) e recibos que dão respaldo jurídico à operação — proteção que caderninho nenhum oferece.' },
      { icon: Gauge, title: 'Aprove com critério', text: 'Consulte CPF e veja o score do cliente antes de liberar, reduzindo o risco de inadimplência já na origem.' },
      { icon: Smartphone, title: 'Do bolso, de onde estiver', text: 'Tudo no navegador do celular ou computador: acompanhe a carteira e cobre mesmo fora de casa.' },
    ]}
    differentials={[
      { title: 'Pensado para o credor pequeno', text: 'Sem complexidade de ERP corporativo: simples de usar, focado em quem empresta por conta própria.' },
      { title: 'PIX + WhatsApp integrados', text: 'A cobrança sai automática com o link de pagamento, do jeito que seu cliente já está acostumado.' },
      { title: 'Portal do cliente', text: 'Ele mesmo consulta as parcelas e paga sozinho, 24h por dia.' },
      { title: 'Dados protegidos', text: 'Criptografia e boas práticas de LGPD para você operar com segurança e responsabilidade.' },
    ]}
    faq={[
      { q: 'Preciso ter CNPJ para usar?', a: 'Não. O Kredor funciona para pessoa física (credor particular) e também para quem tem empresa. Ele organiza e cobra; a decisão de emprestar é sua.' },
      { q: 'É legal usar um sistema desse?', a: 'Sim. O Kredor é um software de gestão e cobrança. Ele ajuda você a formalizar operações com contratos e recibos e a manter tudo organizado.' },
      { q: 'Consigo controlar vários clientes ao mesmo tempo?', a: 'Sim. A carteira mostra todos os clientes, parcelas e vencimentos em um painel único, com filtros por situação.' },
      { q: 'Tem teste grátis?', a: 'Sim, 7 dias grátis, sem cartão de crédito.' },
    ]}
    related={[
      { to: '/software-para-emprestimos', label: 'Software para empréstimos' },
      { to: '/emprestimo-particular-como-organizar', label: 'Como organizar empréstimo particular' },
      { to: '/consulta-cpf-credito', label: 'Consulta de CPF para crédito' },
      { to: '/contratos-digitais-ccb', label: 'Contratos digitais (CCB)' },
      { to: '/precos', label: 'Ver preços' },
    ]}
  />
);

export default SistemaParaCredores;
