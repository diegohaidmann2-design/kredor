import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter
} from '../ui/dialog';
import { Button } from '../ui/button';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '../ui/table';
import { Loader2, Trash2, Undo2, AlertTriangle } from 'lucide-react';
import { emprestimosAPI } from '../../api/api';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { toast } from 'sonner';

/**
 * Componente Modal para gerenciar a Lixeira de Empréstimos
 * @param {boolean} open - Se o modal está aberto
 * @param {function} onOpenChange - Handler para mudança de estado
 * @param {function} onRestored - Callback quando item é restaurado (para refresh da lista principal)
 */
const LixeiraEmprestimos = ({ open, onOpenChange, onRestored }) => {
    const [loading, setLoading] = useState(false);
    const [restoringId, setRestoringId] = useState(null);
    const [deletingId, setDeletingId] = useState(null);
    const [itens, setItens] = useState([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalItems, setTotalItems] = useState(0);

    const carregarLixeira = async (pagina = 1) => {
        try {
            setLoading(true);
            // Chama API passando lixeira=true
            const response = await emprestimosAPI.listar({
                page: pagina,
                limit: 10,
                lixeira: true
            });

            setItens(response.data.items || []);
            setTotalPages(response.data.pages || 1);
            setTotalItems(response.data.total || 0);
            setPage(pagina);
        } catch (error) {
            console.error('Erro ao carregar lixeira:', error);
            toast.error('Não foi possível carregar a lixeira');
        } finally {
            setLoading(false);
        }
    };

    // Carregar dados quando modal abre
    useEffect(() => {
        if (open) {
            carregarLixeira();
        }
    }, [open]);

    const handleRestaurar = async (id) => {
        try {
            setRestoringId(id);
            await emprestimosAPI.restaurar(id);
            toast.success('Empréstimo restaurado com sucesso!');

            // Recarregar lista da lixeira
            await carregarLixeira(page);

            // Avisar pai para recarregar lista principal
            if (onRestored) onRestored();
        } catch (error) {
            console.error('Erro ao restaurar:', error);
            toast.error('Erro ao restaurar empréstimo');
        } finally {
            setRestoringId(null);
        }
    };

    const handleExcluirDefinitivamente = async (id) => {
        if (!window.confirm("ATENÇÃO: Isso excluirá PERMANENTEMENTE o empréstimo e todos os registros associados. Esta ação NÃO pode ser desfeita. Tem certeza?")) {
            return;
        }

        try {
            setDeletingId(id);
            // Passa hard=true para exclusão permanente
            await emprestimosAPI.deletar(id, true);
            toast.success('Empréstimo excluído permanentemente!');

            // Recarregar lista da lixeira
            await carregarLixeira(page);
        } catch (error) {
            console.error('Erro ao excluir definitivamente:', error);
            toast.error('Erro ao excluir registro permanentemente');
        } finally {
            setDeletingId(null);
        }
    };

    const formatMoney = (value) => {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL',
        }).format(value);
    };

    const formatDate = (dateString) => {
        try {
            if (!dateString) return '-';
            return format(new Date(dateString), 'dd/MM/yyyy HH:mm', { locale: ptBR });
        } catch (e) {
            return dateString;
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="w-[98vw] sm:w-[95vw] max-w-4xl max-h-[95vh] overflow-y-auto p-3 sm:p-6 rounded-lg gap-0">
                <DialogHeader className="mb-4 pr-6">
                    <DialogTitle className="flex items-center gap-2 text-lg sm:text-xl">
                        <Trash2 className="h-5 w-5 text-red-500" />
                        Lixeira de Empréstimos
                    </DialogTitle>
                    <DialogDescription className="text-xs sm:text-sm">
                        Visualize e restaure empréstimos excluídos. Itens aqui não aparecem nos relatórios.
                    </DialogDescription>
                </DialogHeader>

                {loading && !itens.length ? (
                    <div className="flex justify-center py-8">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                ) : (
                    <div className="mt-2 text-sm sm:text-base">
                        {itens.length === 0 ? (
                            <div className="text-center py-12 border rounded-lg bg-gray-50 dark:bg-gray-900/50">
                                <Trash2 className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                                <p className="text-muted-foreground">A lixeira está vazia.</p>
                            </div>
                        ) : (
                            <>
                                {/* Versão Desktop - Tabela */}
                                <div className="hidden md:block relative overflow-x-auto border rounded-md">
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Cliente</TableHead>
                                                <TableHead>Valor</TableHead>
                                                <TableHead>Status</TableHead>
                                                <TableHead>Deletado em</TableHead>
                                                <TableHead className="text-right">Ações</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {itens.map((item) => (
                                                <TableRow key={item.id}>
                                                    <TableCell className="font-medium">
                                                        {item.cliente_nome || 'Cliente Desconhecido'}
                                                    </TableCell>
                                                    <TableCell>{formatMoney(item.valor_principal)}</TableCell>
                                                    <TableCell>
                                                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                                            {item.status}
                                                        </span>
                                                    </TableCell>
                                                    <TableCell className="text-sm text-muted-foreground">
                                                        {formatDate(item.deleted_at)}
                                                        {item.deleted_reason && (
                                                            <div className="text-xs italic mt-1">{item.deleted_reason}</div>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        <div className="flex justify-end gap-2">
                                                            <Button
                                                                size="sm"
                                                                variant="outline"
                                                                className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 border-blue-200"
                                                                onClick={() => handleRestaurar(item.id)}
                                                                disabled={restoringId === item.id || deletingId === item.id}
                                                            >
                                                                {restoringId === item.id ? (
                                                                    <Loader2 className="h-3 w-3 animate-spin" />
                                                                ) : (
                                                                    <Undo2 className="h-3 w-3 sm:mr-1" />
                                                                )}
                                                                <span className="hidden sm:inline">Restaurar</span>
                                                            </Button>
                                                            <Button
                                                                size="sm"
                                                                variant="destructive"
                                                                className="bg-red-50 text-red-600 hover:bg-red-100 border border-red-200"
                                                                onClick={() => handleExcluirDefinitivamente(item.id)}
                                                                disabled={restoringId === item.id || deletingId === item.id}
                                                                title="Excluir Definitivamente"
                                                            >
                                                                {deletingId === item.id ? (
                                                                    <Loader2 className="h-3 w-3 animate-spin" />
                                                                ) : (
                                                                    <Trash2 className="h-3 w-3" />
                                                                )}
                                                            </Button>
                                                        </div>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>

                                {/* Versão Mobile - Cards */}
                                <div className="md:hidden space-y-3">
                                    {itens.map((item) => (
                                        <div key={item.id} className="p-4 bg-muted/30 border border-border rounded-lg space-y-3">
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <h3 className="font-medium">{item.cliente_nome || 'Cliente Desconhecido'}</h3>
                                                    <p className="text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                                                        {formatMoney(item.valor_principal)}
                                                    </p>
                                                </div>
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                                                    {item.status}
                                                </span>
                                            </div>

                                            <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t border-border/50">
                                                <div className="flex justify-between">
                                                    <span>Deletado em:</span>
                                                    <span>{formatDate(item.deleted_at)}</span>
                                                </div>
                                                {item.deleted_reason && (
                                                    <div className="italic text-right">{item.deleted_reason}</div>
                                                )}
                                            </div>

                                            <div className="flex gap-2 pt-2">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    className="flex-1 text-blue-600 border-blue-200"
                                                    onClick={() => handleRestaurar(item.id)}
                                                    disabled={restoringId === item.id || deletingId === item.id}
                                                >
                                                    {restoringId === item.id ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <>
                                                            <Undo2 className="h-4 w-4 mr-1" />
                                                            Restaurar
                                                        </>
                                                    )}
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="destructive"
                                                    className="w-10 px-0 flex-shrink-0 bg-red-50 text-red-600 hover:bg-red-100 border border-red-200"
                                                    onClick={() => handleExcluirDefinitivamente(item.id)}
                                                    disabled={restoringId === item.id || deletingId === item.id}
                                                    title="Excluir Definitivamente"
                                                >
                                                    {deletingId === item.id ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Trash2 className="h-4 w-4" />
                                                    )}
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}

                        {/* Pagination Controls */}
                        {totalPages > 1 && (
                            <div className="flex flex-col sm:flex-row items-center justify-between mt-6 gap-4">
                                <div className="text-xs sm:text-sm text-muted-foreground text-center sm:text-left">
                                    Total de {totalItems} itens excluídos
                                </div>
                                <div className="flex gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => carregarLixeira(page - 1)}
                                        disabled={page <= 1 || loading}
                                    >
                                        Anterior
                                    </Button>
                                    <div className="flex items-center px-2 text-sm font-medium">
                                        {page} / {totalPages}
                                    </div>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => carregarLixeira(page + 1)}
                                        disabled={page >= totalPages || loading}
                                    >
                                        Próxima
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <DialogFooter className="mt-8 pt-4 border-t flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div className="text-xs text-muted-foreground flex items-center gap-2 text-center sm:text-left">
                        <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-500" />
                        <span>Itens na lixeira podem ser excluídos permanentemente após 30 dias automaticamente.</span>
                    </div>
                    <Button variant="secondary" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
                        Fechar
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default LixeiraEmprestimos;
