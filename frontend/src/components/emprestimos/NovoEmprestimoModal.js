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
    const [submitting, setSubmitting] = React.useState(false);

    if (!open) return null;

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Prevenir duplo submit
        if (submitting) {
            return;
        }

        setSubmitting(true);

        try {
            const baseData = {
                cliente_id: formData.cliente_id,
                valor_principal: parseFloat(formData.valor_principal),
                metodo_calculo: formData.metodo_calculo,
                periodo_carencia_meses: parseInt(formData.periodo_carencia_meses || 0),
                taxa_multa_atraso: parseFloat(formData.taxa_multa_atraso),
                taxa_juros_mora_diario: parseFloat(formData.taxa_juros_mora_diario),
                periodicidade: formData.periodicidade,
                sem_prazo: formData.sem_prazo || false,
                data_inicio: formData.data_inicio ? new Date(formData.data_inicio + 'T12:00:00').toISOString() : null,
                dia_vencimento: formData.dia_vencimento ? parseInt(formData.dia_vencimento) : null
            };

            // Adicionar campos específicos baseado na periodicidade e se tem prazo
            if (!formData.sem_prazo) {
                if (formData.periodicidade === 'semanal') {
                    baseData.taxa_juros_semanal = parseFloat(formData.taxa_juros_semanal);
                    baseData.prazo_semanas = parseInt(formData.prazo_semanas);
                } else {
                    baseData.taxa_juros_mensal = parseFloat(formData.taxa_juros_mensal);
                    baseData.prazo_meses = parseInt(formData.prazo_meses);
                }
            } else {
                // Empréstimo sem prazo: taxa baseada na periodicidade
                if (formData.periodicidade === 'semanal') {
                    baseData.taxa_juros_semanal = parseFloat(formData.taxa_juros_semanal);
                } else {
                    baseData.taxa_juros_mensal = parseFloat(formData.taxa_juros_mensal);
                }
            }

            await emprestimosAPI.criar(baseData);
            autosave.clear();
            onOpenChange(false);
            resetForm();
            if (onSuccess) onSuccess();
            modal.success('Empréstimo Criado!', 'O empréstimo foi registrado com sucesso. As parcelas foram geradas automaticamente.');
        } catch (err) {
            modal.error('Erro ao criar empréstimo', err.response?.data?.detail || 'Não foi possível criar o empréstimo.');
        } finally {
            setSubmitting(false);
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

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                                    Dia de Vencimento
                                    <span className="text-xs text-muted-foreground ml-2">(opcional)</span>
                                </label>
                                <select
                                    name="dia_vencimento"
                                    value={formData.dia_vencimento || ''}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                >
                                    <option value="">Usar dia da data início</option>
                                    <option value="1">Todo dia 1</option>
                                    <option value="5">Todo dia 5</option>
                                    <option value="10">Todo dia 10</option>
                                    <option value="15">Todo dia 15</option>
                                    <option value="20">Todo dia 20</option>
                                    <option value="25">Todo dia 25</option>
                                    <option value="28">Todo dia 28</option>
                                    <option value="30">Todo dia 30</option>
                                </select>
                                <p className="text-xs text-muted-foreground mt-1">
                                    📅 Parcelas vencerão neste dia de cada mês
                                </p>
                            </div>
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

                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">
                                Periodicidade <span className="text-red-500">*</span>
                            </label>
                            <select
                                name="periodicidade"
                                value={formData.periodicidade}
                                onChange={handleChange}
                                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                            >
                                <option value="mensal">📅 Mensal</option>
                                <option value="semanal">📆 Semanal</option>
                            </select>
                            <p className="text-xs text-muted-foreground mt-1">
                                {formData.periodicidade === 'mensal' && '💡 Parcelas vencerão todo mês no mesmo dia'}
                                {formData.periodicidade === 'semanal' && '💡 Parcelas vencerão toda semana no mesmo dia (ex: toda segunda-feira)'}
                            </p>
                        </div>

                        {/* Checkbox Empréstimo Sem Prazo */}
                        <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                            <label className="flex items-start gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    name="sem_prazo"
                                    checked={formData.sem_prazo || false}
                                    onChange={(e) => {
                                        const checked = e.target.checked;
                                        setFormData({
                                            ...formData,
                                            sem_prazo: checked,
                                            metodo_calculo: checked ? 'apenas_juros' : formData.metodo_calculo,
                                            prazo_meses: checked ? null : formData.prazo_meses,
                                            prazo_semanas: checked ? null : formData.prazo_semanas
                                        });
                                    }}
                                    className="mt-0.5 w-5 h-5 rounded border-amber-300 text-amber-600 focus:ring-amber-500"
                                />
                                <div className="flex-1">
                                    <span className="text-sm font-medium text-foreground">
                                        🔄 Empréstimo Sem Prazo (Aberto)
                                    </span>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Cliente paga apenas juros {formData.periodicidade === 'semanal' ? 'semanalmente' : 'mensalmente'}. Parcelas são geradas automaticamente até a quitação final.
                                    </p>
                                    {formData.sem_prazo && (
                                        <div className="mt-2 p-2 bg-amber-100 dark:bg-amber-900/30 rounded text-xs text-amber-800 dark:text-amber-200">
                                            <strong>⚠️ Método "Apenas Juros":</strong> Capital será pago no final
                                        </div>
                                    )}
                                </div>
                            </label>
                        </div>

                        {/* Taxa de Juros - sempre visível */}
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">
                                Taxa de Juros (% ao {formData.periodicidade === 'semanal' ? 'semana' : 'mês'}) <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="number"
                                name={formData.periodicidade === 'semanal' ? 'taxa_juros_semanal' : 'taxa_juros_mensal'}
                                value={formData.periodicidade === 'semanal' ? formData.taxa_juros_semanal : formData.taxa_juros_mensal}
                                onChange={handleChange}
                                required
                                step="0.01"
                                min="0"
                                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                            />
                        </div>

                        {/* Prazo - apenas se NÃO for empréstimo aberto */}
                        {!formData.sem_prazo && (
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-1">
                                    Prazo ({formData.periodicidade === 'semanal' ? 'semanas' : 'meses'}) <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="number"
                                    name={formData.periodicidade === 'semanal' ? 'prazo_semanas' : 'prazo_meses'}
                                    value={formData.periodicidade === 'semanal' ? formData.prazo_semanas : formData.prazo_meses}
                                    onChange={handleChange}
                                    required
                                    min="1"
                                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                />
                                {formData.periodicidade === 'semanal' && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                        💡 4 semanas ≈ 1 mês
                                    </p>
                                )}
                            </div>
                        )}

                        {/* Aviso para empréstimo aberto */}
                        {formData.sem_prazo && (
                            <div className="p-4 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                                <p className="text-sm text-blue-800 dark:text-blue-200">
                                    ℹ️ <strong>Empréstimo Aberto:</strong> Apenas a taxa de juros é necessária. O prazo não precisa ser definido.
                                </p>
                            </div>
                        )}

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
                            <Button 
                                type="submit" 
                                variant="primary" 
                                className="w-full sm:w-auto"
                                loading={submitting}
                                disabled={submitting}
                            >
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
