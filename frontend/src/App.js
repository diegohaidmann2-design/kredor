import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from './context/AuthContext';
import { PortalProvider, usePortal } from './context/PortalContext';
import { ThemeProvider } from './context/ThemeContext';
import { ModalProvider } from './components/Modal';
import { Toaster } from './components/ui/toaster';
import Loading from './components/Loading';
import Login from './pages/Login';
import Verify2FA from './pages/Verify2FA';
import Dashboard from './pages/Dashboard';
import Clientes from './pages/Clientes';
import Emprestimos from './pages/Emprestimos';
import EmprestimoDetalhes from './pages/EmprestimoDetalhes';
import EmprestimosAbertos from './pages/EmprestimosAbertos';
import Simulacao from './pages/Simulacao';
import Pagamentos from './pages/Pagamentos';
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
import AdminSuporte from './pages/AdminSuporte';
import AdminSuporteDetalhes from './pages/AdminSuporteDetalhes';
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
import TimezoneTest from './pages/TimezoneTest';
import Equipe from './pages/Equipe'; // 🆕 Página de Equipe
import WhatsAppConfig from './pages/WhatsAppConfig'; // 🆕 WhatsApp
import WhatsAppAntiSpam from './pages/WhatsAppAntiSpam'; // 🆕 Anti-Spam
import WhatsAppLogs from './pages/WhatsAppLogs'; // 🆕 Logs WhatsApp
import ConfigNotificacoes from './pages/ConfigNotificacoes'; // 🆕 Config Notificações

import AceitarConvite from './pages/AceitarConvite'; // 🆕 Aceitar Convite
// Portal do Cliente
import PortalHome from './pages/Portal/PortalHome';
import PortalLogin from './pages/Portal/PortalLogin';
import PortalLayout from './pages/Portal/PortalLayout';
import PortalDashboard from './pages/Portal/PortalDashboard';
import PortalEmprestimo from './pages/Portal/PortalEmprestimo';
import PortalPerfil from './pages/Portal/PortalPerfil';

// Componente para rotas protegidas
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return <Loading message="Verificando autenticação..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
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
  if (user?.perfil !== 'admin' && user?.perfil !== 'superadmin') {
    console.warn('⚠️ Acesso negado: usuário não é admin');
    return <Navigate to="/dashboard" />;
  }

  return children;
};

// Componente para rota pública (login)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <Loading message="Carregando..." />;
  }

  return isAuthenticated ? <Navigate to="/dashboard" /> : children;
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

  if (loading) {
    return <Loading message="Carregando..." />;
  }

  if (isAuthenticated) {
    // Se é TRIAL e email não verificado, redirecionar para verificação
    if (user && user.plano === 'trial' && !user.email_verificado) {
      return <Navigate to={`/verificar-email?email=${encodeURIComponent(user.email)}`} />;
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
          <ProtectedRoute>
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
          <ProtectedRoute>
            <Clientes />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clientes/:clienteId/emprestimos"
        element={
          <ProtectedRoute>
            <Emprestimos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/emprestimos"
        element={
          <ProtectedRoute>
            <Emprestimos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/emprestimos/quitados"
        element={
          <ProtectedRoute>
            <Emprestimos somenteQuitados={true} />
          </ProtectedRoute>
        }
      />

      <Route
        path="/emprestimos/abertos"
        element={
          <ProtectedRoute>
            <EmprestimosAbertos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/emprestimos/:id"
        element={
          <ProtectedRoute>
            <EmprestimoDetalhes />
          </ProtectedRoute>
        }
      />

      <Route
        path="/simulacao"
        element={
          <ProtectedRoute>
            <Simulacao />
          </ProtectedRoute>
        }
      />

      <Route
        path="/pagamentos"
        element={
          <ProtectedRoute>
            <Pagamentos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/whatsapp"
        element={
          <ProtectedRoute>
            <WhatsAppConfig />
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp/anti-spam"
        element={
          <ProtectedRoute>
            <WhatsAppAntiSpam />
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp/logs"
        element={
          <ProtectedRoute>
            <WhatsAppLogs />
          </ProtectedRoute>
        }
      />

      <Route
        path="/relatorios"
        element={
          <ProtectedRoute>
            <Relatorios />
          </ProtectedRoute>
        }
      />

      <Route
        path="/contratos"
        element={
          <ProtectedRoute>
            <Contratos />
          </ProtectedRoute>
        }
      />

      <Route
        path="/assistente"
        element={
          <ProtectedRoute>
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
        element={<ProtectedRoute><ConfigNotificacoes /></ProtectedRoute>} 
      />

      {/* 🆕 Minha Equipe (Apenas Dono - Validação feita na página ou sidebar por enquanto, mas rota protegida) */}
      <Route
        path="/equipe"
        element={
          <ProtectedRoute>
            <Equipe />
          </ProtectedRoute>
        }
      />

      <Route
        path="/assinatura"
        element={
          <ProtectedRoute>
            <Assinatura />
          </ProtectedRoute>
        }
      />

      <Route
        path="/exportacao"
        element={
          <ProtectedRoute>
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
        path="/admin/backup"
        element={
          <AdminRoute>
            <AdminBackup />
          </AdminRoute>
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
          <ProtectedRoute>
            <AnaliseDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analise/dashboard"
        element={
          <ProtectedRoute>
            <AnaliseDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analise/clientes"
        element={
          <ProtectedRoute>
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
              <AppRoutes />
            </BrowserRouter>
            <Toaster />
          </PortalProvider>
        </AuthProvider>
      </ModalProvider>
    </ThemeProvider>
  );
}

export default App;
