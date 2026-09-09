import React from 'react';
import { Users, IdCard, History, Search, ShieldCheck, LayoutDashboard } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const GestaoDeClientes = () => (
  <CommercialLanding
    seo={{
      title: 'Gestão de clientes e carteira de crédito (CRM) | Kredor',
      description: 'Organize sua carteira de clientes: dados completos, histórico de crédito, validação de CPF para análise e portal do cliente. Um CRM feito para quem gere crédito.',
      path: '/gestao-de-clientes',
      image: '/og-gestao-de-clientes.jpg',
    }}
    eyebrow="Carteira de clientes (CRM)"
    h1="Gestão de clientes e da sua carteira de crédito"
    subtitle="Tenha o cadastro completo de cada cliente, o histórico de empréstimos e o comportamento de pagamento em um só lugar — a base para decisões de crédito melhores."
    heroBullets={[
      'Cadastro com dados completos e busca de CEP',
      'Histórico de crédito e de pagamentos por cliente',
      'Validação de CPF para análise de crédito',
      'Portal do cliente com autoatendimento',
    ]}
    blocks={[
      { icon: Users, title: 'Cadastro centralizado', text: 'Reúna dados de contato, documentos e endereço de cada cliente, com busca automática de CEP e organização por situação.' },
      { icon: History, title: 'Histórico de relacionamento', text: 'Veja todos os empréstimos, pagamentos e atrasos de um cliente para entender o comportamento e definir limites com segurança.' },
      { icon: IdCard, title: 'Validação de dados (CPF)', text: 'Consulte e valide dados cadastrais para a análise de crédito, com apoio à conformidade com a LGPD. Uma etapa de validação — não de perseguição.' },
      { icon: LayoutDashboard, title: 'Portal do cliente', text: 'Cada cliente acessa suas parcelas, comprovantes e pagamentos por autoatendimento, reduzindo o volume de mensagens para você.' },
      { icon: Search, title: 'Encontre tudo rápido', text: 'Filtre e pesquise por nome, situação ou documento e chegue à informação em segundos.' },
      { icon: ShieldCheck, title: 'Score e análise de risco', text: 'Score de crédito e sinais de risco ajudam a decidir com mais critério antes de conceder uma nova operação.' },
    ]}
    differentials={[
      { title: 'CRM voltado a crédito', text: 'Não é uma agenda genérica: é uma carteira pensada para quem controla empréstimos e recebíveis.' },
      { title: 'Portal do cliente', text: 'Autoatendimento que profissionaliza a relação e reduz o trabalho de suporte.' },
      { title: 'Validação com LGPD em mente', text: 'A consulta de dados é enquadrada como validação para análise de crédito, com respeito à privacidade.' },
      { title: 'Visão 360º do cliente', text: 'Cadastro, histórico, parcelas e comunicação reunidos em uma única tela.' },
    ]}
    faq={[
      { q: 'A consulta de CPF serve para quê?', a: 'Para validar os dados cadastrais do cliente na etapa de análise de crédito, apoiando a conformidade com a LGPD. É uma validação de dados, não uma ferramenta de perseguição.' },
      { q: 'Meus clientes acessam algo?', a: 'Sim. Pelo portal do cliente, cada pessoa acompanha suas próprias parcelas e realiza pagamentos por conta própria.' },
      { q: 'Consigo separar clientes em dia e em atraso?', a: 'Sim. A carteira mostra a situação de cada cliente e permite filtrar por status de pagamento.' },
    ]}
    related={[
      { to: '/sistema-gestao-emprestimos', label: 'Sistema de gestão de empréstimos' },
      { to: '/cobranca-whatsapp', label: 'Cobrança no WhatsApp' },
      { to: '/seguranca', label: 'Segurança e LGPD' },
      { to: '/precos', label: 'Ver preços' },
    ]}
    ctaTitle="Organize sua carteira de clientes"
    ctaText="Centralize dados, histórico e cobranças. Teste grátis por 7 dias."
  />
);

export default GestaoDeClientes;
