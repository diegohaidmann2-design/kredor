import React, { useState, useEffect } from 'react';
import { adminTransacoesAPI } from '../api/api';
import Layout from '../components/Layout';
import { toast } from '../hooks/use-toast';

const AdminCupons = () => {
  const [loading, setLoading] = useState(true);
  const [cupons, setCupons] = useState([]);
  const [estatisticas, setEstatisticas] = useState(null);
  const [filtros, setFiltros] = useState({
    ativo: null,
    tipo: '',
    skip: 0,
    limit: 50
  });
  const [modalAberto, setModalAberto] = useState(null);
  const [formNovoCupom, setFormNovoCupom] = useState({
    codigo: '',
    desconto_percentual: 10,
    valido_ate: '',
    usuario_email: '',
    limite_uso: 1,
    descricao: ''
  });

  useEffect(() => {
    carregarCupons();
  }, [filtros]);

  const carregarCupons = async () => {
    try {
      setLoading(true);

      const params = {};
      if (filtros.ativo !== null) params.ativo = filtros.ativo;
      if (filtros.tipo) params.tipo = filtros.tipo;
      params.skip = filtros.skip;
      params.limit = filtros.limit;

      const response = await adminTransacoesAPI.listarCupons(params);

      setCupons(response.data.cupons || []);
      setEstatisticas(response.data.estatisticas);
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível carregar cupons.", variant: 'destructive' });
      console.error('Erro ao carregar cupons:', error);
      showToast('Erro ao carregar cupons', 'error');
    } finally {
      setLoading(false);
    }
  };

  const criarCupom = async () => {
    try {
      const payload = {
        ...formNovoCupom,
        desconto_percentual: parseInt(formNovoCupom.desconto_percentual),
        limite_uso: parseInt(formNovoCupom.limite_uso)
      };

      await adminTransacoesAPI.criarCupom(payload);

      showToast('Cupom criado com sucesso!', 'success');
      setModalAberto(null);
      setFormNovoCupom({
        codigo: '',
        desconto_percentual: 10,
        valido_ate: '',
        usuario_email: '',
        limite_uso: 1,
        descricao: ''
      });
      carregarCupons();
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível criar cupom.", variant: 'destructive' });
      console.error('Erro ao criar cupom:', error);
      showToast(error.response?.data?.detail || 'Erro ao criar cupom', 'error');
    }
  };

  const desativarCupom = async (codigo) => {
    if (!window.confirm(`Deseja desativar o cupom ${codigo}?`)) return;

    try {
      await adminTransacoesAPI.desativarCupom(codigo);
      showToast('Cupom desativado com sucesso', 'success');
      carregarCupons();
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível desativar cupom.", variant: 'destructive' });
      console.error('Erro ao desativar cupom:', error);
      showToast(error.response?.data?.detail || 'Erro ao desativar cupom', 'error');
    }
  };

  const deletarCupom = async (codigo) => {
    if (!window.confirm(`Deseja deletar permanentemente o cupom ${codigo}?`)) return;

    try {
      await adminTransacoesAPI.deletarCupom(codigo);
      showToast('Cupom deletado com sucesso', 'success');
      carregarCupons();
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível deletar cupom.", variant: 'destructive' });
      console.error('Erro ao deletar cupom:', error);
      showToast(error.response?.data?.detail || 'Erro ao deletar cupom', 'error');
    }
  };

  const showToast = (message, type = 'info') => {
    const bgColors = {
      success: 'bg-green-600',
      error: 'bg-red-600',
      info: 'bg-blue-600'
    };

    const toastEl = document.createElement('div');
    toastEl.className = `fixed top-4 right-4 ${bgColors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity`;
    toastEl.textContent = message;
    document.body.appendChild(toastEl);

    setTimeout(() => {
      toastEl.style.opacity = '0';
      setTimeout(() => toastEl.remove(), 300);
    }, 3000);
  };

  const formatarData = (data) => {
    if (!data) return '-';
    return new Date(data).toLocaleString('pt-BR');
  };

  const getStatusBadge = (cupom) => {
    const agora = new Date();
    const validade = new Date(cupom.valido_ate);

    if (cupom.usado) {
      return <span className="px-2 py-1 bg-gray-500/10 text-gray-400 border border-gray-500/30 rounded-full text-xs font-semibold">USADO</span>;
    }

    if (validade < agora) {
      return <span className="px-2 py-1 bg-orange-500/10 text-orange-400 border border-orange-500/30 rounded-full text-xs font-semibold">EXPIRADO</span>;
    }

    return <span className="px-2 py-1 bg-green-500/10 text-green-400 border border-green-500/30 rounded-full text-xs font-semibold">ATIVO</span>;
  };

  if (loading && !estatisticas) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-cabinet font-black text-3xl sm:text-4xl tracking-tighter text-foreground">Gestão de Cupons</h1>
              <p className="text-muted-foreground mt-1">
                Crie e gerencie cupons de desconto
              </p>
            </div>
            <button
              onClick={() => setModalAberto('criar')}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Criar Cupom
            </button>
          </div>

          {/* Cards de Estatísticas */}
          {estatisticas && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-card rounded-lg p-6 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Cupons Ativos</p>
                    <p className="text-3xl font-bold text-green-400 mt-1">{estatisticas.ativos}</p>
                  </div>
                  <div className="p-3 bg-green-500/10 rounded-lg">
                    <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-card rounded-lg p-6 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Cupons Usados</p>
                    <p className="text-3xl font-bold text-blue-400 mt-1">{estatisticas.usados}</p>
                  </div>
                  <div className="p-3 bg-blue-500/10 rounded-lg">
                    <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="bg-card rounded-lg p-6 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Cupons Expirados</p>
                    <p className="text-3xl font-bold text-orange-400 mt-1">{estatisticas.expirados}</p>
                  </div>
                  <div className="p-3 bg-orange-500/10 rounded-lg">
                    <svg className="w-8 h-8 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Filtros */}
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <select
                value={filtros.ativo === null ? '' : filtros.ativo}
                onChange={(e) => setFiltros({ ...filtros, ativo: e.target.value === '' ? null : e.target.value === 'true', skip: 0 })}
                className="px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">Todos os Status</option>
                <option value="true">Apenas Ativos</option>
                <option value="false">Usados/Expirados</option>
              </select>

              <select
                value={filtros.tipo}
                onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value, skip: 0 })}
                className="px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">Todos os Tipos</option>
                <option value="manual">Criados Manualmente</option>
                <option value="remarketing">Remarketing Automático</option>
              </select>

              <button
                onClick={() => setFiltros({ ativo: null, tipo: '', skip: 0, limit: 50 })}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
              >
                Limpar Filtros
              </button>
            </div>
          </div>

          {/* Tabela de Cupons */}
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Código</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Desconto</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Validade</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Email</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Tipo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {cupons.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="px-4 py-8 text-center text-muted-foreground">
                        Nenhum cupom encontrado
                      </td>
                    </tr>
                  ) : (
                    cupons.map((cupom) => (
                      <tr key={cupom.id} className="hover:bg-muted/30 transition">
                        <td className="px-4 py-3">
                          <span className="font-mono font-bold text-purple-400">{cupom.codigo}</span>
                          {cupom.descricao && (
                            <p className="text-xs text-muted-foreground mt-1">{cupom.descricao}</p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-green-400 font-semibold">{cupom.desconto_percentual}%</span>
                        </td>
                        <td className="px-4 py-3 text-sm text-foreground">
                          {formatarData(cupom.valido_ate)}
                        </td>
                        <td className="px-4 py-3 text-sm text-foreground">
                          {cupom.usuario_email || <span className="text-muted-foreground">Qualquer email</span>}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-xs ${cupom.tipo === 'manual' ? 'bg-blue-500/10 text-blue-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                            {cupom.tipo === 'manual' ? 'Manual' : 'Remarketing'}
                          </span>
                        </td>
                        <td className="px-4 py-3">{getStatusBadge(cupom)}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            {!cupom.usado && new Date(cupom.valido_ate) > new Date() && (
                              <button
                                onClick={() => desativarCupom(cupom.codigo)}
                                className="p-2 bg-orange-500/10 text-orange-400 rounded hover:bg-orange-500/20 transition"
                                title="Desativar"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                                </svg>
                              </button>
                            )}
                            {!cupom.usado && (
                              <button
                                onClick={() => deletarCupom(cupom.codigo)}
                                className="p-2 bg-red-500/10 text-red-400 rounded hover:bg-red-500/20 transition"
                                title="Deletar"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Modal Criar Cupom */}
          {modalAberto === 'criar' && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setModalAberto(null)}>
              <div className="bg-card rounded-lg p-6 max-w-2xl w-full" onClick={(e) => e.stopPropagation()}>
                <h3 className="text-xl font-bold text-foreground mb-4">Criar Novo Cupom</h3>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Código do Cupom (deixe vazio para gerar automaticamente)
                    </label>
                    <input
                      type="text"
                      value={formNovoCupom.codigo}
                      onChange={(e) => setFormNovoCupom({ ...formNovoCupom, codigo: e.target.value.toUpperCase().replace(/\s/g, '') })}
                      placeholder="Ex: PROMO2024"
                      className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 font-mono"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">
                        Desconto (%)
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={formNovoCupom.desconto_percentual}
                        onChange={(e) => setFormNovoCupom({ ...formNovoCupom, desconto_percentual: e.target.value })}
                        className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">
                        Limite de Uso
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={formNovoCupom.limite_uso}
                        onChange={(e) => setFormNovoCupom({ ...formNovoCupom, limite_uso: e.target.value })}
                        className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Válido até
                    </label>
                    <input
                      type="datetime-local"
                      value={formNovoCupom.valido_ate}
                      onChange={(e) => setFormNovoCupom({ ...formNovoCupom, valido_ate: e.target.value })}
                      className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Deixe vazio para 30 dias a partir de agora
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Email Específico (opcional)
                    </label>
                    <input
                      type="email"
                      value={formNovoCupom.usuario_email}
                      onChange={(e) => setFormNovoCupom({ ...formNovoCupom, usuario_email: e.target.value })}
                      placeholder="usuario@exemplo.com"
                      className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Deixe vazio para permitir qualquer email
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">
                      Descrição (opcional)
                    </label>
                    <textarea
                      value={formNovoCupom.descricao}
                      onChange={(e) => setFormNovoCupom({ ...formNovoCupom, descricao: e.target.value })}
                      placeholder="Ex: Promoção Black Friday 2024"
                      rows="2"
                      className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={criarCupom}
                    className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
                  >
                    Criar Cupom
                  </button>
                  <button
                    onClick={() => setModalAberto(null)}
                    className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default AdminCupons;
