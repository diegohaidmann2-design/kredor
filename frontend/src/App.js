import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from './context/AuthContext';
import { PortalProvider, usePortal } from './context/PortalContext';
import { ThemeProvider } from './context/ThemeContext';
import { ModalProvider } from './components/Modal';
import { Toaster } from './components/ui/toaster';
import PWAManager from './components/PWAManager';
import Loading from './components/Loading';
import Login from './pages/Login';
import Verify2FA from './pages/Verify2FA';
import Dashboard from './pages/Dashboard';
import Clientes from './pages/Clientes';
import Emprestimos from './pages/Emprestimos';
import EmprestimoDetalhes from './pages/EmprestimoDetalhes';
import EmprestimosAbertos from './pages/EmprestimosAbertos';
import Simulacao from './pages/Simulacao';
import Consultas from './pages/Consultas';
import Carteira from './pages/Carteira';
import PageTitle from './components/PageTitle';
import Pagamentos from './pages/Pagamentos';
import Agenda from './pages/Agenda';
import Aprovacoes from './pages/Aprovacoes';
import CadastroPublico from './pages/CadastroPublico';
import AceiteEmprestimo from './pages/AceiteEmprestimo';
import Relatorios from './pages/Relatorios';
import Contratos from './pages/Contratos';
import AssistenteIA from './pages/AssistenteIA';
import Notificacoes from './pages/Notificacoes';
import Suporte from './pages/Suporte';
import SuporteDetalhes from './pages/SuporteDetalhes';
import Auditoria from './pages/Auditoria';
import Configuracoes from './pages/Configuracoes';
import Perfil from './pages/Perfil';
import LandingPage from './pages/LandingPage';
import Assinatura from './pages/Assinatura';
import CheckoutPublico from './pages/CheckoutPublico';
import CheckoutAsaasPagamento from './pages/CheckoutAsaasPagamento';
import CheckoutSyncPayPagamento from './pages/CheckoutSyncPayPagamento';
import CheckoutTransparenteBrick from './pages/CheckoutTransparenteBrick';
import Exportacao from './pages/Exportacao';
import SuperAdmin from './pages/SuperAdmin';
import AdminUsuarios from './pages/AdminUsuarios';
import AdminAssinaturas from './pages/AdminAssinaturas';
import AdminTransacoes from './pages/AdminTransacoes';
import AdminCupons from './pages/AdminCupons';
import AdminScheduler from './pages/AdminScheduler';
import AdminBackup from './pages/AdminBackup';
import AdminCarteiras from './pages/AdminCarteiras';
import AdminSuporte from './pages/AdminSuporte';
import AdminSuporteDetalhes from './pages/AdminSuporteDetalhes';
import AdminSeguranca from './pages/AdminSeguranca';
import VerificarEmail from './pages/VerificarEmail';
import AssinaturaExpirada from './pages/AssinaturaExpirada';
// Análise e Score
import AnaliseDashboard from './pages/AnaliseDashboard';
import AnaliseClientes from './pages/AnaliseClientes';
// Páginas Institucionais
import PoliticaPrivacidade from './pages/PoliticaPrivacidade';
import TermosUso from './pages/TermosUso';
import ComoFunciona from './pages/ComoFunciona';
import Sobre from './pages/Sobre';
import Contato from './pages/Contato';
import FAQ from './pages/FAQ';
import Precos from './pages/Precos';
import Seguranca from './pages/Seguranca';
import SistemaGestaoEmprestimos from './pages/landings/SistemaGestaoEmprestimos';
import CobrancaWhatsapp from './pages/landings/CobrancaWhatsapp';
import CobrancaPix from './pages/landings/CobrancaPix';
import ControleParcelasJuros from './pages/landings/ControleParcelasJuros';
import GestaoDeClientes from './pages/landings/GestaoDeClientes';
import SoftwareParaEmprestimos from './pages/landings/SoftwareParaEmprestimos';
import SistemaParaCredores from './pages/landings/SistemaParaCredores';
import SistemaMicrocredito from './pages/landings/SistemaMicrocredito';
import GestaoCarteiraCredito from './pages/landings/GestaoCarteiraCredito';
import ContratosDigitaisCCB from './pages/landings/ContratosDigitaisCCB';
import EmprestimoParticularComoOrganizar from './pages/landings/EmprestimoParticularComoOrganizar';
import ConsultaCpfCredito from './pages/landings/ConsultaCpfCredito';
import CalculadoraJuros from './pages/landings/CalculadoraJuros';
import Blog from './pages/Blog';
import BlogPost from './pages/BlogPost';
import TimezoneTest from './pages/TimezoneTest';
import Equipe from './pages/Equipe'; // 🆕 Página de Equipe
import WhatsAppConfig from './pages/WhatsAppConfig'; // 🆕 WhatsApp
import WhatsAppAntiSpam from './pages/WhatsAppAntiSpam'; // 🆕 Anti-Spam
import WhatsAppLogs from './pages/WhatsAppLogs'; // 🆕 Logs WhatsApp
import ReguaCobranca from './pages/ReguaCobranca'; // 🆕 Régua de Cobrança
import WhatsAppTemplates from './pages/WhatsAppTemplates'; // 🆕 Templates WhatsApp
import ConfigNotificacoes from './pages/ConfigNotificacoes'; // 🆕 Config Notificações

