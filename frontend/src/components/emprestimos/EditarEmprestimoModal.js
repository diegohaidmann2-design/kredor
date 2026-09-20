import React, { useState, useEffect } from 'react';
import Button from '../Button';
import { emprestimosAPI } from '../../api/api';
import { useModal } from '../../components/Modal';

const EditarEmprestimoModal = ({
    open,
    onOpenChange,
    onSuccess,
    clientes,
    emprestimo
}) => {
    const modal = useModal();
    const [formData, setFormData] = useState({
        cliente_id: '',
        valor_principal: '',
        taxa_juros_mensal: '',
        taxa_juros_semanal: '',
        taxa_juros_quinzenal: '',
        prazo_meses: '',
        prazo_semanas: '',
        prazo_quinzenas: '',
        metodo_calculo: 'tabela_price',
        periodo_carencia_meses: 0,
        taxa_multa_atraso: 2.0,
        taxa_juros_mora_diario: 0.033,
        periodicidade: 'mensal',
        sem_prazo: false,
        data_inicio: '',
        status: 'ativo'
    });
    const [loading, setLoading] = useState(false);
    const [possuiParcelasPagas, setPossuiParcelasPagas] = useState(false);

    useEffect(() => {
        if (open && emprestimo) {
            setFormData({
                cliente_id: emprestimo.cliente_id || '',
                valor_principal: emprestimo.valor_principal || '',
                taxa_juros_mensal: emprestimo.taxa_juros_mensal || '',
                taxa_juros_semanal: emprestimo.taxa_juros_semanal || '',
                taxa_juros_quinzenal: emprestimo.taxa_juros_quinzenal || '',
                prazo_meses: emprestimo.prazo_meses || '',
                prazo_semanas: emprestimo.prazo_semanas || '',
                prazo_quinzenas: emprestimo.prazo_quinzenas || '',
                metodo_calculo: emprestimo.metodo_calculo || 'tabela_price',
                periodo_carencia_meses: emprestimo.periodo_carencia_meses || 0,
                taxa_multa_atraso: emprestimo.taxa_multa_atraso || 2.0,
                taxa_juros_mora_diario: emprestimo.taxa_juros_mora_diario || 0.033,
                periodicidade: emprestimo.periodicidade || 'mensal',
                sem_prazo: emprestimo.sem_prazo || false,
                data_inicio: emprestimo.data_inicio ? emprestimo.data_inicio.split('T')[0] : '',
                status: emprestimo.status || 'ativo'
            });

            verificarParcelasPagas(emprestimo.id);
        }
    }, [open, emprestimo]);

    const verificarParcelasPagas = async (id) => {
        try {
            const response = await emprestimosAPI.listarParcelas(id);
            const pagas = response.data.some(p => p.status === 'pago');
            setPossuiParcelasPagas(pagas);
        } catch (err) {
            // silencioso: verificação auxiliar; na falha assume o padrão e não bloqueia a edição
            console.error('Erro ao verificar parcelas:', err);
        }
    };

    if (!open || !emprestimo) return null;

    const PERIOD = {
        mensal:    { taxa: 'taxa_juros_mensal',    prazo: 'prazo_meses',     unidade: 'mês',      plural: 'meses' },
        semanal:   { taxa: 'taxa_juros_semanal',   prazo: 'prazo_semanas',   unidade: 'semana',   plural: 'semanas' },
        quinzenal: { taxa: 'taxa_juros_quinzenal', prazo: 'prazo_quinzenas', unidade: 'quinzena', plural: 'quinzenas' },
    };
    const per = PERIOD[formData.periodicidade] || PERIOD.mensal;

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const data = {
                cliente_id: formData.cliente_id,
                valor_principal: parseFloat(formData.valor_principal),
                metodo_calculo: formData.metodo_calculo,
                periodo_carencia_meses: parseInt(formData.periodo_carencia_meses || 0),
                taxa_multa_atraso: parseFloat(formData.taxa_multa_atraso),
                taxa_juros_mora_diario: parseFloat(formData.taxa_juros_mora_diario),
                periodicidade: formData.periodicidade,
                sem_prazo: formData.sem_prazo,
                data_inicio: formData.data_inicio ? new Date(formData.data_inicio + 'T12:00:00').toISOString() : null,
                status: formData.status
            };

            data[per.taxa] = parseFloat(formData[per.taxa]);

            if (!formData.sem_prazo) {
                data[per.prazo] = parseInt(formData[per.prazo]);
            }

            await emprestimosAPI.atualizar(emprestimo.id, data);
            onOpenChange(false);
            if (onSuccess) onSuccess();
            modal.success('Empréstimo Atualizado!', 'Os dados foram salvos com sucesso.');
        } catch (err) {
            modal.error('Erro ao atualizar', err.response?.data?.detail || 'Não foi possível salvar as alterações.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-2 sm:p-4 z-50 backdrop-blur-sm">
            <div className="bg-card rounded-lg border border-border shadow-2xl max-w-2xl w-full max-h-[95vh] overflow-y-auto">
                <div className="p-4 sm:p-8">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
                        <h2 className="text-xl sm:text-2xl font-bold text-foreground">
                            Editar Empréstimo
                        </h2>
                        {possuiParcelasPagas && (
                            <span className="text-xs bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 px-2 py-1 rounded-full font-medium">
                                Campos financeiros bloqueados (já existem parcelas pagas)
                            </span>
                        )}
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-1">
                                    Cliente
                                </label>
                                <select
                                    name="cliente_id"
                                    value={formData.cliente_id}
                                    onChange={handleChange}
                                    disabled={possuiParcelasPagas}
                                    required
                                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                                >
                                    {clientes.map(cliente => (
                                        <option key={cliente.id} value={cliente.id}>
                                            {cliente.nome}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-foreground mb-1">
                                    Status do Empréstimo
                                </label>
                                <select
                                    name="status"
                                    value={formData.status}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                >
                                    <option value="ativo">Ativo</option>
                                    <option value="quitado">Quitado</option>
                                    <option value="inadimplente">Inadimplente</option>
                                    <option value="cancelado">Cancelado</option>
                                </select>
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">
                                Data de Início
                            </label>
                            <input
                                type="date"
                                name="data_inicio"
                                value={formData.data_inicio}
                                onChange={handleChange}
                                disabled={possuiParcelasPagas}
                                required
                                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">
                                Valor Principal (R$)
                            </label>
                            <input
                                type="number"
                                name="valor_principal"
                                value={formData.valor_principal}
                                onChange={handleChange}
                                disabled={possuiParcelasPagas}
                                required
                                step="0.01"
                                min="0"
                                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-1">
                                    Taxa Juros (% ao {per.unidade})
                                </label>
                                <input
                                    type="number"
                                    name={per.taxa}
                                    value={formData[per.taxa] || ''}
                                    onChange={handleChange}
                                    disabled={possuiParcelasPagas}
                                    required
                                    step="0.01"
                                    min="0"
                                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                                />
                            </div>
                            {!formData.sem_prazo && (
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-1">
                                        Prazo ({per.plural})
                                    </label>
                                    <input
                                        type="number"
                                        name={per.prazo}
                                        value={formData[per.prazo] || ''}
                                        onChange={handleChange}
                                        disabled={possuiParcelasPagas}
                                        required
                                        min="1"
                                        className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                                    />
                                </div>
                            )}
                        </div>

                        {formData.sem_prazo && (
                            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md p-3">
                                <p className="text-sm text-amber-700 dark:text-amber-400 font-medium">
                                    Empréstimo sem prazo definido — parcelas geradas automaticamente.
                                </p>
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-1">
                                    Periodicidade
                                </label>
                                <select
                                    name="periodicidade"
                                    value={formData.periodicidade}
                                    onChange={handleChange}
                                    disabled={possuiParcelasPagas}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                                >
                                    <option value="mensal">Mensal</option>
                                    <option value="semanal">Semanal</option>
                                    <option value="quinzenal">Quinzenal</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-1">
                                    Método de Cálculo
                                </label>
                                <select
                                    name="metodo_calculo"
                                    value={formData.metodo_calculo}
                                    onChange={handleChange}
                                    disabled={possuiParcelasPagas}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                                >
                                    <option value="tabela_price">Tabela Price</option>
                                    <option value="sac">SAC</option>
                                    <option value="juros_simples">Juros Simples</option>
                                    <option value="juros_compostos">Juros Compostos</option>
                                    <option value="apenas_juros">Apenas Juros</option>
                                </select>
                            </div>
                        </div>

                        <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 mt-6 pt-6 border-t border-border">
                            <Button
                                type="button"
                                onClick={() => onOpenChange(false)}
                                variant="secondary"
                                className="w-full sm:w-auto"
                            >
                                Cancelar
                            </Button>
                            <Button 
                                type="submit" 
                                variant="primary" 
                                className="w-full sm:w-auto"
                                disabled={loading}
                            >
                                {loading ? 'Salvando...' : 'Salvar Alterações'}
                            </Button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default EditarEmprestimoModal;
