import React, { useState } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { relatoriosAPI } from '../api/api';
import { PageHeader, SectionCard, FormField } from '../components/uikit';
import { FileText, FileSpreadsheet, BarChart3, AlertTriangle, Wallet, ClipboardList, Info, Loader2 } from 'lucide-react';

const RAPIDOS = [
  { tipo: 'fluxo_caixa', Icon: BarChart3, titulo: 'Fluxo de Caixa', desc: 'Entradas e saídas do período', tone: 'text-blue-400', testid: 'rapido-fluxo-caixa' },
  { tipo: 'inadimplencia', Icon: AlertTriangle, titulo: 'Clientes Inadimplentes', desc: 'Lista de devedores em atraso', tone: 'text-amber-400', testid: 'rapido-inadimplencia' },
  { tipo: 'pagamentos', Icon: Wallet, titulo: 'Receitas do Mês', desc: 'Pagamentos recebidos', tone: 'text-emerald-400', testid: 'rapido-pagamentos' },
  { tipo: 'emprestimos', Icon: ClipboardList, titulo: 'Empréstimos Ativos', desc: 'Todos os empréstimos cadastrados', tone: 'text-foreground', testid: 'rapido-emprestimos' },
];

const TIPOS = [
  { dot: 'bg-blue-500', label: 'Empréstimos', desc: 'Lista completa de todos os empréstimos' },
  { dot: 'bg-emerald-500', label: 'Pagamentos', desc: 'Histórico de pagamentos recebidos' },
  { dot: 'bg-violet-500', label: 'Clientes', desc: 'Cadastro completo de clientes' },
  { dot: 'bg-rose-500', label: 'Inadimplência', desc: 'Parcelas em atraso' },
  { dot: 'bg-amber-500', label: 'Fluxo de Caixa', desc: 'Resumo de entradas e saídas' },
];

