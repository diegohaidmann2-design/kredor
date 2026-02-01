import React from 'react';
import Button from '../Button';
import { formatarMoeda, formatarData, getStatusLabel } from '../../utils/formatters';

const DetalhesEmprestimoModal = ({ open, onOpenChange, emprestimo }) => {
    if (!open || !emprestimo) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-card rounded-lg border border-border shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-2xl font-bold text-foreground">
                            Detalhes do Empréstimo
                        </h2>
                        <button
                            onClick={() => onOpenChange(false)}
                            className="text-muted-foreground hover:text-foreground"
                        >
                            ✕
                        </button>
                    </div>

                    <div className="space-y-6">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <h3 className="text-sm font-medium text-muted-foreground">Valor Principal</h3>
                                <p className="text-lg font-semibold">{formatarMoeda(emprestimo.valor_principal)}</p>
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-muted-foreground">Status</h3>
                                <p className="text-lg font-semibold">{getStatusLabel(emprestimo.status)}</p>
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-muted-foreground">Data Início</h3>
                                <p>{formatarData(emprestimo.data_inicio)}</p>
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-muted-foreground">Taxa Mensal</h3>
                                <p>{emprestimo.taxa_juros_mensal}%</p>
                            </div>
                        </div>

                        <div className="pt-4 border-t border-border">
                            <h3 className="font-semibold mb-2">Resumo Financeiro</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <span className="text-muted-foreground">Total a Receber:</span>
                                    <div className="font-bold text-emerald-500">{formatarMoeda(emprestimo.valor_total_com_juros)}</div>
                                </div>
                            </div>
                        </div>

                        {/* Aqui poderia entrar lista de parcelas, mas vamos manter simples por enquanto */}
                    </div>

                    <div className="flex justify-end mt-6 pt-6 border-t border-border">
                        <Button
                            onClick={() => onOpenChange(false)}
                            variant="secondary"
                        >
                            Fechar
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DetalhesEmprestimoModal;
