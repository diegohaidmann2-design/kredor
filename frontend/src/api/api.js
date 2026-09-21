import axios from 'axios';
import { BACKEND_URL as ENV_BACKEND_URL } from '../config/env';
import { toast } from '../hooks/use-toast';

// 1. Configuração da URL base da API
export const BACKEND_URL = ENV_BACKEND_URL;

const API = `${BACKEND_URL}/api`;

// Interceptor de resposta: 403 de permissão de equipe vira aviso legível.
//
// Com as permissões de equipe, um botão que o membro não alcança responde 403 com uma mensagem
// já escrita para ele ("Você não tem a permissão X. Peça ao dono da conta."). Sem isto, cada
// tela precisaria tratar o caso, e a que esquecesse mostraria "erro desconhecido" — o membro
// acha que o sistema quebrou em vez de entender que é um bloqueio.
//
// Só em escrita (POST/PUT/PATCH/DELETE), por dois motivos: um GET de tela que o membro não
// pode ver nem sai, porque o ProtectedRoute barra antes; e as telas já mostram o próprio
// ErrorMessage quando a carga falha — avisar aqui também daria dois avisos para uma causa, que
// é justamente o que o gate de feedback do projeto proíbe.
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const detalhe = error?.response?.data?.detail;
    const metodo = (error?.config?.method || 'get').toUpperCase();
    const escrita = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(metodo);
    if (escrita && error?.response?.status === 403 && typeof detalhe === 'string'
        && (detalhe.includes('permissão') || detalhe.includes('dono da conta'))) {
      toast({
        variant: 'destructive',
        title: 'Acesso não liberado',
        description: detalhe,
      });
      // Marca para a tela poder pular o próprio aviso, se um dia quiser tratar o caso.
      error.permissaoAvisada = true;
    }
    return Promise.reject(error);
  }
);

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
  meusRecursos: () => axios.get(`${API}/auth/meus-recursos`),
  atualizarPerfil: (data) => axios.put(`${API}/auth/me`, data),
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

// Segurança (Painel Admin)
export const segurancaAPI = {
  resumo: () => axios.get(`${API}/seguranca/resumo`),
  loginBloqueios: () => axios.get(`${API}/seguranca/login-bloqueios`),
  webhooksSuspeitos: () => axios.get(`${API}/seguranca/webhooks-suspeitos`),
  desbloquearConta: (email) => axios.post(`${API}/seguranca/desbloquear-conta`, null, { params: { email } }),
  desbloquearIp: (ip) => axios.post(`${API}/seguranca/desbloquear-ip`, null, { params: { ip } }),
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
  simularPublico: (data) => axios.post(`${API}/emprestimos/simular-publico`, data),
  criar: (data) => axios.post(`${API}/emprestimos`, data),
  listar: (params) => axios.get(`${API}/emprestimos`, { params }),
  resumoAbertos: () => axios.get(`${API}/emprestimos/abertos/resumo`),
  obter: (id) => axios.get(`${API}/emprestimos/${id}`),
  atualizar: (id, data) => axios.put(`${API}/emprestimos/${id}`, data),
  listarParcelas: (id) => axios.get(`${API}/emprestimos/${id}/parcelas`),
  deletar: (id, hard = false) => axios.delete(`${API}/emprestimos/${id}`, { params: { hard } }),
  restaurar: (id) => axios.post(`${API}/emprestimos/${id}/restaurar`),
  quitarAberto: (id) => axios.post(`${API}/emprestimos/${id}/quitar`),
  prorrogar: (id, periodos) => axios.post(`${API}/emprestimos/${id}/prorrogar`, { periodos }),
  prorrogarPreview: (id, periodos) => axios.post(`${API}/emprestimos/${id}/prorrogar/preview`, { periodos }),
  reciboProrrogacao: (id, prorrogacaoId) => axios.get(`${API}/emprestimos/${id}/recibo-prorrogacao/${prorrogacaoId}`, {
    responseType: 'blob'
  }),
  enviarReciboProrrogacaoWhatsapp: (id, prorrogacaoId) => axios.post(`${API}/emprestimos/${id}/recibo-prorrogacao/${prorrogacaoId}/whatsapp`),
  amortizar: (id, data) => axios.post(`${API}/emprestimos/${id}/amortizar`, data),
  incorporarJuros: (id, data) => axios.post(`${API}/emprestimos/${id}/incorporar-juros`, data),
  rolarPeriodo: (id, periodos) => axios.post(`${API}/emprestimos/${id}/rolar-periodo`, { periodos }),
  listarAjustes: (id) => axios.get(`${API}/emprestimos/${id}/ajustes`),
  reciboAmortizacao: (id, pagamentoId) => axios.get(`${API}/emprestimos/${id}/recibo-amortizacao/${pagamentoId}`, {
    responseType: 'blob'
  }),
  enviarReciboWhatsapp: (id, pagamentoId) => axios.post(`${API}/emprestimos/${id}/recibo-amortizacao/${pagamentoId}/whatsapp`),
  estornarAjuste: (id, pagamentoId) => axios.post(`${API}/emprestimos/${id}/ajustes/${pagamentoId}/estornar`),
  exportar: (id, formato = 'pdf') => axios.get(`${API}/emprestimos/${id}/exportar`, {
    params: { formato },
    responseType: 'blob'
  }),
  compartilharPDF: (id) => axios.get(`${API}/emprestimos/${id}/compartilhar-pdf`, {
    responseType: 'blob'
  }),
  reciboQuitacao: (id) => axios.get(`${API}/emprestimos/${id}/recibo-quitacao`, {
    responseType: 'blob'
  }),
};

