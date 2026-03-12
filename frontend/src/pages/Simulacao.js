import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import ErrorMessage from '../components/ErrorMessage';
import { emprestimosAPI } from '../api/api';
import { formatarMoeda, formatarData, getMetodoCalculoLabel } from '../utils/formatters';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import useAutosave, { useUnsavedChangesWarning } from '../hooks/useAutosave';
import DraftRecovery, { SaveStatusBadge } from '../components/DraftRecovery';
import { getDraftTimestamp } from '../utils/storageUtils';

const Simulacao = () => {
  const [formData, setFormData] = useState({
    valor_principal: '',
    taxa_juros_mensal: '',
    prazo_meses: '',
    metodo_calculo: 'tabela_price',
    periodo_carencia_meses: 0,
    taxa_multa_atraso: 2.0,
    taxa_juros_mora_diario: 0.033
  });
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showDraftRecovery, setShowDraftRecovery] = useState(false);

  // Sistema de autosave
  const autosave = useAutosave('simulacao', formData, {
    enabled: true,
    delay: 3000,
    encrypt: false,
  });

  // Aviso ao sair
  useUnsavedChangesWarning(
    autosave.hasUnsavedChanges,
    'Você tem uma simulação em andamento. Deseja sair?'
  );

  useEffect(() => {
    if (autosave.exists()) {
      setShowDraftRecovery(true);
    }
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    setError('');
  };

  const handleSimular = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const data = {
        ...formData,
        valor_principal: parseFloat(formData.valor_principal),
        taxa_juros_mensal: parseFloat(formData.taxa_juros_mensal),
        prazo_meses: parseInt(formData.prazo_meses),
        periodo_carencia_meses: parseInt(formData.periodo_carencia_meses || 0),
        taxa_multa_atraso: parseFloat(formData.taxa_multa_atraso),
        taxa_juros_mora_diario: parseFloat(formData.taxa_juros_mora_diario)
      };

      const response = await emprestimosAPI.simular(data);
      setResultado(response.data);
      autosave.clear(); // Limpar após simulação bem-sucedida
    } catch (err) {
      console.error('Erro ao simular:', err);
      setError(err.response?.data?.detail || 'Erro ao simular empréstimo');
    } finally {
      setLoading(false);
    }
  };

  // Funções de recuperação de rascunho
  const handleRecoverDraft = () => {
    const draft = autosave.restore();
    if (draft) {
      setFormData(draft);
      setShowDraftRecovery(false);
    }
  };

  const handleDiscardDraft = () => {
    autosave.clear();
    setShowDraftRecovery(false);
  };

  const handleClearDraft = () => {
    if (window.confirm('Deseja limpar o rascunho salvo?')) {
      autosave.clear();
    }
  };

  const exportarPDF = () => {
    if (!resultado) return;

    const doc = new jsPDF();

    // Configurações
    const pageWidth = doc.internal.pageSize.width;
    const margin = 15;
    let yPosition = 20;

    // Título
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.text('Simulação de Empréstimo', margin, yPosition);

    yPosition += 10;
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100);
    doc.text(`Gerado em: ${new Date().toLocaleDateString('pt-BR')} às ${new Date().toLocaleTimeString('pt-BR')}`, margin, yPosition);

    yPosition += 15;

    // Resumo da Simulação
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(0);
    doc.text('Resumo da Simulação', margin, yPosition);
    yPosition += 8;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    const resumoData = [
      ['Método de Cálculo', getMetodoCalculoLabel(resultado.metodo_calculo)],
      ['Valor Principal', formatarMoeda(resultado.valor_principal)],
      ['Taxa de Juros', `${resultado.taxa_juros_mensal}% ao mês`],
      ['Prazo', `${resultado.prazo_meses} meses`],
    ];

    if (resultado.periodo_carencia_meses > 0) {
      resumoData.push(['Período de Carência', `${resultado.periodo_carencia_meses} meses`]);
    }

    resumoData.push(
      ['Total de Juros', formatarMoeda(resultado.valor_total_juros)],
      ['Valor Total', formatarMoeda(resultado.valor_total_com_juros)]
    );

    autoTable(doc, {
      startY: yPosition,
      head: [],
      body: resumoData,
      theme: 'striped',
      styles: { fontSize: 10 },
      columnStyles: {
        0: { fontStyle: 'bold', cellWidth: 60 },
        1: { cellWidth: 'auto' }
      },
      margin: { left: margin, right: margin }
    });

    yPosition = doc.lastAutoTable.finalY + 15;

    // Tabela de Parcelas
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('Parcelas', margin, yPosition);
    yPosition += 5;

    const parcelasData = resultado.parcelas.map(p => [
      p.numero_parcela.toString(),
      formatarData(p.data_vencimento),
      formatarMoeda(p.valor_principal),
      formatarMoeda(p.valor_juros),
      formatarMoeda(p.valor_total),
      formatarMoeda(p.saldo_devedor)
    ]);

    autoTable(doc, {
      startY: yPosition,
      head: [['#', 'Vencimento', 'Principal', 'Juros', 'Total', 'Saldo']],
      body: parcelasData,
      theme: 'grid',
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [99, 102, 241], textColor: 255, fontStyle: 'bold' },
      columnStyles: {
        0: { cellWidth: 15, halign: 'center' },
        1: { cellWidth: 30, halign: 'center' },
        2: { cellWidth: 27, halign: 'right' },
        3: { cellWidth: 27, halign: 'right' },
        4: { cellWidth: 27, halign: 'right' },
        5: { cellWidth: 27, halign: 'right' }
      },
      margin: { left: margin, right: margin }
    });

    // Salvar PDF
    doc.save(`simulacao-emprestimo-${new Date().getTime()}.pdf`);
  };

  const compartilharWhatsApp = () => {
    if (!resultado) return;

    const mensagem = `*📊 Simulação de Empréstimo*\n\n` +
      `*Método:* ${getMetodoCalculoLabel(resultado.metodo_calculo)}\n` +
      `*Valor Principal:* ${formatarMoeda(resultado.valor_principal)}\n` +
      `*Taxa de Juros:* ${resultado.taxa_juros_mensal}% ao mês\n` +
      `*Prazo:* ${resultado.prazo_meses} meses\n` +
      (resultado.periodo_carencia_meses > 0 ? `*Carência:* ${resultado.periodo_carencia_meses} meses\n` : '') +
      `\n*💰 Resumo Financeiro:*\n` +
      `Total de Juros: ${formatarMoeda(resultado.valor_total_juros)}\n` +
      `*Valor Total: ${formatarMoeda(resultado.valor_total_com_juros)}*\n\n` +
      `_Simulação gerada pelo sistema Gestor Cred_`;

    const url = `https://wa.me/?text=${encodeURIComponent(mensagem)}`;
    window.open(url, '_blank');
  };

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground" data-testid="simulacao-title">
              Simulação de Empréstimo
            </h1>
            <p className="text-muted-foreground mt-1">
              Simule diferentes cenários de empréstimo
            </p>
          </div>
          <SaveStatusBadge
            isSaving={autosave.isSaving}
            lastSaved={autosave.lastSaved}
            hasUnsavedChanges={autosave.hasUnsavedChanges}
            onClearDraft={handleClearDraft}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Formulário */}
          <div className="bg-card rounded-lg border border-border p-6" data-testid="simulacao-form">
            <h2 className="text-xl font-bold text-foreground mb-6">
              Parâmetros do Empréstimo
            </h2>

            {error && <ErrorMessage message={error} />}

            <form onSubmit={handleSimular} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Valor Principal (R$) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  name="valor_principal"
                  value={formData.valor_principal}
                  onChange={handleChange}
                  required
                  step="0.01"
                  min="0"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="input-valor-principal"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Taxa de Juros Mensal (%) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  name="taxa_juros_mensal"
                  value={formData.taxa_juros_mensal}
                  onChange={handleChange}
                  required
                  step="0.01"
                  min="0"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="input-taxa-juros"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Prazo (meses) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  name="prazo_meses"
                  value={formData.prazo_meses}
                  onChange={handleChange}
                  required
                  min="1"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="input-prazo-meses"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Método de Cálculo <span className="text-red-500">*</span>
                </label>
                <select
                  name="metodo_calculo"
                  value={formData.metodo_calculo}
                  onChange={handleChange}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="select-metodo-calculo"
                >
                  <option value="tabela_price">Tabela Price (Parcelas Fixas)</option>
                  <option value="sac">SAC (Amortização Constante)</option>
                  <option value="juros_simples">Juros Simples</option>
                  <option value="juros_compostos">Juros Compostos</option>
                  <option value="apenas_juros">Apenas Juros (Capital no Final)</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  {formData.metodo_calculo === 'tabela_price' && 'Parcelas fixas ao longo do prazo'}
                  {formData.metodo_calculo === 'sac' && 'Amortização constante, parcelas decrescentes'}
                  {formData.metodo_calculo === 'juros_simples' && 'Juros calculados sobre o valor inicial'}
                  {formData.metodo_calculo === 'juros_compostos' && 'Juros sobre juros'}
                  {formData.metodo_calculo === 'apenas_juros' && 'Paga somente juros mensais, capital pago no final'}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Período de Carência (meses)
                </label>
                <input
                  type="number"
                  name="periodo_carencia_meses"
                  value={formData.periodo_carencia_meses}
                  onChange={handleChange}
                  min="0"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="input-carencia"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Durante a carência, paga-se apenas juros
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Multa por Atraso (%)
                  </label>
                  <input
                    type="number"
                    name="taxa_multa_atraso"
                    value={formData.taxa_multa_atraso}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    data-testid="input-multa"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Juros de Mora (% ao dia)
                  </label>
                  <input
                    type="number"
                    name="taxa_juros_mora_diario"
                    value={formData.taxa_juros_mora_diario}
                    onChange={handleChange}
                    step="0.001"
                    min="0"
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    data-testid="input-juros-mora"
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                disabled={loading}
                className="w-full"
                testId="simular-button"
              >
                {loading ? 'Simulando...' : 'Simular Empréstimo'}
              </Button>
            </form>
          </div>

          {/* Resultado */}
          <div className="space-y-6">
            {resultado && (
              <>
                {/* Resumo */}
                <div className="bg-card rounded-lg border border-border p-6" data-testid="resultado-resumo">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-foreground">
                      Resumo da Simulação
                    </h2>
                    <div className="flex gap-2">
                      <button
                        onClick={exportarPDF}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex items-center gap-2 text-sm"
                        title="Exportar para PDF"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        PDF
                      </button>
                      <button
                        onClick={compartilharWhatsApp}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition flex items-center gap-2 text-sm"
                        title="Compartilhar no WhatsApp"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                        </svg>
                        WhatsApp
                      </button>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center border-b border-border pb-2">
                      <span className="text-muted-foreground">Método:</span>
                      <span className="font-semibold text-foreground" data-testid="resultado-metodo">
                        {getMetodoCalculoLabel(resultado.metodo_calculo)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center border-b border-border pb-2">
                      <span className="text-muted-foreground">Valor Principal:</span>
                      <span className="font-semibold text-foreground" data-testid="resultado-principal">
                        {formatarMoeda(resultado.valor_principal)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center border-b border-border pb-2">
                      <span className="text-muted-foreground">Taxa de Juros:</span>
                      <span className="font-semibold text-foreground">{resultado.taxa_juros_mensal}% ao mês</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-border pb-2">
                      <span className="text-muted-foreground">Prazo:</span>
                      <span className="font-semibold text-foreground">{resultado.prazo_meses} meses</span>
                    </div>
                    {resultado.periodo_carencia_meses > 0 && (
                      <div className="flex justify-between items-center border-b border-border pb-2">
                        <span className="text-muted-foreground">Carência:</span>
                        <span className="font-semibold text-foreground">{resultado.periodo_carencia_meses} meses</span>
                      </div>
                    )}
                    <div className="flex justify-between items-center border-b border-border pb-2 text-emerald-500">
                      <span>Total de Juros:</span>
                      <span className="font-bold" data-testid="resultado-juros">
                        {formatarMoeda(resultado.valor_total_juros)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center pt-2">
                      <span className="text-lg font-semibold text-foreground">Valor Total:</span>
                      <span className="text-2xl font-bold text-primary" data-testid="resultado-total">
                        {formatarMoeda(resultado.valor_total_com_juros)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Tabela de Parcelas */}
                <div className="bg-card rounded-lg border border-border p-4 md:p-6" data-testid="resultado-parcelas">
                  <h2 className="text-xl font-bold text-foreground mb-4">
                    Parcelas ({resultado.parcelas.length})
                  </h2>

                  {/* Versão Desktop - Tabela */}
                  <div className="hidden md:block overflow-x-auto max-h-96 overflow-y-auto">
                    <table className="min-w-full divide-y divide-border">
                      <thead className="bg-muted/50 sticky top-0">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">
                            #
                          </th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">
                            Vencimento
                          </th>
                          <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground uppercase">
                            Principal
                          </th>
                          <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground uppercase">
                            Juros
                          </th>
                          <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground uppercase">
                            Total
                          </th>
                          <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground uppercase">
                            Saldo
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {resultado.parcelas.map((parcela) => (
                          <tr key={parcela.numero_parcela} data-testid={`parcela-row-${parcela.numero_parcela}`} className="hover:bg-muted/50">
                            <td className="px-4 py-2 text-sm font-medium text-foreground">
                              {parcela.numero_parcela}
                            </td>
                            <td className="px-4 py-2 text-sm text-muted-foreground">
                              {formatarData(parcela.data_vencimento)}
                            </td>
                            <td className="px-4 py-2 text-sm text-foreground text-right">
                              {formatarMoeda(parcela.valor_principal)}
                            </td>
                            <td className="px-4 py-2 text-sm text-emerald-500 text-right">
                              {formatarMoeda(parcela.valor_juros)}
                            </td>
                            <td className="px-4 py-2 text-sm font-semibold text-foreground text-right">
                              {formatarMoeda(parcela.valor_total)}
                            </td>
                            <td className="px-4 py-2 text-sm text-muted-foreground text-right">
                              {formatarMoeda(parcela.saldo_devedor)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Versão Mobile - Cards */}
                  <div className="md:hidden space-y-3 max-h-96 overflow-y-auto">
                    {resultado.parcelas.map((parcela) => (
                      <div key={parcela.numero_parcela} className="p-3 bg-muted/30 rounded-lg border border-border" data-testid={`parcela-card-${parcela.numero_parcela}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-lg font-bold text-foreground">Parcela {parcela.numero_parcela}</span>
                          <span className="text-xs text-muted-foreground">{formatarData(parcela.data_vencimento)}</span>
                        </div>
                        <div className="space-y-1.5 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Principal:</span>
                            <span className="text-foreground font-medium">{formatarMoeda(parcela.valor_principal)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Juros:</span>
                            <span className="text-emerald-500 font-medium">{formatarMoeda(parcela.valor_juros)}</span>
                          </div>
                          <div className="flex justify-between pt-1.5 border-t border-border">
                            <span className="text-foreground font-semibold">Total:</span>
                            <span className="text-foreground font-bold">{formatarMoeda(parcela.valor_total)}</span>
                          </div>
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Saldo Devedor:</span>
                            <span className="text-muted-foreground">{formatarMoeda(parcela.saldo_devedor)}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {!resultado && (
              <div className="bg-card rounded-lg border border-border p-12 text-center" data-testid="sem-resultado">
                <svg
                  className="mx-auto h-12 w-12 text-muted-foreground mb-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                  />
                </svg>
                <p className="text-muted-foreground">
                  Preencha os dados e clique em "Simular Empréstimo" para ver os resultados
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal de Recuperação de Rascunho */}
      <DraftRecovery
        isOpen={showDraftRecovery}
        onRecover={handleRecoverDraft}
        onDiscard={handleDiscardDraft}
        draftTimestamp={getDraftTimestamp('simulacao')}
        title="Rascunho de Simulação Encontrado"
        description="Encontramos parâmetros de simulação salvos."
      />
    </Layout>
  );
};

export default Simulacao;
