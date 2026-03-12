import React from 'react';
import Button from '../Button';
import { SaveStatusBadge } from '../DraftRecovery';
import { emprestimosAPI } from '../../api/api';
import { useModal } from '../../components/Modal';

const NovoEmprestimoModal = ({
    open,
    onOpenChange,
    onSuccess,
    clientes,
    formData,
    setFormData,
    resetForm,
    autosave,
    handleClearDraft
}) => {
    const modal = useModal();

    if (!open) return null;

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            const data = {
                ...formData,
                valor_principal: parseFloat(formData.valor_principal),
                taxa_juros_mensal: parseFloat(formData.taxa_juros_mensal),
                prazo_meses: parseInt(formData.prazo_meses),
                periodo_carencia_meses: parseInt(formData.periodo_carencia_meses || 0),
                taxa_multa_atraso: parseFloat(formData.taxa_multa_atraso),
                taxa_juros_mora_diario: parseFloat(formData.taxa_juros_mora_diario),
                // Adiciona T12:00:00 para garantir que a data não recue um dia devido ao fuso horário (UTC-3 vs UTC)
                data_inicio: formData.data_inicio ? new Date(formData.data_inicio + 'T12:00:00').toISOString() : null,
                // ✅ Passar dia_vencimento (null se vazio)
                dia_vencimento: formData.dia_vencimento ? parseInt(formData.dia_vencimento) : null
            };

            await emprestimosAPI.criar(data);
            autosave.clear();
            onOpenChange(false);
            resetForm();
            if (onSuccess) onSuccess();
            modal.success('Empréstimo Criado!', 'O empréstimo foi registrado com sucesso. As parcelas foram geradas automaticamente.');
        } catch (err) {
            modal.error('Erro ao criar empréstimo', err.response?.data?.detail || 'Não foi possível criar o empréstimo.');
        }
    };

    return (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-2 sm:p-4 z-50 backdrop-blur-sm">
            <div className="bg-card rounded-lg border border-border shadow-2xl max-w-2xl w-full max-h-[95vh] overflow-y-auto">
                <div className="p-4 sm:p-8">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
                        <h2 className="text-xl sm:text-2xl font-bold text-foreground">
                            Novo Empréstimo
                        </h2>
                        <SaveStatusBadge
                            isSaving={autosave.isSaving}
                            lastSaved={autosave.lastSaved}
                            hasUnsavedChanges={autosave.hasUnsavedChanges}
                            onClearDraft={handleClearDraft}
                        />
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">
                                Cliente <span className="text-red-500">*</span>
                            </label>
                            <select
                                name="cliente_id"
                                value={formData.cliente_id}
                                onChange={handleChange}
                                required
                                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                            >
                                <option value="">Selecione um cliente</option>
                                {clientes
                                    .filter(c => c.status !== 'bloqueado')
                                    .map(cliente => (
                                        <option key={cliente.id} value={cliente.id}>
                                            {cliente.nome} - {cliente.cpf_cnpj}
                                        </option>
                                    ))}
                            </select>
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
                                required
                                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                            />
                        </div>

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
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
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
                                />
                            </div>
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
                            >
                                <option value="tabela_price">Tabela Price</option>
                                <option value="sac">SAC</option>
                                <option value="juros_simples">Juros Simples</option>
                                <option value="juros_compostos">Juros Compostos</option>
                                <option value="apenas_juros">Apenas Juros (Capital no final)</option>
                            </select>
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
                            />
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
                                />
                            </div>
                        </div>

                        <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 mt-6 pt-6 border-t border-border">
                            <Button
                                type="button"
                                onClick={() => {
                                    onOpenChange(false);
                                    resetForm();
                                }}
                                variant="secondary"
                                className="w-full sm:w-auto"
                            >
                                Cancelar
                            </Button>
                            <Button type="submit" variant="primary" className="w-full sm:w-auto">
                                Criar Empréstimo
                            </Button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default NovoEmprestimoModal;
