import React from 'react';
import { FileText, ShieldCheck, PenLine, Download, Scale, Clock } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const ContratosDigitaisCCB = () => (
  <CommercialLanding
    seo={{
      title: 'Contratos digitais e CCB para empréstimos | Kredor',
      description: 'Gere contratos digitais e CCB (Cédula de Crédito Bancário) e recibos em PDF automaticamente para cada empréstimo. Formalize suas operações. Teste 7 dias grátis.',
      path: '/contratos-digitais-ccb',
      image: '/og-image-kredor.jpg',
    }}
    eyebrow="Formalização"
    h1="Contratos digitais e CCB gerados automaticamente para cada empréstimo"
    subtitle="Dê respaldo jurídico às suas operações: o Kredor preenche e gera contratos e recibos em PDF com os dados do empréstimo, prontos para enviar ao cliente."
    heroBullets={[
      'Contratos (CCB) preenchidos automaticamente',
      'Recibos de pagamento em PDF',
      'Dados do empréstimo sempre corretos',
      'Envio rápido para o cliente',
    ]}
    blocks={[
      { icon: FileText, title: 'Contrato pronto em segundos', text: 'A partir dos dados do empréstimo (valor, prazo, juros e parcelas), o sistema monta o contrato completo — sem copiar e colar e sem erro de digitação.' },
      { icon: Scale, title: 'Respaldo para a operação', text: 'A Cédula de Crédito Bancário (CCB) e os contratos digitais dão formalidade e segurança à relação entre você e o cliente.' },
      { icon: Download, title: 'PDF pronto para enviar', text: 'Baixe ou compartilhe o documento em PDF direto para o WhatsApp ou e-mail do cliente.' },
      { icon: PenLine, title: 'Recibos automáticos', text: 'Cada pagamento gera um recibo em PDF, mantendo o histórico documentado da quitação.' },
      { icon: Clock, title: 'Menos tempo em burocracia', text: 'O que levava minutos por contrato passa a ser um clique, liberando você para o que importa: emprestar e receber.' },
      { icon: ShieldCheck, title: 'Documentos organizados', text: 'Todos os contratos e recibos ficam vinculados ao empréstimo e ao cliente, fáceis de localizar quando precisar.' },
    ]}
    differentials={[
      { title: 'Integrado à operação', text: 'O contrato nasce do próprio empréstimo cadastrado — nada é redigitado.' },
      { title: 'Recibo a cada pagamento', text: 'A quitação é documentada automaticamente, protegendo as duas partes.' },
      { title: 'Compartilhamento fácil', text: 'Envie o PDF pelo WhatsApp em segundos.' },
      { title: 'Histórico completo', text: 'Documentos sempre acessíveis por cliente e por contrato.' },
    ]}
    faq={[
      { q: 'O que é uma CCB?', a: 'A Cédula de Crédito Bancário (CCB) é um título de crédito que representa uma promessa de pagamento. É usada para formalizar operações de empréstimo e dar respaldo à cobrança.' },
      { q: 'O contrato já vem preenchido?', a: 'Sim. O Kredor usa os dados do empréstimo (valor, prazo, juros e parcelas) para preencher o documento automaticamente.' },
      { q: 'Consigo enviar o contrato para o cliente?', a: 'Sim. O documento é gerado em PDF e pode ser baixado ou compartilhado pelo WhatsApp e e-mail.' },
      { q: 'O Kredor substitui a orientação jurídica?', a: 'Não. Ele agiliza a geração dos documentos; para dúvidas específicas do seu caso, consulte um advogado.' },
    ]}
    related={[
      { to: '/sistema-para-credores', label: 'Sistema para credores' },
      { to: '/software-para-emprestimos', label: 'Software para empréstimos' },
      { to: '/controle-de-parcelas-e-juros', label: 'Controle de parcelas e juros' },
      { to: '/gestao-de-clientes', label: 'Gestão de clientes' },
      { to: '/precos', label: 'Ver preços' },
    ]}
  />
);

export default ContratosDigitaisCCB;