// Aceite de Empréstimo (link público)
export const aceiteEmprestimoAPI = {
  gerar: (emprestimoId) => axios.post(`${API}/aceite-emprestimo/gerar/${emprestimoId}`),
  regenerar: (emprestimoId) => axios.post(`${API}/aceite-emprestimo/regenerar/${emprestimoId}`),
  info: (token) => axios.get(`${API}/aceite-emprestimo/info/${token}`),
  confirmar: (token, formData) => axios.post(`${API}/aceite-emprestimo/confirmar/${token}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  obterAssinatura: (emprestimoId) => axios.get(`${API}/aceite-emprestimo/${emprestimoId}/assinatura`, { responseType: 'blob' }),
  baixarContratoPdf: (token) => axios.get(`${API}/aceite-emprestimo/contrato-pdf/${token}`, { responseType: 'blob' }),
  baixarContratoAssinado: (emprestimoId) => axios.get(`${API}/aceite-emprestimo/${emprestimoId}/contrato-assinado-pdf`, { responseType: 'blob' }),
};

// Pagamentos
export const pagamentosAPI = {
  criar: (data) => axios.post(`${API}/pagamentos`, data),
  // Quanto a parcela deve na data informada e o que sobraria com o valor digitado (não grava nada)
  previa: (data) => axios.post(`${API}/pagamentos/previa`, data),
  listar: (params) => axios.get(`${API}/pagamentos`, { params }),
  estornar: (id) => axios.delete(`${API}/pagamentos/${id}`),
  recibo: (id) => axios.get(`${API}/pagamentos/${id}/recibo`, { responseType: 'blob' }),
  enviarReciboWhatsapp: (id) => axios.post(`${API}/pagamentos/${id}/recibo/whatsapp`),
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
    enviarCobrancaParcela: (parcelaId, usarFila = true, templateId = null) => axios.post(`${API}/whatsapp/enviar-cobranca-parcela/${parcelaId}`, null, { params: { usar_fila: usarFila, template_id: templateId || undefined } }),
    previewCobrancaParcela: (parcelaId, templateId = null) => axios.get(`${API}/whatsapp/enviar-cobranca-parcela/${parcelaId}/preview`, { params: { template_id: templateId || undefined } }),
    enviarConfirmacaoPagamento: (pagamentoId) => axios.post(`${API}/whatsapp/enviar-confirmacao-pagamento/${pagamentoId}`),
    
    // Logs e Auditoria
    listarLogs: (params) => axios.get(`${API}/whatsapp/logs`, { params }),
    obterEstatisticasLogs: () => axios.get(`${API}/whatsapp/logs/estatisticas`),
    verificarStatusServico: () => axios.get(`${API}/whatsapp/status-servico`),
    
    // Templates
    listarTemplates: (tipo = null) => axios.get(`${API}/whatsapp/templates`, { params: { tipo } }),
    obterTemplate: (id) => axios.get(`${API}/whatsapp/templates/${id}`),
    criarTemplate: (dados) => axios.post(`${API}/whatsapp/templates`, null, { params: dados }),
    atualizarTemplate: (id, dados) => axios.put(`${API}/whatsapp/templates/${id}`, null, { params: dados }),
    excluirTemplate: (id) => axios.delete(`${API}/whatsapp/templates/${id}`),
    duplicarTemplate: (id, novo_nome) => axios.post(`${API}/whatsapp/templates/${id}/duplicar`, null, { params: { novo_nome } }),
    previewTemplate: (mensagem, dados_exemplo) => axios.post(`${API}/whatsapp/templates/preview`, dados_exemplo || {}, { params: { mensagem } }),
    restaurarTemplatesPadrao: () => axios.post(`${API}/whatsapp/templates/restaurar-padrao`),

    // Régua de Cobrança automática
    obterConfigRegua: () => axios.get(`${API}/whatsapp/regua/config`),
    atualizarConfigRegua: (dados) => axios.put(`${API}/whatsapp/regua/config`, dados),
    executarRegua: () => axios.post(`${API}/whatsapp/regua/executar`),
    historicoRegua: (limit = 50) => axios.get(`${API}/whatsapp/regua/historico`, { params: { limit } }),
    
    // Anti-Spam
    obterConfigAntiSpam: () => axios.get(`${API}/whatsapp/anti-spam/config`),
    atualizarConfigAntiSpam: (params) => axios.put(`${API}/whatsapp/anti-spam/config`, null, { params }),
    verificarStatusAntiSpam: () => axios.get(`${API}/whatsapp/anti-spam/status`),
    ativarWarmingUp: () => axios.post(`${API}/whatsapp/anti-spam/warming-up/ativar`),
    desativarWarmingUp: () => axios.post(`${API}/whatsapp/anti-spam/warming-up/desativar`),
    
    // Fila
    obterEstatisticasFila: () => axios.get(`${API}/whatsapp/fila/estatisticas`),
    processarFila: (limite = 100) => axios.post(`${API}/whatsapp/fila/processar`, null, { params: { limite } }),
    listarFila: (status = null, limite = 50) => axios.get(`${API}/whatsapp/fila/lista`, { params: { status, limite } }),
    cancelarMensagemFila: (filaId) => axios.delete(`${API}/whatsapp/fila/${filaId}`),
    reprocessarFalhadas: () => axios.post(`${API}/whatsapp/fila/reprocessar-falhadas`)
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
  cobrarEmMassa: (parcela_ids) => axios.post(`${API}/parcelas/cobrar-em-massa`, { parcela_ids }),
};

// Cadastro Público + Aprovação
export const cadastroPublicoAPI = {
  obterLink: () => axios.get(`${API}/cadastro-publico/link`),
  regenerarLink: () => axios.post(`${API}/cadastro-publico/regenerar-link`),
  info: (token) => axios.get(`${API}/cadastro-publico/info/${token}`),
  solicitar: (token, data) => axios.post(`${API}/cadastro-publico/solicitar/${token}`, data),
  solicitarMultipart: (token, formData) => axios.post(`${API}/cadastro-publico/solicitar/${token}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  listarSolicitacoes: (status) => axios.get(`${API}/cadastro-publico/solicitacoes`, { params: status ? { status } : {} }),
  contadorPendentes: () => axios.get(`${API}/cadastro-publico/solicitacoes/contador`),
  aprovar: (id) => axios.post(`${API}/cadastro-publico/solicitacoes/${id}/aprovar`),
  rejeitar: (id, motivo) => axios.post(`${API}/cadastro-publico/solicitacoes/${id}/rejeitar`, { motivo }),
  excluir: (id) => axios.delete(`${API}/cadastro-publico/solicitacoes/${id}`),
  obterAnexo: (solicitacaoId, tipo) => axios.get(`${API}/cadastro-publico/solicitacoes/${solicitacaoId}/anexo/${tipo}`, { responseType: 'blob' }),
  obterAnexoCliente: (clienteId, tipo) => axios.get(`${API}/cadastro-publico/clientes/${clienteId}/anexo/${tipo}`, { responseType: 'blob' }),
  baixarPdf: (solicitacaoId) => axios.get(`${API}/cadastro-publico/solicitacoes/${solicitacaoId}/pdf`, { responseType: 'blob' }),
  baixarPdfCliente: (clienteId) => axios.get(`${API}/cadastro-publico/clientes/${clienteId}/ficha-pdf`, { responseType: 'blob' }),
};

// Assinaturas / Stripe / Asaas
export const assinaturasAPI = {
  listarPlanos: () => axios.get(`${API}/assinaturas/planos`),
  obterSocialProof: () => axios.get(`${API}/assinaturas/social-proof`),
  checkoutAsaas: (data) => axios.post(`${API}/assinaturas/checkout-asaas`, data),
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
  // SyncPay
  checkoutSyncPay: (data) => axios.post(`${API}/assinaturas/checkout-syncpay`, data),
  verificarStatusSyncPay: (transactionId) => axios.get(`${API}/assinaturas/syncpay-status/${transactionId}`),
  validarCupom: (codigo, email) => axios.get(`${API}/assinaturas/cupom/validar/${codigo}`, { params: { email } }),
  obterTransacao: (id, config) => axios.get(`${API}/assinaturas/transacao/${id}`, config),
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
  resetarSenha: (id) => axios.post(`${API}/superadmin/usuarios/${id}/resetar-senha`),
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
  metricas: () => axios.get(`${API}/admin/transacoes/metricas`),
  listar: (params) => axios.get(`${API}/admin/transacoes/`, { params }),
  listarPixPendentes: (params) => axios.get(`${API}/admin/transacoes/pix-pendentes`, { params }),
  listarCartoesRecusados: (params) => axios.get(`${API}/admin/transacoes/cartoes-recusados`, { params }),
  enviarEmail: (id) => axios.post(`${API}/admin/transacoes/${id}/enviar-email`),
  gerarCupomTransacao: (id, desconto) => axios.post(`${API}/admin/transacoes/${id}/gerar-cupom`, null, { params: { desconto_percentual: desconto } }),
};

// Consultas (CPF, etc.)
export const consultasAPI = {
  cpf: (cpf) => axios.post(`${API}/consultas/cpf`, { cpf }),
  cpfPremium: (cpf) => axios.post(`${API}/consultas/cpf-premium`, { cpf }),
  cnpj: (cnpj) => axios.post(`${API}/consultas/cnpj`, { cnpj }),
  telefone: (telefone) => axios.post(`${API}/consultas/telefone`, { telefone }),
  nome: (nome) => axios.post(`${API}/consultas/nome`, { nome }),
  cpfDividas: (cpf) => axios.post(`${API}/consultas/cpf-dividas`, { cpf }),
  cnpjDividas: (cnpj) => axios.post(`${API}/consultas/cnpj-dividas`, { cnpj }),
  facial: (foto) => axios.post(`${API}/consultas/reconhecimento-facial`, { foto }),
  historico: (params = {}) => axios.get(`${API}/consultas/historico`, { params }),
  obter: (id) => axios.get(`${API}/consultas/${id}`),
  excluir: (id) => axios.delete(`${API}/consultas/${id}`),
  pdf: (id) => axios.get(`${API}/consultas/${id}/pdf`, { responseType: 'blob' }),
  vincular: (id, data) => axios.post(`${API}/consultas/${id}/vincular`, data),
};

// Carteira de Consultas (usuário)
export const carteiraAPI = {
  resumo: () => axios.get(`${API}/carteira/`),
  precos: () => axios.get(`${API}/carteira/precos`),
  movimentos: (params = {}) => axios.get(`${API}/carteira/movimentos`, { params }),
  gateways: () => axios.get(`${API}/carteira/gateways`),
  recargaAsaas: (valor) => axios.post(`${API}/carteira/recarga/asaas`, { valor }),
  recargaSyncpay: (valor) => axios.post(`${API}/carteira/recarga/syncpay`, { valor }),
  statusRecarga: (id) => axios.get(`${API}/carteira/recarga/${id}/status`),
  configurarAlerta: (data) => axios.put(`${API}/carteira/alerta-saldo`, data),
};

// Admin - Carteiras
export const adminCarteirasAPI = {
  dashboard: () => axios.get(`${API}/admin/carteiras/dashboard`),
  listar: (params = {}) => axios.get(`${API}/admin/carteiras/`, { params }),
  detalhes: (ownerId) => axios.get(`${API}/admin/carteiras/${ownerId}`),
  movimentos: (ownerId, params = {}) => axios.get(`${API}/admin/carteiras/${ownerId}/movimentos`, { params }),
  ajuste: (ownerId, data) => axios.post(`${API}/admin/carteiras/${ownerId}/ajuste`, data),
  precos: () => axios.get(`${API}/admin/carteiras/precos`),
  atualizarPreco: (tipo, data) => axios.put(`${API}/admin/carteiras/precos/${tipo}`, data),
};

// Upload
export const uploadAPI = {
  uploadFile: (formData) => axios.post(`${API}/upload/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),
};

// Backup & Restore (Admin) — Authorization vai pelo interceptor global
export const backupAPI = {
  listar: () => axios.get(`${API}/backup/listar`),
  status: () => axios.get(`${API}/backup/status`),
  logs: (limit = 20) => axios.get(`${API}/backup/logs`, { params: { limit } }),
  criar: () => axios.post(`${API}/backup/criar`),
  importar: (formData) => axios.post(`${API}/backup/importar`, formData),
  restaurar: (nome) => axios.post(`${API}/backup/restaurar/${encodeURIComponent(nome)}`),
  deletar: (nome) => axios.delete(`${API}/backup/deletar/${encodeURIComponent(nome)}`),
  download: (nome) => axios.get(`${API}/backup/download/${encodeURIComponent(nome)}`, { responseType: 'blob' }),
};

// Portal do Cliente
export const portalAPI = {
  meuPerfil: () => axios.get(`${API}/portal/meu-perfil`),
  emprestimos: () => axios.get(`${API}/portal/emprestimos`),
  proximasParcelas: () => axios.get(`${API}/portal/proximas-parcelas`),
  emprestimo: (id) => axios.get(`${API}/portal/emprestimo/${id}`),
  historicoPagamentos: (id) => axios.get(`${API}/portal/emprestimo/${id}/historico-pagamentos`),
};

// Informações de timezone
export const timezoneAPI = {
  info: () => axios.get(`${API}/timezone-info`),
};

// Consulta de CEP (ViaCEP — serviço externo, fica fora do axios com token)
export const cepAPI = {
  consultar: async (cep) => {
    const limpo = String(cep || '').replace(/\D/g, '');
    const resp = await fetch(`https://viacep.com.br/ws/${limpo}/json/`);
    if (!resp.ok) throw new Error('Erro ao consultar CEP');
    return resp.json();
  },
};

// Blog público (SEO)
export const blogAPI = {
  listar: () => axios.get(`${API}/blog/posts`),
  obter: (slug) => axios.get(`${API}/blog/posts/${slug}`),
};
