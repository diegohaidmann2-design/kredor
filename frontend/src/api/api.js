import axios from 'axios';
import { BACKEND_URL as ENV_BACKEND_URL } from '../config/env';

// 1. Configuração da URL base da API
export const BACKEND_URL = ENV_BACKEND_URL;

const API = `${BACKEND_URL}/api`;

// Configurar interceptor para adicionar token
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth
export const authAPI = {
  registro: (data) => axios.post(`${API}/auth/registro`, data),
  login: (data) => axios.post(`${API}/auth/login`, data),
  getMe: () => axios.get(`${API}/auth/me`),
  permissoes: () => axios.get(`${API}/auth/permissoes`),
  refresh: (refreshToken) => axios.post(`${API}/auth/refresh`, { refresh_token: refreshToken }),
  verificarEmail: (token) => axios.post(`${API}/auth/verificar-email/${token}`),
  verificarStatusEmail: (email) => axios.get(`${API}/auth/verificar-status-email`, { params: { email } }),
  reenviarVerificacao: (email) => axios.post(`${API}/auth/reenviar-verificacao`, { email }),
  getStatus2FA: () => axios.get(`${API}/auth/2fa-status`),
  toggle2FA: (data) => axios.post(`${API}/auth/toggle-2fa`, data),
  verify2FA: (data) => axios.post(`${API}/auth/verify-2fa`, data),
  resend2FA: (data) => axios.post(`${API}/auth/resend-2fa`, data),
  alterarSenha: (data) => axios.post(`${API}/auth/alterar-senha`, data),
};

// Clientes
export const clientesAPI = {
  criar: (data) => axios.post(`${API}/clientes`, data),
  listar: (params) => axios.get(`${API}/clientes`, { params }),
  obter: (id) => axios.get(`${API}/clientes/${id}`),
  atualizar: (id, data) => axios.put(`${API}/clientes/${id}`, data),
  deletar: (id) => axios.delete(`${API}/clientes/${id}`),
  reenviarCodigoPortal: (id) => axios.post(`${API}/clientes/${id}/reenviar-codigo-portal`),
  gerarCodigoPortal: (id) => axios.post(`${API}/clientes/${id}/gerar-codigo-portal`),
};

// Empréstimos
export const emprestimosAPI = {
  simular: (data) => axios.post(`${API}/emprestimos/simular`, data),
  criar: (data) => axios.post(`${API}/emprestimos`, data),
  listar: (params) => axios.get(`${API}/emprestimos`, { params }),
  obter: (id) => axios.get(`${API}/emprestimos/${id}`),
  atualizar: (id, data) => axios.put(`${API}/emprestimos/${id}`, data),
  listarParcelas: (id) => axios.get(`${API}/emprestimos/${id}/parcelas`),
  deletar: (id, hard = false) => axios.delete(`${API}/emprestimos/${id}`, { params: { hard } }),
  restaurar: (id) => axios.post(`${API}/emprestimos/${id}/restaurar`),
  exportar: (id, formato = 'pdf') => axios.get(`${API}/emprestimos/${id}/exportar`, {
    params: { formato },
    responseType: 'blob'
  }),
};

// Pagamentos
export const pagamentosAPI = {
  criar: (data) => axios.post(`${API}/pagamentos`, data),
  listar: (params) => axios.get(`${API}/pagamentos`, { params }),
};

// Dashboard
export const dashboardAPI = {
  obterStats: () => axios.get(`${API}/dashboard`)
};

// WhatsApp API
export const whatsappAPI = {
    // Configura\u00e7\u00f5es (Super Admin)
    obterConfigEvolution: () => axios.get(`${API}/whatsapp/config/evolution`),
    atualizarConfigEvolution: (config) => axios.put(`${API}/whatsapp/config/evolution`, config),
    testarConfigEvolution: (config) => axios.post(`${API}/whatsapp/config/evolution/test`, config),

    
    // Conex\u00f5es
    listarConexoes: () => axios.get(`${API}/whatsapp/conexoes`),
    criarConexao: () => axios.post(`${API}/whatsapp/conexoes`),
    obterQRCode: (conexaoId) => axios.get(`${API}/whatsapp/conexoes/${conexaoId}/qrcode`),
    verificarStatus: (conexaoId) => axios.get(`${API}/whatsapp/conexoes/${conexaoId}/status`),
    deletarConexao: (conexaoId) => axios.delete(`${API}/whatsapp/conexoes/${conexaoId}`),
    
    // Mensagens
    enviarMensagem: (dados) => axios.post(`${API}/whatsapp/mensagens/enviar`, dados),
    listarMensagens: (params) => axios.get(`${API}/whatsapp/mensagens`, { params }),
    enviarCobrancaParcela: (parcelaId) => axios.post(`${API}/whatsapp/enviar-cobranca-parcela/${parcelaId}`)
};

