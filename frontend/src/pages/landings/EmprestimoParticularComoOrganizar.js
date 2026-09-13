import React from 'react';
import { ClipboardList, Bell, Calculator, FileText, ShieldCheck, Wallet } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const EmprestimoParticularComoOrganizar = () => (
  <CommercialLanding
    seo={{
      title: 'Empréstimo particular: como organizar e cobrar | Kredor',
      description: 'Como organizar empréstimo particular sem planilha: controle parcelas e juros, formalize com contrato e cobre no automático pelo PIX e WhatsApp. Teste 7 dias grátis.',
      path: '/emprestimo-particular-como-organizar',
      image: '/og-image-kredor.jpg',
    }}
    eyebrow="Guia prático"
    h1="Empréstimo particular: como organizar, formalizar e receber em dia"
    subtitle="Emprestar dinheiro por conta própria não precisa virar dor de cabeça. Veja como sair do caderninho e da planilha e passar a controlar, formalizar e cobrar de forma automática."
    heroBullets={[
      'Registre cada empréstimo com prazo e juros',
      'Formalize com contrato (CCB) e recibos',
      'Cobre no automático pelo PIX e WhatsApp',
      'Acompanhe quem está em dia e quem atrasou',
    ]}
    blocks={[
      { icon: ClipboardList, title: '1. Registre a operação', text: 'Cadastre o cliente, o valor emprestado, o prazo e a taxa. O sistema gera as parcelas automaticamente — sem contas manuais.' },
      { icon: FileText, title: '2. Formalize', text: 'Gere um contrato digital (CCB) e um recibo para cada pagamento. Isso protege você e deixa claro o combinado com o cliente.' },
      { icon: Calculator, title: '3. Deixe os juros no automático', text: 'Escolha juros simples, compostos, Price ou SAC. Multa e juros de mora em atrasos são aplicados sozinhos.' },
      { icon: Bell, title: '4. Cobre sem estresse', text: 'Ative a régua de cobrança: lembretes antes do vencimento e avisos após o atraso saem pelo WhatsApp, com o PIX na mensagem.' },
      { icon: Wallet, title: '5. Receba e dê baixa sozinho', text: 'Com PIX dinâmico, o pagamento é reconhecido automaticamente e a parcela é quitada sem você conferir extrato.' },
      { icon: ShieldCheck, title: '6. Tenha tudo à mão', text: 'Histórico, documentos e situação de cada cliente organizados para consultar em segundos.' },
    ]}
    differentials={[
      { title: 'Sai da planilha de vez', text: 'Você para de depender de anotações soltas e passa a ter uma carteira organizada e confiável.' },
      { title: 'Cobrança educada e automática', text: 'Recupere crédito sem ligar e sem constranger o cliente.' },
      { title: 'Formalização simples', text: 'Contrato e recibo em PDF em poucos cliques.' },
      { title: 'Decisões melhores', text: 'Consulta de CPF e score ajudam a decidir a quem emprestar.' },
    ]}
    faq={[
      { q: 'Preciso entender de finanças para usar?', a: 'Não. Você informa valor, prazo e taxa, e o Kredor calcula tudo e gera as parcelas. É pensado para quem empresta, não para especialistas.' },
      { q: 'Como cobrar sem brigar com o cliente?', a: 'A régua envia lembretes educados e automáticos pelo WhatsApp, com o link de pagamento PIX. A cobrança fica profissional e sem desgaste.' },
      { q: 'Vale a pena fazer contrato em empréstimo pequeno?', a: 'Sim. O contrato e o recibo dão respaldo e evitam desentendimentos, mesmo em valores baixos — e no Kredor eles são gerados automaticamente.' },
      { q: 'Tem teste grátis?', a: 'Sim, 7 dias grátis e sem cartão de crédito.' },
    ]}
    related={[
      { to: '/sistema-para-credores', label: 'Sistema para credores' },
      { to: '/contratos-digitais-ccb', label: 'Contratos digitais (CCB)' },
      { to: '/controle-de-parcelas-e-juros', label: 'Controle de parcelas e juros' },
      { to: '/cobranca-whatsapp', label: 'Cobrança no WhatsApp' },
      { to: '/precos', label: 'Ver preços' },
    ]}
  />
);

export default EmprestimoParticularComoOrganizar;
