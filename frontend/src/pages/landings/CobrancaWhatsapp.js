import React from 'react';
import { MessageCircle, Bell, ShieldCheck, Clock, Repeat, Link2 } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const CobrancaWhatsapp = () => (
  <CommercialLanding
    seo={{
      title: 'Cobrança automática no WhatsApp | Régua de cobrança | Kredor',
      description: 'Automatize a cobrança no WhatsApp com régua de mensagens antes e depois do vencimento, proteção anti-spam e link de pagamento PIX. Recupere crédito com menos esforço.',
      path: '/cobranca-whatsapp',
      image: '/og-cobranca-whatsapp.jpg',
    }}
    eyebrow="Régua de cobrança automática"
    h1="Cobrança automática no WhatsApp para reduzir a inadimplência"
    subtitle="Configure uma régua de mensagens e deixe o sistema lembrar cada cliente no momento certo — antes e depois do vencimento — com link de pagamento PIX incluído."
    heroBullets={[
      'Lembretes automáticos antes do vencimento',
      'Cobranças após o atraso, sem você precisar digitar',
      'Mensagens personalizáveis com nome, valor e vencimento',
      'Proteção anti-spam para preservar seu número',
    ]}
    blocks={[
      { icon: Repeat, title: 'Régua configurável', text: 'Defina quando cada mensagem sai (ex.: 3 dias antes, no dia, 1 e 7 dias após o vencimento). O sistema executa a sequência automaticamente para toda a carteira.' },
      { icon: Bell, title: 'Lembretes que evitam esquecimento', text: 'A maioria dos atrasos acontece por esquecimento. Lembretes educados no WhatsApp aumentam a chance de pagamento em dia.' },
      { icon: Link2, title: 'Link de PIX na mensagem', text: 'Cada cobrança já vai com o PIX daquela parcela. O cliente paga em um toque e a baixa é automática.' },
      { icon: ShieldCheck, title: 'Anti-spam integrado', text: 'Controle de frequência e limites para evitar excesso de mensagens e reduzir o risco de bloqueio do seu número.' },
      { icon: Clock, title: 'Economia de tempo', text: 'Pare de mandar mensagem uma a uma. A cobrança roda sozinha enquanto você cuida do resto do negócio.' },
      { icon: MessageCircle, title: 'Tom profissional', text: 'Modelos de mensagem prontos, com linguagem respeitosa e profissional, fortalecendo a relação com o cliente.' },
    ]}
    differentials={[
      { title: 'Automação de verdade', text: 'Não é só um botão de enviar: é uma régua que dispara a mensagem certa, na hora certa, para cada parcela.' },
      { title: 'Integrada ao PIX dinâmico', text: 'A cobrança e o recebimento andam juntos — mensagem, link e baixa automática no mesmo fluxo.' },
      { title: 'Histórico de envios', text: 'Acompanhe o que foi enviado para cada cliente, mantendo registro de toda a comunicação de cobrança.' },
      { title: 'Personalização por cliente', text: 'Variáveis automáticas inserem nome, valor e data em cada mensagem, sem trabalho manual.' },
    ]}
    faq={[
      { q: 'A cobrança é realmente automática?', a: 'Sim. Depois de configurar a régua, o sistema envia as mensagens nos momentos definidos, sem intervenção manual.' },
      { q: 'Corro risco de bloqueio no WhatsApp?', a: 'O Kredor tem proteção anti-spam com limites de frequência para reduzir esse risco. Ainda assim, recomendamos mensagens moderadas e respeitosas.' },
      { q: 'Posso personalizar as mensagens?', a: 'Sim. Você edita os modelos e usa variáveis como nome, valor e vencimento, mantendo um tom profissional.' },
    ]}
    related={[
      { to: '/cobranca-pix', label: 'Cobrança por PIX' },
      { to: '/sistema-gestao-emprestimos', label: 'Sistema de gestão de empréstimos' },
      { to: '/controle-de-parcelas-e-juros', label: 'Controle de parcelas e juros' },
      { to: '/precos', label: 'Ver preços' },
    ]}
    ctaTitle="Deixe a cobrança no automático"
    ctaText="Configure sua régua no WhatsApp e teste grátis por 7 dias."
  />
);

export default CobrancaWhatsapp;