// Asaas API
export const asaasAPI = {
  obterConfig: () => axios.get(`${API}/asaas/config`),
  atualizarConfig: (config) => axios.put(`${API}/asaas/config`, config),
  testarConfig: (config) => axios.post(`${API}/asaas/config/testar`, config),
  verificarStatus: () => axios.get(`${API}/asaas/status`),
};

// Notificações
export const notificacoesAPI = {
  listar: (params = {}) => axios.get(`${API}/notificacoes`, { params }),
  marcarLida: (id) => axios.post(`${API}/notificacoes/${id}/marcar-lida`),
  marcarTodasLidas: () => axios.post(`${API}/notificacoes/marcar-todas-lidas`),
  verificarVencimentos: () => axios.post(`${API}/notificacoes/verificar-vencimentos`),
  excluir: (id) => axios.delete(`${API}/notificacoes/${id}`),
  limparTodas: () => axios.delete(`${API}/notificacoes/limpar-todas`),
};

// Contratos
export const contratosAPI = {
  gerar: (data) => axios.post(`${API}/contratos/gerar`, data, { responseType: 'blob' }),
  preview: (emprestimoId) => axios.get(`${API}/contratos/preview/${emprestimoId}`),
};

// Configurações
export const configuracoesAPI = {
  obterLanding: () => axios.get(`${API}/configuracoes/landing`),
  atualizarLanding: (data) => axios.put(`${API}/configuracoes/landing`, data),
  obterIA: () => axios.get(`${API}/configuracoes/ia`),
  atualizarIA: (data) => axios.put(`${API}/configuracoes/ia`, data),
  obterNotificacoes: () => axios.get(`${API}/configuracoes/notificacoes`),
  atualizarNotificacoes: (data) => axios.put(`${API}/configuracoes/notificacoes`, data),
  restaurarNotificacoesPadrao: () => axios.post(`${API}/configuracoes/notificacoes/restaurar-padrao`),
};

// Relatórios
export const relatoriosAPI = {
  gerar: (data) => axios.post(`${API}/relatorios/gerar`, data, { responseType: 'blob' }),
};

// Parcelas
export const parcelasAPI = {
  listarPendentes: () => axios.get(`${API}/parcelas/pendentes`),
  excluir: (id) => axios.delete(`${API}/parcelas/${id}`),
};

// Assinaturas / Stripe / Asaas
export const assinaturasAPI = {
  listarPlanos: () => axios.get(`${API}/assinaturas/planos`),
  criarCheckout: (data) => axios.post(`${API}/assinaturas/checkout`, data),
  checkoutPublico: (data) => axios.post(`${API}/assinaturas/checkout-publico`, data),
  checkoutAsaas: (data) => axios.post(`${API}/assinaturas/checkout-asaas`, data),
  verificarStatus: (sessionId) => axios.get(`${API}/assinaturas/status/${sessionId}`),
  obter: () => axios.get(`${API}/assinaturas/minha`),
  obterMinha: () => axios.get(`${API}/assinaturas/minha`),
  historico: () => axios.get(`${API}/assinaturas/historico`),
  cancelar: () => axios.post(`${API}/assinaturas/cancelar`),
  // Gateway de Assinaturas (Admin)
  obterGatewayConfig: () => axios.get(`${API}/assinaturas/gateway/config`),
  atualizarGatewayConfig: (data) => axios.put(`${API}/assinaturas/gateway/config`, data),
  listarGatewaysDisponiveis: () => axios.get(`${API}/assinaturas/gateway/disponiveis`),
  // Mercado Pago
  checkoutMercadoPago: (data) => axios.post(`${API}/assinaturas/checkout-mercadopago`, data),
  checkoutTransparenteCard: (data) => axios.post(`${API}/assinaturas/checkout-transparente-card`, data),
  checkoutTransparentePix: (data) => axios.post(`${API}/assinaturas/checkout-transparente-pix`, data),
  upgradePix: (params) => axios.post(`${API}/assinaturas/upgrade-pix`, null, { params }),
  verificarAssinaturaMp: (subscriptionId) => axios.get(`${API}/assinaturas/verificar-assinatura-mp/${subscriptionId}`),
  verificarPagamentoStatus: (paymentId) => axios.get(`${API}/assinaturas/payment-status/${paymentId}`),
  validarCupom: (codigo, email) => axios.get(`${API}/assinaturas/cupom/validar/${codigo}`, { params: { email } }),
};