const Relatorios = () => {
  const [tipoRelatorio, setTipoRelatorio] = useState('emprestimos');
  const [formato, setFormato] = useState('pdf');
  const [periodo, setPeriodo] = useState('mes');
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const modal = useModal();

  const baixar = (blob, tipo, fmt) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `relatorio_${tipo}_${new Date().toISOString().split('T')[0]}.${fmt === 'pdf' ? 'pdf' : 'xlsx'}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  const handleGerar = async () => {
    try {
      setLoading(true);
      setError('');
      const data = {
        tipo: tipoRelatorio,
        formato,
        periodo,
        data_inicio: periodo === 'personalizado' ? dataInicio : null,
        data_fim: periodo === 'personalizado' ? dataFim : null,
      };
      const response = await relatoriosAPI.gerar(data);
      const blob = new Blob([response.data], {
        type: formato === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      baixar(blob, tipoRelatorio, formato);
      modal.success('Relatório Gerado!', 'O download do relatório iniciou automaticamente.');
    } catch (err) {
      console.error('Erro ao gerar relatório:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao gerar relatório. Tente novamente.';
      modal.error('Erro ao gerar relatório', typeof errorMsg === 'string' ? errorMsg : 'Erro ao gerar relatório');
    } finally {
      setLoading(false);
    }
  };

  const handleRelatorioRapido = async (tipo) => {
    setTipoRelatorio(tipo);
    setPeriodo('mes');
    setFormato('pdf');
    try {
      setLoading(true);
      setError('');
      const response = await relatoriosAPI.gerar({ tipo, formato: 'pdf', periodo: 'mes' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      baixar(blob, tipo, 'pdf');
    } catch (err) {
      console.error('Erro ao gerar relatório:', err);
      const errorMsg = err.response?.data?.detail || 'Erro ao gerar relatório. Tente novamente.';
      setError(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
    } finally {
      setLoading(false);
    }
  };

  const selectCls = 'w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/40';

  return (
    <Layout>
      <div className="container mx-auto px-4 sm:px-6 py-8 font-satoshi">
        <PageHeader
          title="Relatórios"
          subtitle="Gere relatórios personalizados em PDF ou Excel"
          testId="relatorios-title"
        />

        {error && (
          <div className="mb-6 bg-rose-500/10 ring-1 ring-rose-500/30 text-rose-400 px-4 py-3 rounded-lg" data-testid="error-message">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <SectionCard testId="config-relatorio">
            <h2 className="font-cabinet font-bold text-lg text-foreground mb-6">Configurar Relatório</h2>

            <div className="space-y-5">
              <FormField label="Tipo de Relatório">
                <select value={tipoRelatorio} onChange={(e) => setTipoRelatorio(e.target.value)} className={selectCls} data-testid="select-tipo-relatorio">
                  <option value="emprestimos">Empréstimos</option>
                  <option value="pagamentos">Pagamentos</option>
                  <option value="clientes">Clientes</option>
                  <option value="inadimplencia">Inadimplência</option>
                  <option value="fluxo_caixa">Fluxo de Caixa</option>
                </select>
              </FormField>

              <FormField label="Formato">
                <div className="flex gap-3">
                  {[
                    { v: 'pdf', label: 'PDF', Icon: FileText, tone: 'text-rose-400', testid: 'formato-pdf' },
                    { v: 'excel', label: 'Excel', Icon: FileSpreadsheet, tone: 'text-emerald-400', testid: 'formato-excel' },
                  ].map((f) => (
                    <button
                      key={f.v}
                      type="button"
                      onClick={() => setFormato(f.v)}
                      data-testid={f.testid}
                      className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md ring-1 transition-colors text-sm font-medium ${
                        formato === f.v ? 'ring-emerald-500/40 bg-emerald-500/10 text-foreground' : 'ring-border text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <f.Icon className={`w-4 h-4 ${f.tone}`} strokeWidth={1.75} />
                      {f.label}
                    </button>
                  ))}
                </div>
              </FormField>

              <FormField label="Período">
                <select value={periodo} onChange={(e) => setPeriodo(e.target.value)} className={selectCls} data-testid="select-periodo">
                  <option value="hoje">Hoje</option>
                  <option value="semana">Última Semana</option>
                  <option value="mes">Último Mês</option>
                  <option value="trimestre">Último Trimestre</option>
                  <option value="ano">Último Ano</option>
                  <option value="personalizado">Personalizado</option>
                </select>
              </FormField>

              {periodo === 'personalizado' && (
                <div className="grid grid-cols-2 gap-4">
                  <FormField label="Data Início">
                    <input type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} className={selectCls} data-testid="input-data-inicio" />
                  </FormField>
                  <FormField label="Data Fim">
                    <input type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} className={selectCls} data-testid="input-data-fim" />
                  </FormField>
                </div>
              )}

              <div className="pt-2">
                <Button onClick={handleGerar} variant="primary" className="w-full" testId="gerar-relatorio-button" disabled={loading}>
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Gerando...
                    </span>
                  ) : (
                    `Gerar Relatório (${formato.toUpperCase()})`
                  )}
                </Button>
              </div>
            </div>
          </SectionCard>

          <div className="space-y-6">
            <SectionCard testId="relatorios-rapidos">
              <h2 className="font-cabinet font-bold text-lg text-foreground mb-1">Relatórios Rápidos</h2>
              <p className="text-sm text-muted-foreground mb-4">Clique para gerar PDF do mês atual</p>
              <div className="space-y-3">
                {RAPIDOS.map((r) => (
                  <button
                    key={r.tipo}
                    onClick={() => handleRelatorioRapido(r.tipo)}
                    disabled={loading}
                    className="w-full text-left px-4 py-3 rounded-lg ring-1 ring-border hover:ring-foreground/20 hover:bg-muted/40 transition-all disabled:opacity-50 flex items-center gap-3"
                    data-testid={r.testid}
                  >
                    <span className="h-9 w-9 rounded-md bg-muted/60 flex items-center justify-center shrink-0">
                      <r.Icon className={`w-5 h-5 ${r.tone}`} strokeWidth={1.75} />
                    </span>
                    <div>
                      <div className="font-medium text-foreground">{r.titulo}</div>
                      <div className="text-xs text-muted-foreground">{r.desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            </SectionCard>

            <div className="rounded-xl bg-blue-500/[0.06] ring-1 ring-blue-500/20 p-4">
              <h3 className="font-semibold text-blue-400 mb-2 flex items-center gap-2">
                <Info className="w-4 h-4" strokeWidth={1.75} />
                Dica
              </h3>
              <p className="text-sm text-blue-400/80">
                Os relatórios em PDF são ideais para impressão e compartilhamento. Use Excel para análises mais detalhadas com filtros e gráficos.
              </p>
            </div>

            <SectionCard>
              <h2 className="font-cabinet font-bold text-base text-foreground mb-3">Tipos de Relatório</h2>
              <div className="space-y-2.5 text-sm">
                {TIPOS.map((t) => (
                  <div key={t.label} className="flex items-start gap-2.5">
                    <span className={`mt-1.5 h-1.5 w-1.5 rounded-full ${t.dot} shrink-0`} />
                    <div className="text-foreground"><strong>{t.label}:</strong> {t.desc}</div>
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Relatorios;
