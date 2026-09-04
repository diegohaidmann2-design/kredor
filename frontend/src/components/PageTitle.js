import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const BASE = 'GestorCred';

// Título SEO completo mantido apenas na landing pública
const LANDING_TITLE = 'GestorCred - Sistema #1 de Gestão de Empréstimos | Software Controle Crédito Pessoal | Cobrança PIX Automática';

const ROUTES = [
  { prefix: '/dashboard', title: 'Dashboard' },
  { prefix: '/clientes', title: 'Clientes' },
  { prefix: '/emprestimos', title: 'Empréstimos' },
  { prefix: '/parcelas', title: 'Parcelas' },
  { prefix: '/pagamentos', title: 'Pagamentos' },
  { prefix: '/agenda', title: 'Agenda de Cobrança' },
  { prefix: '/consultas', title: 'Consultas' },
  { prefix: '/relatorios', title: 'Relatórios' },
  { prefix: '/analise', title: 'Análise' },
  { prefix: '/simulacao', title: 'Simulação' },
  { prefix: '/equipe', title: 'Equipe' },
  { prefix: '/aprovacoes', title: 'Aprovações' },
  { prefix: '/contratos', title: 'Contratos' },
  { prefix: '/notificacoes', title: 'Notificações' },
  { prefix: '/suporte', title: 'Suporte' },
  { prefix: '/configuracoes', title: 'Configurações' },
  { prefix: '/assinatura', title: 'Assinatura' },
  { prefix: '/onboarding', title: 'Primeiros Passos' },
  { prefix: '/verificar-email', title: 'Verificar E-mail' },
  { prefix: '/aceitar-convite', title: 'Aceitar Convite' },
  { prefix: '/superadmin', title: 'Super Admin' },
  { prefix: '/admin', title: 'Administração' },
  { prefix: '/portal', title: 'Portal do Cliente' },
  { prefix: '/login', title: 'Entrar' },
  { prefix: '/cadastro', title: 'Cadastro' },
];

export default function PageTitle() {
  const { pathname } = useLocation();

  useEffect(() => {
    if (pathname === '/') {
      document.title = LANDING_TITLE;
      return;
    }
    const match = ROUTES.find((r) => pathname === r.prefix || pathname.startsWith(`${r.prefix}/`));
    document.title = match ? `${match.title} · ${BASE}` : BASE;
  }, [pathname]);

  return null;
}