// Assistente IA
export const assistenteAPI = {
  chat: (data) => axios.post(`${API}/assistente/chat`, data),
  historico: (sessionId) => axios.get(`${API}/assistente/historico`, { params: { session_id: sessionId } }),
};

// Auditoria
export const auditoriaAPI = {
  listar: (params) => axios.get(`${API}/auditoria`, { params }),
  estatisticas: () => axios.get(`${API}/auditoria/estatisticas`),
  limpar: () => axios.delete(`${API}/auditoria/limpar`),
};

// Dados de teste
export const dadosTesteAPI = {
  criar: () => axios.post(`${API}/dados-teste/criar`),
};

// Exportação em Massa
export const exportacaoAPI = {
  resumo: () => axios.get(`${API}/exportacao/resumo`),
  exportar: async (data) => {
    try {
      const response = await axios.post(`${API}/exportacao/exportar`, data, {
        responseType: 'arraybuffer'
      });
      return response;
    } catch (error) {
      // Converter arraybuffer para JSON se for erro
      if (error.response && error.response.data) {
        try {
          const decoder = new TextDecoder('utf-8');
          const text = decoder.decode(error.response.data);
          const json = JSON.parse(text);
          error.response.data = json;
        } catch (e) {
          // Mantém o erro original
        }
      }
      throw error;
    }
  },
};

// Super Admin
export const superadminAPI = {
  // Dashboard
  dashboard: () => axios.get(`${API}/superadmin/dashboard`),

  // Configurações
  obterConfigEmail: () => axios.get(`${API}/superadmin/configuracoes/email`),
  atualizarConfigEmail: (data) => axios.put(`${API}/superadmin/configuracoes/email`, data),
  testarConfigEmail: (emailDestino) => axios.post(`${API}/superadmin/configuracoes/email/testar`, null, { params: { email_destino: emailDestino } }),

  // Usuários
  listarUsuarios: (params) => axios.get(`${API}/superadmin/usuarios`, { params }),
  criarUsuario: (data) => axios.post(`${API}/superadmin/usuarios`, data),
  obterUsuario: (id) => axios.get(`${API}/superadmin/usuarios/${id}`),
  atualizarUsuario: (id, data) => axios.put(`${API}/superadmin/usuarios/${id}`, data),
  deletarUsuario: (id, permanent = false) => axios.delete(`${API}/superadmin/usuarios/${id}`, { params: { permanent } }),
  ativarUsuario: (id) => axios.post(`${API}/superadmin/usuarios/${id}/ativar`),
  resetarSenhaUsuario: (id, novaSenha) => axios.post(`${API}/superadmin/usuarios/${id}/resetar-senha`, null, { params: { nova_senha: novaSenha } }),
  verificarEmailUsuario: (id) => axios.post(`${API}/superadmin/usuarios/${id}/verificar-email`),
  desativar2FAUsuario: (id) => axios.post(`${API}/superadmin/usuarios/${id}/desativar-2fa`),

  // Assinaturas
  listarAssinaturas: (params) => axios.get(`${API}/superadmin/assinaturas`, { params }),
  criarAssinatura: (data) => axios.post(`${API}/superadmin/assinaturas`, data),
  obterAssinatura: (id) => axios.get(`${API}/superadmin/assinaturas/${id}`),
  atualizarAssinatura: (id, data) => axios.put(`${API}/superadmin/assinaturas/${id}`, data),
  cancelarAssinatura: (id) => axios.post(`${API}/superadmin/assinaturas/${id}/cancelar`),
  renovarAssinatura: (id, dias) => axios.post(`${API}/superadmin/assinaturas/${id}/renovar`, null, { params: { dias } }),
  logsAssinatura: (id) => axios.get(`${API}/superadmin/assinaturas/${id}/logs`),
  deletarAssinatura: (id) => axios.delete(`${API}/superadmin/assinaturas/${id}`),

  // Estatísticas
  estatisticasReceita: (meses) => axios.get(`${API}/superadmin/estatisticas/receita`, { params: { meses } }),
  estatisticasUsuarios: () => axios.get(`${API}/superadmin/estatisticas/usuarios`),
};

