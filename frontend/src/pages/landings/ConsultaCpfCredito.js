import React from 'react';
import { Search, Gauge, ShieldCheck, UserCheck, AlertTriangle, FileText } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const ConsultaCpfCredito = () => (
  <CommercialLanding
    seo={{
      title: 'Consulta de CPF para análise de crédito | Kredor',
      description: 'Consulte CPF e avalie o risco antes de emprestar: validação de dados e score de crédito integrados à gestão da carteira, com tratamento conforme a LGPD. Teste grátis.',
      path: '/consulta-cpf-credito',
      image: '/og-image-kredor.jpg',
    }}
    eyebrow="Análise de crédito"
    h1="Consulta de CPF para decidir a quem emprestar com segurança"
    subtitle="Antes de liberar o empréstimo, valide os dados do cliente e avalie o risco. No Kredor, a consulta de CPF e o score ficam integrados à gestão da sua carteira de crédito."
    heroBullets={[
      'Validação de dados do cliente por CPF',
      'Score de crédito para apoiar a decisão',
      'Análise integrada à carteira e ao histórico',
      'Tratamento de dados conforme a LGPD',
    ]}
    blocks={[
      { icon: Search, title: 'Confirme quem é o cliente', text: 'Valide os dados cadastrais pelo CPF e reduza fraudes e erros logo na entrada, antes de comprometer seu dinheiro.' },
      { icon: Gauge, title: 'Meça o risco com score', text: 'Uma classificação de risco ajuda a decidir se aprova, quanto libera e em que condições — com base em dados, não no achismo.' },
      { icon: UserCheck, title: 'Decisão dentro do fluxo', text: 'A análise acontece no mesmo lugar em que você cadastra o empréstimo: sem sair do sistema, sem retrabalho.' },
      { icon: AlertTriangle, title: 'Menos calote na origem', text: 'Avaliar antes de emprestar é a forma mais barata de reduzir inadimplência: você evita o problema em vez de correr atrás dele.' },
      { icon: FileText, title: 'Histórico que acompanha o cliente', text: 'As consultas e o comportamento de pagamento ficam registrados, enriquecendo a decisão em novos empréstimos.' },
      { icon: ShieldCheck, title: 'Responsabilidade com os dados', text: 'O tratamento das informações segue as boas práticas da LGPD, com segurança e finalidade legítima de análise de crédito.' },
    ]}
    differentials={[
      { title: 'Para o credor, não para o consumidor', text: 'O Kredor é uma ferramenta de quem empresta: a consulta serve para você avaliar o cliente, não para consulta pessoal do próprio CPF.' },
      { title: 'Integrado ao empréstimo', text: 'Analise e cadastre a operação no mesmo fluxo.' },
      { title: 'Score + histórico', text: 'Some a classificação de risco ao comportamento de pagamento na sua carteira.' },
      { title: 'Conforme a LGPD', text: 'Uso responsável dos dados, com finalidade de análise de crédito.' },
    ]}
    faq={[
      { q: 'A consulta serve para eu ver meu próprio CPF?', a: 'Não. O Kredor é voltado a credores. A consulta existe para você validar e avaliar o risco de um cliente antes de emprestar, dentro da gestão da carteira.' },
      { q: 'A análise reduz mesmo a inadimplência?', a: 'Avaliar o cliente antes de liberar ajuda a evitar operações de alto risco, reduzindo o calote na origem.' },
      { q: 'O uso dos dados é seguro e legal?', a: 'Sim. O tratamento segue as boas práticas da LGPD, com finalidade legítima de análise de crédito e segurança das informações.' },
      { q: 'A consulta já vem integrada ao sistema?', a: 'Sim. Ela faz parte do fluxo de cadastro e análise, junto ao score e ao histórico do cliente.' },
    ]}
    related={[
      { to: '/gestao-de-clientes', label: 'Gestão de clientes' },
      { to: '/sistema-para-credores', label: 'Sistema para credores' },
      { to: '/sistema-gestao-emprestimos', label: 'Sistema de gestão de empréstimos' },
      { to: '/emprestimo-particular-como-organizar', label: 'Como organizar empréstimo particular' },
      { to: '/precos', label: 'Ver preços' },
    ]}
  />
);

export default ConsultaCpfCredito;