import AceitarConvite from './pages/AceitarConvite'; // 🆕 Aceitar Convite
// Portal do Cliente
import PortalHome from './pages/Portal/PortalHome';
import PortalLogin from './pages/Portal/PortalLogin';
import PortalLayout from './pages/Portal/PortalLayout';
import PortalDashboard from './pages/Portal/PortalDashboard';
import PortalEmprestimo from './pages/Portal/PortalEmprestimo';
import PortalPerfil from './pages/Portal/PortalPerfil';
import {
  podeAcessar, rotaInicial, SOMENTE_DONO, VER_CLIENTES, GERIR_CLIENTES,
  VER_EMPRESTIMOS, VER_FINANCEIRO, GERIR_EQUIPE, USAR_CONSULTAS,
} from './lib/permissoes';

// Aviso de acesso negado ao membro. Não é 404 nem redirecionamento silencioso: o membro
// precisa entender que a conta existe e o acesso é que não foi liberado.
const SemPermissao = ({ user }) => (
  <div
    className="min-h-screen flex items-center justify-center p-6 bg-background"
    data-testid="sem-permissao"
  >
    <div className="max-w-md text-center space-y-3">
      <h1 className="text-xl font-semibold">Acesso não liberado</h1>
      <p className="text-sm text-muted-foreground">
        O dono da conta não liberou esta área para o seu acesso. Peça a ele para ajustar as
        suas permissões em Minha Equipe.
      </p>
      {/* Volta para uma tela que ele ABRE — /dashboard exige ver_financeiro e seria outro muro. */}
      <a href={rotaInicial(user)} className="inline-block text-sm text-primary underline">
        Voltar ao início
      </a>
    </div>
  </div>
);

// Componente para rotas protegidas.
//
// `permissao` é o requisito para MEMBRO de equipe (services/permissoes_equipe.py no servidor).
// O servidor é quem nega de fato; isto evita a tela abrir e quebrar em 403 — inclusive quando
// o membro chega pela URL, sem passar pelo menu.
const ProtectedRoute = ({ children, permissao }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return <Loading message="Verificando autenticação..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (!podeAcessar(user, permissao)) {
    return <SemPermissao user={user} />;
  }

  // Se é TRIAL e email não verificado, redirecionar para verificação
  if (user && user.plano === 'trial' && !user.email_verificado) {
    // Permitir apenas a rota de verificação de email
    const currentPath = window.location.pathname;
    if (!currentPath.includes('/verificar-email')) {
      return <Navigate to={`/verificar-email?email=${encodeURIComponent(user.email)}`} />;
    }
  }

  return children;
};

// 🔒 Componente para rotas EXCLUSIVAS de ADMIN
const AdminRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return <Loading message="Verificando permissões..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  // Verificar se é admin
  if (user?.perfil !== 'admin') {
    console.warn('⚠️ Acesso negado: usuário não é admin');
    return <Navigate to={rotaInicial(user)} />;
  }

  return children;
};

// Componente para rota pública (login)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return <Loading message="Carregando..." />;
  }

  // rotaInicial, e não /dashboard fixo: o dashboard exige ver_financeiro, então um membro sem
  // essa permissão entrava com a senha certa e caía no aviso de acesso não liberado.
  return isAuthenticated ? <Navigate to={rotaInicial(user)} /> : children;
};

// 🔒 Componente para rotas protegidas do PORTAL
const PortalProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = usePortal();

  if (loading) {
    return <Loading message="Verificando acesso..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/portal/login" />;
  }

  return children;
};

