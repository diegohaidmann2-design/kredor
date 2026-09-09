import React from 'react';
import { Lock, ShieldCheck, KeyRound, Server, Eye, FileCheck } from 'lucide-react';
import CommercialLanding from '../components/CommercialLanding';

const Seguranca = () => (
  <CommercialLanding
    seo={{
      title: 'Segurança e proteção de dados (LGPD) | Kredor',
      description: 'Saiba como o Kredor protege seus dados: criptografia, controle de acesso e boas práticas de segurança, com respeito à LGPD. Seus dados e os dos seus clientes seguros.',
      path: '/seguranca',
    }}
    eyebrow="Segurança e privacidade"
    h1="Segurança dos seus dados e conformidade com a LGPD"
    subtitle="Trabalhar com crédito exige responsabilidade com dados. O Kredor adota criptografia, controle de acesso e boas práticas para proteger as informações da sua carteira."
    heroBullets={[
      'Dados sensíveis criptografados',
      'Controle de acesso por usuário e perfil',
      'Boas práticas alinhadas à LGPD',
      'Registro de atividades (auditoria)',
    ]}
    blocks={[
      { icon: Lock, title: 'Criptografia de dados', text: 'Informações sensíveis são armazenadas com criptografia e o tráfego é protegido, reduzindo o risco de exposição.' },
      { icon: KeyRound, title: 'Acesso controlado', text: 'Cada usuário acessa apenas o que precisa. Perfis e permissões evitam acessos indevidos aos dados da carteira.' },
      { icon: Eye, title: 'Trilha de auditoria', text: 'Ações relevantes ficam registradas, permitindo acompanhar quem fez o quê e quando dentro do sistema.' },
      { icon: FileCheck, title: 'Privacidade e LGPD', text: 'A coleta e o uso de dados seguem o princípio da finalidade: validação e gestão de crédito. Consulte nossa Política de Privacidade.' },
      { icon: Server, title: 'Infraestrutura confiável', text: 'Hospedagem em ambiente monitorado, com rotinas de backup para preservar suas informações.' },
      { icon: ShieldCheck, title: 'Uso responsável', text: 'O Kredor é um software de gestão. A consulta de dados serve à análise de crédito — nunca à perseguição de pessoas.' },
    ]}
    differentials={[
      { title: 'Segurança como padrão', text: 'Criptografia e controle de acesso já vêm ativados, sem configuração complexa da sua parte.' },
      { title: 'Transparência', text: 'Política de Privacidade e Termos de Uso claros, disponíveis a qualquer momento.' },
      { title: 'Auditoria integrada', text: 'Histórico de ações para rastreabilidade e governança da operação.' },
      { title: 'Foco em conformidade', text: 'Decisões de produto orientadas ao respeito à LGPD e à privacidade dos clientes.' },
    ]}
    faq={[
      { q: 'Meus dados ficam seguros?', a: 'Sim. Utilizamos criptografia para dados sensíveis, controle de acesso por usuário e boas práticas de segurança, além de rotinas de backup.' },
      { q: 'O Kredor é compatível com a LGPD?', a: 'Adotamos princípios da LGPD, como finalidade e minimização. A consulta de dados é usada para validação e análise de crédito. Veja a Política de Privacidade para detalhes.' },
      { q: 'Quem pode ver os dados dos meus clientes?', a: 'Apenas usuários autorizados da sua conta, conforme os perfis e permissões que você definir.' },
    ]}
    related={[
      { to: '/privacidade', label: 'Política de Privacidade' },
      { to: '/termos', label: 'Termos de Uso' },
      { to: '/gestao-de-clientes', label: 'Gestão de clientes' },
      { to: '/precos', label: 'Ver preços' },
    ]}
    ctaTitle="Gestão de crédito com segurança"
    ctaText="Profissionalize sua operação com um sistema seguro. Teste grátis por 7 dias."
  />
);

export default Seguranca;
