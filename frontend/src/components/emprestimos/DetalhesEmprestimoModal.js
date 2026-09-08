import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Button from '../Button';
import { formatarMoeda, formatarData, getStatusLabel, getMetodoCalculoLabel } from '../../utils/formatters';
import { emprestimosAPI, clientesAPI } from '../../api/api';
import { CheckCircle, Clock, XCircle, AlertCircle, Calendar, TrendingUp, User, FileText, Download, Send, RefreshCw } from 'lucide-react';

const DetalhesEmprestimoModal = ({ open, onOpenChange, emprestimo, onUpdate }) => {
    const [parcelas, setParcelas] = useState([]);
    const [cliente, setCliente] = useState(null);
    const [loading, setLoading] = useState(true);
    const [historico, setHistorico] = useState([]);
    const [enviandoWhats, setEnviandoWhats] = useState(null);

    useEffect(() => {
        if (open && emprestimo) {
            carregarDados();
        }
    }, [open, emprestimo]);

    const carregarDados = async () => {
        try {
            setLoading(true);
            const [parcelasRes, clienteRes, emprestimoRes] = await Promise.all([
                emprestimosAPI.listarParcelas(emprestimo.id),
                clientesAPI.obter(emprestimo.cliente_id),
                emprestimosAPI.obter(emprestimo.id)
            ]);
            setParcelas(parcelasRes.data || []);
            setCliente(clienteRes.data);
            setHistorico((emprestimoRes.data?.historico_prorrogacoes) || emprestimo.historico_prorrogacoes || []);
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
        } finally {
            setLoading(false);
        }
    };

    const baixarReciboProrrogacao = async (prorrogacaoId) => {
        try {
            const response = await emprestimosAPI.reciboProrrogacao(emprestimo.id, prorrogacaoId);
            const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
            const a = document.createElement('a');
            a.href = url;
            a.download = `comprovante_prorrogacao_${emprestimo.id.substring(0, 8)}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            alert('Erro ao gerar o PDF do recibo. Tente novamente.');
        }
    };

    const enviarReciboWhatsApp = async (prorrogacaoId) => {
        try {
            setEnviandoWhats(prorrogacaoId);
            await emprestimosAPI.enviarReciboProrrogacaoWhatsapp(emprestimo.id, prorrogacaoId);
            alert('Comprovante de prorrogação enviado pelo WhatsApp!');
        } catch (err) {
            alert(err.response?.data?.detail || 'Não foi possível enviar pelo WhatsApp.');
        } finally {
            setEnviandoWhats(null);
        }
    };

    if (!open || !emprestimo) return null;

    // Calcular estatísticas das parcelas
    const totalParcelasAtivas = parcelas.length;
    const totalParcelasOriginal = Number.isFinite(emprestimo?.prazo_meses) ? emprestimo.prazo_meses : totalParcelasAtivas;
    const parcelasPagas = parcelas.filter(p => p.status === 'pago').length;
    const parcelasAtrasadas = parcelas.filter(p => p.status === 'atrasado').length;
    const parcelasPendentes = parcelas.filter(p => p.status === 'pendente' || p.status === 'parcial').length;
    const percentualPago = totalParcelasAtivas > 0 ? ((parcelasPagas / totalParcelasAtivas) * 100).toFixed(1) : 0;

    // Encontrar próximo vencimento
    const proximaParcela = parcelas
        .filter(p => p.status === 'pendente' || p.status === 'parcial' || p.status === 'atrasado')
        .sort((a, b) => new Date(a.data_vencimento) - new Date(b.data_vencimento))[0];

    // Calcular valores financeiros
    const totalDevidoAtivo = parcelas.reduce((acc, p) => {
        const valorTotal = Number(p?.valor_total) || 0;
        const multa = Number(p?.valor_multa) || 0;
        const mora = Number(p?.valor_juros_mora) || 0;
        return acc + valorTotal + multa + mora;
    }, 0);
    const valorPago = parcelas.reduce((acc, p) => acc + (Number(p?.valor_pago) || 0), 0);
    const valorRestante = Math.max(0, totalDevidoAtivo - valorPago);
    const statusEmprestimo = (parcelasPendentes === 0 && valorRestante === 0) ? 'quitado' : emprestimo.status;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
             onClick={() => onOpenChange(false)}>
            <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-card rounded-xl border border-border shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}>
                
                {/* Header */}
                <div className="sticky top-0 bg-card border-b border-border p-6 z-10">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-2xl font-bold text-foreground">
                                Detalhes do Empréstimo
                            </h2>
                            <p className="text-sm text-muted-foreground mt-1">
                                ID: {emprestimo.id?.substring(0, 8)}...
                            </p>
                        </div>
                        <button
                            onClick={() => onOpenChange(false)}
                            className="text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg p-2 transition"
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                <div className="p-6 space-y-6">
                    {loading ? (
                        <div className="text-center py-8 text-muted-foreground">Carregando...</div>
                    ) : (
                        <>
                            {/* Cliente Info */}
                            {cliente && (
                                <div className="bg-muted/30 rounded-lg p-4 border border-border">
                                    <div className="flex items-center gap-3 mb-2">
                                        <User className="w-5 h-5 text-primary" />
                                        <h3 className="font-semibold text-foreground">Cliente</h3>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4 ml-8">
                                        <div>
                                            <p className="text-sm text-muted-foreground">Nome</p>
                                            <p className="font-medium text-foreground">{cliente.nome}</p>
                                        </div>
                                        <div>
                                            <p className="text-sm text-muted-foreground">CPF/CNPJ</p>
                                            <p className="font-medium text-foreground">{cliente.cpf_cnpj}</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Próximo Vencimento */}
                            {proximaParcela && (
                                <div className={`rounded-lg p-4 border ${
                                    proximaParcela.status === 'atrasado' 
                                        ? 'bg-red-500/10 border-red-500/30' 
                                        : 'bg-blue-500/10 border-blue-500/30'
                                }`}>
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <Calendar className={`w-5 h-5 ${
                                                proximaParcela.status === 'atrasado' ? 'text-red-500' : 'text-blue-500'
                                            }`} />
                                            <div>
                                                <h3 className="font-semibold text-foreground">
                                                    {proximaParcela.status === 'atrasado' ? '⚠️ Parcela Vencida' : '📅 Próximo Vencimento'}
                                                </h3>
                                                <p className="text-sm text-muted-foreground">
                                                    Parcela {proximaParcela.numero_parcela}/{totalParcelasOriginal}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className={`text-lg font-bold ${
                                                proximaParcela.status === 'atrasado' ? 'text-red-500' : 'text-blue-500'
                                            }`}>
                                                {formatarData(proximaParcela.data_vencimento)}
                                            </p>
                                            <p className="text-sm font-semibold text-foreground">
                                                {formatarMoeda(proximaParcela.valor_total)}
                                            </p>
                                        </div>
                                    </div>
                                    {proximaParcela.status === 'atrasado' && proximaParcela.dias_atraso > 0 && (
                                        <div className="mt-2 pt-2 border-t border-red-500/20">
                                            <p className="text-xs text-red-500">
                                                🚨 {proximaParcela.dias_atraso} dia(s) de atraso
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Progresso de Pagamento */}
                            <div className="bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg p-5 border border-primary/20">
                                <div className="flex items-center gap-3 mb-4">
                                    <TrendingUp className="w-5 h-5 text-primary" />
                                    <h3 className="font-semibold text-foreground">Progresso do Pagamento</h3>
                                </div>
                                
                                {/* Barra de progresso */}
                                <div className="mb-4">
                                    <div className="flex justify-between text-sm mb-2">
                                        <span className="text-muted-foreground">
                                            {parcelasPagas} de {totalParcelasAtivas} parcelas pagas
                                        </span>
                                        <span className="font-semibold text-primary">{percentualPago}%</span>
                                    </div>
                                    <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
                                        <motion.div 
                                            initial={{ width: 0 }}
                                            animate={{ width: `${percentualPago}%` }}
                                            transition={{ duration: 0.5, ease: "easeOut" }}
                                            className="bg-gradient-to-r from-primary to-primary/80 h-full rounded-full"
                                        />
                                    </div>
                                </div>

                                {/* Status das parcelas */}
                                <div className="grid grid-cols-3 gap-3">
                                    <div className="bg-card rounded-lg p-3 border border-border">
                                        <div className="flex items-center gap-2 mb-1">
                                            <CheckCircle className="w-4 h-4 text-emerald-500" />
                                            <span className="text-xs text-muted-foreground">Pagas</span>
                                        </div>
                                        <p className="text-xl font-bold text-emerald-500">{parcelasPagas}</p>
                                    </div>
                                    <div className="bg-card rounded-lg p-3 border border-border">
                                        <div className="flex items-center gap-2 mb-1">
                                            <Clock className="w-4 h-4 text-blue-500" />
                                            <span className="text-xs text-muted-foreground">Pendentes</span>
                                        </div>
                                        <p className="text-xl font-bold text-blue-500">{parcelasPendentes}</p>
                                    </div>
                                    <div className="bg-card rounded-lg p-3 border border-border">
                                        <div className="flex items-center gap-2 mb-1">
                                            <AlertCircle className="w-4 h-4 text-red-500" />
                                            <span className="text-xs text-muted-foreground">Atrasadas</span>
                                        </div>
                                        <p className="text-xl font-bold text-red-500">{parcelasAtrasadas}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Dados do Empréstimo */}
                            <div>
                                <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
                                    <FileText className="w-5 h-5 text-primary" />
                                    Informações do Empréstimo
                                </h3>
                                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                                    <div className="bg-muted/30 rounded-lg p-4 border border-border">
                                        <p className="text-xs text-muted-foreground mb-1">Valor Emprestado</p>
                                        <p className="text-lg font-bold text-foreground">{formatarMoeda(emprestimo.valor_principal)}</p>
                                    </div>
                                    <div className="bg-muted/30 rounded-lg p-4 border border-border">
                                        <p className="text-xs text-muted-foreground mb-1">Taxa de Juros</p>
                                        <p className="text-lg font-bold text-foreground">{emprestimo.taxa_juros_mensal}% a.m.</p>
                                    </div>
                                    <div className="bg-muted/30 rounded-lg p-4 border border-border">
                                        <p className="text-xs text-muted-foreground mb-1">Prazo</p>
                                        <p className="text-lg font-bold text-foreground">{emprestimo.prazo_meses} meses</p>
                                    </div>
                                    <div className="bg-muted/30 rounded-lg p-4 border border-border">
                                        <p className="text-xs text-muted-foreground mb-1">Método de Cálculo</p>
                                        <p className="text-sm font-medium text-foreground">{getMetodoCalculoLabel(emprestimo.metodo_calculo)}</p>
                                    </div>
                                    <div className="bg-muted/30 rounded-lg p-4 border border-border">
                                        <p className="text-xs text-muted-foreground mb-1">Data de Início</p>
                                        <p className="text-sm font-medium text-foreground">{formatarData(emprestimo.data_inicio)}</p>
                                    </div>
                                    {proximaParcela && (
                                        <div className="bg-muted/30 rounded-lg p-4 border border-border">
                                            <p className="text-xs text-muted-foreground mb-1">Próximo Vencimento</p>
                                            <p className={`text-sm font-bold ${
                                                proximaParcela.status === 'atrasado' ? 'text-red-500' : 'text-blue-500'
                                            }`}>
                                                {formatarData(proximaParcela.data_vencimento)}
                                            </p>
                                        </div>
                                    )}
                                    <div className="bg-muted/30 rounded-lg p-4 border border-border">
                                        <p className="text-xs text-muted-foreground mb-1">Status</p>
                                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                            statusEmprestimo === 'ativo' ? 'bg-emerald-500/20 text-emerald-500' :
                                            statusEmprestimo === 'quitado' ? 'bg-blue-500/20 text-blue-500' :
                                            'bg-red-500/20 text-red-500'
                                        }`}>
                                            {getStatusLabel(statusEmprestimo)}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Resumo Financeiro */}
                            <div className="bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 rounded-lg p-5 border border-emerald-500/20">
                                <h3 className="font-semibold text-foreground mb-4">💰 Resumo Financeiro</h3>
                                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-1">Total (parcelas ativas)</p>
                                        <p className="text-lg font-bold text-foreground">{formatarMoeda(totalDevidoAtivo)}</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-1">Total de Juros</p>
                                        <p className="text-lg font-bold text-amber-500">{formatarMoeda(emprestimo.valor_total_juros)}</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-1">Valor Pago</p>
                                        <p className="text-lg font-bold text-emerald-500">{formatarMoeda(valorPago)}</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-1">Valor Restante (parcelas ativas)</p>
                                        <p className="text-lg font-bold text-blue-500">{formatarMoeda(valorRestante)}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Histórico de Prorrogações */}
                            {historico.length > 0 && (
                                <div data-testid="historico-prorrogacoes">
                                    <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
                                        <RefreshCw className="w-5 h-5 text-primary" />
                                        Histórico de Prorrogações ({historico.length})
                                    </h3>
                                    <div className="space-y-2">
                                        {historico.map((h) => (
                                            <div key={h.id}
                                                 className="p-3 bg-muted/30 rounded-lg border border-border"
                                                 data-testid={`prorrogacao-item-${h.id}`}>
                                                <div className="flex items-center justify-between gap-3 flex-wrap">
                                                    <div>
                                                        <p className="text-sm font-medium text-foreground">
                                                            + {h.periodos} {h.periodicidade === 'semanal' ? 'semana(s)' : 'mês(es)'}
                                                            <span className="ml-2 text-xs text-muted-foreground">
                                                                ({getMetodoCalculoLabel(h.metodo_calculo)})
                                                            </span>
                                                        </p>
                                                        <p className="text-xs text-muted-foreground mt-0.5">
                                                            {formatarData(h.data)} • {h.parcelas_antes} → {h.parcelas_depois} parcelas
                                                            {h.valor_parcela ? ` • parcela ${formatarMoeda(h.valor_parcela)}` : ''}
                                                        </p>
                                                    </div>
                                                    <div className="flex gap-2">
                                                        <button
                                                            onClick={() => baixarReciboProrrogacao(h.id)}
                                                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md border border-border hover:bg-muted transition"
                                                            data-testid={`btn-recibo-prorrogacao-pdf-${h.id}`}
                                                        >
                                                            <Download className="w-4 h-4" /> PDF
                                                        </button>
                                                        <button
                                                            onClick={() => enviarReciboWhatsApp(h.id)}
                                                            disabled={enviandoWhats === h.id}
                                                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-green-600 hover:bg-green-700 text-white transition disabled:opacity-60"
                                                            data-testid={`btn-recibo-prorrogacao-whatsapp-${h.id}`}
                                                        >
                                                            <Send className="w-4 h-4" /> {enviandoWhats === h.id ? 'Enviando…' : 'WhatsApp'}
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Lista de Parcelas Resumida */}
                            {parcelas.length > 0 && (
                                <div>
                                    <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
                                        <Calendar className="w-5 h-5 text-primary" />
                                        Últimas Parcelas ({totalParcelasAtivas} ativas)
                                    </h3>
                                    <div className="space-y-2 max-h-60 overflow-y-auto">
                                        {parcelas.slice(0, 6).map((parcela) => (
                                            <div key={parcela.id} 
                                                 className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border hover:bg-muted/50 transition">
                                                <div className="flex items-center gap-3">
                                                    {parcela.status === 'pago' && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                                                    {parcela.status === 'pendente' && <Clock className="w-4 h-4 text-blue-500" />}
                                                    {parcela.status === 'atrasado' && <AlertCircle className="w-4 h-4 text-red-500" />}
                                                    <div>
                                                        <p className="text-sm font-medium text-foreground">
                                                            Parcela {parcela.numero_parcela}/{totalParcelasOriginal}
                                                        </p>
                                                        <p className="text-xs text-muted-foreground">
                                                            Venc: {formatarData(parcela.data_vencimento)}
                                                        </p>
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <p className="text-sm font-semibold text-foreground">
                                                        {formatarMoeda(parcela.valor_total)}
                                                    </p>
                                                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                                                        parcela.status === 'pago' ? 'bg-emerald-500/20 text-emerald-500' :
                                                        parcela.status === 'pendente' ? 'bg-blue-500/20 text-blue-500' :
                                                        'bg-red-500/20 text-red-500'
                                                    }`}>
                                                        {parcela.status === 'pago' ? 'Paga' : parcela.status === 'pendente' ? 'Pendente' : 'Atrasada'}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    {parcelas.length > 6 && (
                                        <p className="text-xs text-center text-muted-foreground mt-2">
                                            E mais {parcelas.length - 6} parcelas...
                                        </p>
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="sticky bottom-0 bg-card border-t border-border p-4 flex justify-end gap-3">
                    <Button
                        onClick={() => onOpenChange(false)}
                        variant="secondary"
                    >
                        Fechar
                    </Button>
                </div>
            </motion.div>
        </div>
    );
};

export default DetalhesEmprestimoModal;