// Componente para Home - Landing ou Dashboard baseado em autenticação
const HomeRoute = () => {
  const { isAuthenticated, loading, user } = useAuth();
  // Visitante sem token nunca deve ver o spinner: entrega a landing direto.
  const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('token');

  if (loading && hasToken) {
    return <Loading message="Carregando..." />;
  }

  if (isAuthenticated) {
    // Se é TRIAL e email não verificado, redirecionar para verificação
    if (user && user.plano === 'trial' && !user.email_verificado) {
      return <Navigate to={`/verificar-email?email=${encodeURIComponent(user.email)}`} />;
    }
    // Esta rota renderiza o Dashboard sem passar pelo ProtectedRoute, e é para "/" que o login
    // navega. O membro sem ver_financeiro chegava aqui e o Dashboard montava chamando uma API
    // que responde 403 — tela quebrada logo no primeiro segundo de uso. Manda para a primeira
    // tela que ele abre de verdade.
    if (!podeAcessar(user, VER_FINANCEIRO)) {
      return <Navigate to={rotaInicial(user)} />;
    }
    return <Dashboard />;
  }

  return <LandingPage />;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Home - Landing (não logado) ou Dashboard (logado) */}
      <Route path="/" element={<HomeRoute />} />

      {/* Dashboard direto (para navegação interna) */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute permissao={VER_FINANCEIRO}>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      {/* Rotas públicas */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />

      {/* Página de verificação 2FA */}
      <Route
        path="/verify-2fa"
        element={
          <PublicRoute>
            <Verify2FA />
          </PublicRoute>
        }
      />

      {/* 🆕 Teste de Timezone */}
      <Route path="/timezone-test" element={<TimezoneTest />} />

      <Route
        path="/clientes"
        element={
          <ProtectedRoute permissao={VER_CLIENTES}>
            <Clientes />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clientes/:clienteId/emprestimos"
        element={
          <ProtectedRoute permissao={VER_EMPRESTIMOS}>
            <Emprestimos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/emprestimos"
        element={
          <ProtectedRoute permissao={VER_EMPRESTIMOS}>
            <Emprestimos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/emprestimos/quitados"
        element={
          <ProtectedRoute permissao={VER_EMPRESTIMOS}>
            <Emprestimos somenteQuitados={true} />
          </ProtectedRoute>
        }
      />

      <Route
        path="/emprestimos/abertos"
        element={
          <ProtectedRoute permissao={VER_EMPRESTIMOS}>
            <EmprestimosAbertos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/emprestimos/:id"
        element={
          <ProtectedRoute permissao={VER_EMPRESTIMOS}>
            <EmprestimoDetalhes />
          </ProtectedRoute>
        }
      />

      <Route
        path="/consultas"
        element={
          <ProtectedRoute permissao={USAR_CONSULTAS}>
            <Consultas />
          </ProtectedRoute>
        }
      />

      <Route
        path="/simulacao"
        element={
          <ProtectedRoute permissao={VER_EMPRESTIMOS}>
            <Simulacao />
          </ProtectedRoute>
        }
      />

      <Route
        path="/pagamentos"
        element={
          <ProtectedRoute permissao={SOMENTE_DONO}>
            <Pagamentos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/agenda"
        element={
          <ProtectedRoute permissao={VER_EMPRESTIMOS}>
            <Agenda />
          </ProtectedRoute>
        }
      />

      <Route
        path="/aprovacoes"
        element={
          <ProtectedRoute permissao={GERIR_CLIENTES}>
            <Aprovacoes />
          </ProtectedRoute>
        }
      />

      {/* Cadastro público do cliente (sem autenticação) */}
      <Route path="/cadastro" element={<CadastroPublico />} />
      <Route path="/cadastro/:token" element={<CadastroPublico />} />

      {/* Aceite de empréstimo (link público, sem autenticação) */}
      <Route path="/aceite" element={<AceiteEmprestimo />} />
      <Route path="/aceite/:token" element={<AceiteEmprestimo />} />

      <Route
        path="/whatsapp"
        element={
          <ProtectedRoute permissao={SOMENTE_DONO}>
            <WhatsAppConfig />
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp/anti-spam"
        element={
          <ProtectedRoute permissao={SOMENTE_DONO}>
            <WhatsAppAntiSpam />
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp/logs"
        element={
          <ProtectedRoute permissao={SOMENTE_DONO}>
            <WhatsAppLogs />
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp/regua"
        element={
          <ProtectedRoute permissao={SOMENTE_DONO}>
            <ReguaCobranca />
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp/templates"
        element={
          <ProtectedRoute permissao={SOMENTE_DONO}>
            <WhatsAppTemplates />
          </ProtectedRoute>
        }
      />

      <Route
        path="/relatorios"
        element={
          <ProtectedRoute permissao={VER_FINANCEIRO}>
            <Relatorios />
          </ProtectedRoute>
        }
      />

      <Route
        path="/contratos"
        element={
          <ProtectedRoute permissao={VER_EMPRESTIMOS}>
            <Contratos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/assistente"
        element={
          <ProtectedRoute permissao={VER_FINANCEIRO}>
            <AssistenteIA />
          </ProtectedRoute>
        }
      />

      <Route
        path="/notificacoes"
        element={
          <ProtectedRoute>
            <Notificacoes />
          </ProtectedRoute>
        }
      />

      <Route
        path="/suporte"
        element={
          <ProtectedRoute>
            <Suporte />
          </ProtectedRoute>
        }
      />

      <Route
        path="/suporte/:numero_ticket"
        element={
          <ProtectedRoute>
            <SuporteDetalhes />
          </ProtectedRoute>
        }
      />

      <Route
        path="/auditoria"
        element={
          <AdminRoute>
            <Auditoria />
          </AdminRoute>
        }
      />

      <Route
        path="/perfil"
        element={
          <ProtectedRoute>
            <Perfil />
          </ProtectedRoute>
        }
      />

      <Route
        path="/configuracoes"
        element={
          <AdminRoute>
            <Configuracoes />
          </AdminRoute>
        }
      />

      <Route 
        path="/config-notificacoes" 
        element={<ProtectedRoute permissao={SOMENTE_DONO}><ConfigNotificacoes /></ProtectedRoute>} 
      />

      {/* 🆕 Minha Equipe (Apenas Dono - Validação feita na página ou sidebar por enquanto, mas rota protegida) */}
      <Route
        path="/equipe"
        element={
          <ProtectedRoute permissao={GERIR_EQUIPE}>
            <Equipe />
          </ProtectedRoute>
        }
      />

      <Route
        path="/assinatura"
        element={
          <ProtectedRoute permissao={SOMENTE_DONO}>
            <Assinatura />
          </ProtectedRoute>
        }
      />

      <Route
        path="/exportacao"
        element={
          <ProtectedRoute permissao={SOMENTE_DONO}>
            <Exportacao />
          </ProtectedRoute>
        }
      />

      <Route
        path="/superadmin"
        element={
          <AdminRoute>
            <SuperAdmin />
          </AdminRoute>
        }
      />


      <Route
        path="/admin/usuarios"
        element={
          <AdminRoute>
            <AdminUsuarios />
          </AdminRoute>
        }
      />

      <Route
        path="/admin/assinaturas"
        element={
          <AdminRoute>
            <AdminAssinaturas />
          </AdminRoute>
        }
      />

      <Route
        path="/admin/transacoes"
        element={
          <AdminRoute>
            <AdminTransacoes />
          </AdminRoute>
        }
      />

      <Route
        path="/admin/cupons"
        element={
          <AdminRoute>
            <AdminCupons />
          </AdminRoute>
        }
      />

      <Route
        path="/admin/scheduler"
        element={
          <AdminRoute>
            <AdminScheduler />
          </AdminRoute>
        }
      />

      <Route
        path="/admin/seguranca"
        element={
          <AdminRoute>
            <AdminSeguranca />
          </AdminRoute>
        }
      />

      <Route
        path="/admin/backup"
        element={
          <AdminRoute>
            <AdminBackup />
          </AdminRoute>
        }
      />

      <Route
        path="/admin/carteiras"
        element={
          <AdminRoute>
            <AdminCarteiras />
          </AdminRoute>
        }
      />

      <Route
        path="/carteira"
        element={
          <ProtectedRoute permissao={SOMENTE_DONO}>
            <Carteira />
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin/suporte"
        element={
          <AdminRoute>
            <AdminSuporte />
          </AdminRoute>
        }
      />

      <Route
        path="/admin/suporte/:numero_ticket"
        element={
          <AdminRoute>
            <AdminSuporteDetalhes />
          </AdminRoute>
        }
      />

      {/* Análise e Score */}
      <Route
        path="/analise"
        element={
          <ProtectedRoute permissao={VER_CLIENTES}>
            <AnaliseDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analise/dashboard"
        element={
          <ProtectedRoute permissao={VER_CLIENTES}>
            <AnaliseDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analise/clientes"
        element={
          <ProtectedRoute permissao={VER_CLIENTES}>
            <AnaliseClientes />
          </ProtectedRoute>
        }
      />

      {/* Páginas Institucionais (públicas) */}
      <Route path="/privacidade" element={<PoliticaPrivacidade />} />
      <Route path="/termos" element={<TermosUso />} />
      <Route path="/como-funciona" element={<ComoFunciona />} />
      <Route path="/sobre" element={<Sobre />} />
      <Route path="/contato" element={<Contato />} />
      <Route path="/faq" element={<FAQ />} />

      {/* Páginas comerciais / landings (públicas, SEO) */}
      <Route path="/precos" element={<Precos />} />
      <Route path="/seguranca" element={<Seguranca />} />
      <Route path="/sistema-gestao-emprestimos" element={<SistemaGestaoEmprestimos />} />
      <Route path="/cobranca-whatsapp" element={<CobrancaWhatsapp />} />
      <Route path="/cobranca-pix" element={<CobrancaPix />} />
      <Route path="/controle-de-parcelas-e-juros" element={<ControleParcelasJuros />} />
      <Route path="/gestao-de-clientes" element={<GestaoDeClientes />} />
      <Route path="/software-para-emprestimos" element={<SoftwareParaEmprestimos />} />
      <Route path="/sistema-para-credores" element={<SistemaParaCredores />} />
      <Route path="/sistema-microcredito" element={<SistemaMicrocredito />} />
      <Route path="/gestao-carteira-credito" element={<GestaoCarteiraCredito />} />
      <Route path="/contratos-digitais-ccb" element={<ContratosDigitaisCCB />} />
      <Route path="/emprestimo-particular-como-organizar" element={<EmprestimoParticularComoOrganizar />} />
      <Route path="/consulta-cpf-credito" element={<ConsultaCpfCredito />} />
      <Route path="/calculadora-de-juros" element={<CalculadoraJuros />} />
      <Route path="/blog" element={<Blog />} />
      <Route path="/blog/:slug" element={<BlogPost />} />

      {/* Checkout Público (sem autenticação) */}
      <Route path="/checkout/:planoId" element={<CheckoutPublico />} />

      {/* Checkout Asaas - Página de Pagamento */}
      <Route path="/checkout-asaas-pagamento" element={<CheckoutAsaasPagamento />} />

      {/* Checkout SyncPay PIX - Página de Pagamento */}
      <Route path="/checkout-syncpay-pagamento" element={<CheckoutSyncPayPagamento />} />

      {/* Checkout Transparente com Card Payment Brick (PIX + Cartão - sem redirecionar) */}
      <Route path="/checkout-transparente/:planoId" element={<CheckoutTransparenteBrick />} />

      {/* Verificação de email (pública) */}
      <Route path="/verificar-email" element={<VerificarEmail />} />
      <Route path="/verificar-email/:token" element={<VerificarEmail />} />

      {/* 🆕 Aceitar Convite (Público) */}
      <Route path="/aceitar-convite/:token" element={<AceitarConvite />} />

      {/* Assinatura expirada (pública) */}
      <Route path="/assinatura-expirada" element={<AssinaturaExpirada />} />

      {/* 🆕 PORTAL DO CLIENTE (Self-Service) */}
      <Route path="/portal" element={<PortalHome />} />
      <Route path="/portal/login" element={<PortalLogin />} />
      <Route path="/portal/app" element={
        <PortalProtectedRoute>
          <PortalLayout />
        </PortalProtectedRoute>
      }>
        <Route path="dashboard" element={<PortalDashboard />} />
        <Route path="emprestimo/:id" element={<PortalEmprestimo />} />
        <Route path="perfil" element={<PortalPerfil />} />
      </Route>

      {/* Rota padrão - redireciona para home */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <ModalProvider>
        <AuthProvider>
          <PortalProvider>
            <BrowserRouter>
              <PageTitle />
              <AppRoutes />
            </BrowserRouter>
            <Toaster />
            <PWAManager />
          </PortalProvider>
        </AuthProvider>
      </ModalProvider>
    </ThemeProvider>
  );
}

export default App;