// Análise e Score
export const analiseAPI = {
  // Dashboard
  obterDashboard: (params) => axios.get(`${API}/analise/dashboard`, { params }),

  // Clientes com Score
  listarClientesComScore: (params) => axios.get(`${API}/analise/clientes`, { params }),

  // Detalhes do Score
  obterDetalheScore: (clienteId) => axios.get(`${API}/analise/score/${clienteId}`),

  // Recalcular
  recalcularScore: (clienteId) => axios.post(`${API}/analise/recalcular/${clienteId}`),
  recalcularTodos: () => axios.post(`${API}/analise/recalcular-todos`),
};

// Scheduler (Admin)
export const schedulerAPI = {
  status: () => axios.get(`${API}/admin/scheduler/status`),
  estatisticas: () => axios.get(`${API}/admin/scheduler/estatisticas`),
  historico: (limit = 20) => axios.get(`${API}/admin/scheduler/jobs/historico`, { params: { limit } }),
  executarJob: (jobName) => axios.post(`${API}/admin/scheduler/jobs/${jobName}/executar`),
};

// Suporte
export const suporteAPI = {
  listarTickets: (params) => axios.get(`${API}/suporte/tickets`, { params }),
  criarTicket: (data) => axios.post(`${API}/suporte/tickets`, data),
  obterTicket: (id) => axios.get(`${API}/suporte/tickets/${id}`),
  enviarMensagem: (id, data) => axios.post(`${API}/suporte/tickets/${id}/mensagens`, data),
  fecharTicket: (id) => axios.post(`${API}/suporte/tickets/${id}/fechar`),
};

// Suporte (Admin)
export const adminSuporteAPI = {
  criarTicket: (data) => axios.post(`${API}/suporte/admin/tickets`, data),
  listarTickets: (params) => axios.get(`${API}/suporte/admin/tickets`, { params }),
  obterTicket: (numero_ticket) => axios.get(`${API}/suporte/admin/tickets/${numero_ticket}`),
  responderTicket: (numero_ticket, data) => axios.post(`${API}/suporte/admin/tickets/${numero_ticket}/mensagens`, data),
  atualizarStatus: (numero_ticket, data) => axios.put(`${API}/suporte/admin/tickets/${numero_ticket}/status`, data),
  atribuirTicket: (numero_ticket) => axios.put(`${API}/suporte/admin/tickets/${numero_ticket}/atribuir`),
  deletarTicket: (numero_ticket) => axios.delete(`${API}/suporte/admin/tickets/${numero_ticket}`),
  obterEstatisticas: () => axios.get(`${API}/suporte/admin/estatisticas`),
};

// Admin Transações (incluindo Cupons)
export const adminTransacoesAPI = {
  listarCupons: (params) => axios.get(`${API}/admin/transacoes/cupons`, { params }),
  criarCupom: (data) => axios.post(`${API}/admin/transacoes/cupons/criar`, data),
  desativarCupom: (codigo) => axios.put(`${API}/admin/transacoes/cupons/${encodeURIComponent(codigo)}/desativar`),
  deletarCupom: (codigo) => axios.delete(`${API}/admin/transacoes/cupons/${encodeURIComponent(codigo)}`),
  exportar: (formato, params) => axios.get(`${API}/admin/transacoes/exportar/${formato}`, {
    params,
    responseType: 'blob'
  }),
};

// Upload
export const uploadAPI = {
  uploadFile: (formData) => axios.post(`${API}/upload/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),
};
