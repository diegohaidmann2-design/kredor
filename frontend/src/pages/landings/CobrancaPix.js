import React from 'react';
import { QrCode, Zap, CheckCircle2, RefreshCw, Wallet, ShieldCheck } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const CobrancaPix = () => (
  <CommercialLanding
    seo={{
      title: 'Cobrança por PIX com baixa automática | Kredor',
      description: 'Gere PIX dinâmico para cada parcela e tenha baixa automática do pagamento. Envie a cobrança pelo WhatsApp e acompanhe os recebimentos em tempo real. Teste grátis.',
      path: '/cobranca-pix',
      image: '/og-cobranca-pix.jpg',
    }}
    eyebrow="PIX dinâmico + baixa automática"
    h1="Cobrança por PIX com baixa automática das parcelas"
    subtitle="Cada parcela gera um PIX próprio. Quando o cliente paga, o sistema reconhece e dá baixa sozinho — sem conferência manual de comprovante."
    heroBullets={[
      'PIX dinâmico individual por parcela',
      'Baixa automática ao receber o pagamento',
      'Envio do PIX direto pelo WhatsApp',
      'Status das parcelas atualizado em tempo real',
    ]}
    blocks={[
      { icon: QrCode, title: 'PIX dinâmico por parcela', text: 'Nada de chave única e conferência confusa. Cada cobrança tem seu próprio PIX, com valor e identificação, facilitando a conciliação.' },
      { icon: RefreshCw, title: 'Baixa automática', text: 'O pagamento é detectado e a parcela é marcada como paga automaticamente, mantendo sua carteira sempre atualizada.' },
      { icon: Zap, title: 'Recebimento na hora', text: 'PIX cai na hora. Você acompanha os recebimentos do dia em tempo real, sem esperar compensação.' },
      { icon: Wallet, title: 'Conciliação sem dor de cabeça', text: 'Cada valor recebido já está associado à parcela e ao cliente certos, eliminando erros de baixa manual.' },
      { icon: CheckCircle2, title: 'Menos inadimplência', text: 'Pagar fica fácil: o cliente recebe o PIX pronto no WhatsApp e quita em um toque, o que ajuda a reduzir atrasos.' },
      { icon: ShieldCheck, title: 'Registro completo', text: 'Todo pagamento fica registrado com data e valor, gerando histórico e recibo para o cliente.' },
    ]}
    differentials={[
      { title: 'Dinâmico, não estático', text: 'PIX por parcela (dinâmico) evita a bagunça de uma chave única recebendo valores soltos.' },
      { title: 'Fluxo ponta a ponta', text: 'Gera o PIX, envia no WhatsApp e dá baixa — tudo dentro do mesmo sistema.' },
      { title: 'Recibo automático', text: 'Após o pagamento, o comprovante fica disponível para envio ao cliente.' },
      { title: 'Visão de caixa', text: 'Acompanhe o que entrou hoje e o que ainda está previsto, com clareza.' },
    ]}
    faq={[
      { q: 'O que é PIX dinâmico?', a: 'É um PIX gerado especificamente para cada cobrança, com valor e identificação próprios. Isso facilita a baixa automática e a conciliação, diferente de uma chave PIX única que recebe valores soltos.' },
      { q: 'A baixa é mesmo automática?', a: 'Sim. Ao identificar o pagamento, o sistema marca a parcela como paga e atualiza o status, sem você precisar conferir comprovante no extrato.' },
      { q: 'Preciso de maquininha?', a: 'Não. A cobrança é feita por PIX, enviado ao cliente pelo WhatsApp ou pelo portal do cliente. Não há taxa de maquininha nem aluguel de equipamento.' },
      { q: 'Como o PIX ajuda a reduzir a inadimplência?', a: 'Quando o cliente recebe o PIX pronto na mensagem, ele paga em um toque. Facilitar o pagamento é uma das formas mais eficazes de diminuir atrasos.' },
      { q: 'Consigo emitir recibo do pagamento?', a: 'Sim. Todo pagamento fica registrado com data e valor, e o sistema disponibiliza o recibo em PDF para envio ao cliente.' },
      { q: 'O PIX funciona junto com a cobrança no WhatsApp?', a: 'Sim. A cobrança e o recebimento andam juntos: a régua de mensagens no WhatsApp já envia o PIX daquela parcela, e a baixa acontece automaticamente quando o cliente paga.' },
    ]}
    related={[
      { to: '/cobranca-whatsapp', label: 'Cobrança no WhatsApp' },
      { to: '/sistema-gestao-emprestimos', label: 'Sistema de gestão de empréstimos' },
      { to: '/gestao-de-clientes', label: 'Gestão de clientes' },
      { to: '/precos', label: 'Ver preços' },
    ]}
    ctaTitle="Receba por PIX com baixa automática"
    ctaText="Teste grátis por 7 dias e veja os pagamentos entrarem sozinhos na carteira."
  >
    {({ isDark }) => (
      <p className={`text-base leading-relaxed ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
        A cobrança por PIX é o coração de um bom <strong>sistema de empréstimos e cobranças</strong>:
        em vez de repassar uma chave única e conferir o extrato no fim do dia, cada parcela ganha um
        PIX dinâmico próprio, com valor e identificação. Quando o cliente paga, a baixa é automática
        e a sua carteira de crédito fica atualizada em tempo real — sem conferência manual e sem
        erro de conciliação.
      </p>
    )}
  </CommercialLanding>
);

export default CobrancaPix;
