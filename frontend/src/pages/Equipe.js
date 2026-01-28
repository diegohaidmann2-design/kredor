import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { equipeAPI } from '../api/equipe';
import { useToast } from '../hooks/use-toast';
import Layout from '../components/Layout';
import Header from '../components/Header';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "../components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "../components/ui/dialog";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Checkbox } from "../components/ui/checkbox";
import { Loader2, Plus, Trash2, Mail, Shield, User, Key, Check } from 'lucide-react';

const PERMISSOES_DISPONIVEIS = [
    { id: 'ver_clientes', label: 'Ver Clientes' },
    { id: 'gerir_clientes', label: 'Criar/Editar Clientes' },
    { id: 'ver_emprestimos', label: 'Ver Empréstimos' },
    { id: 'gerir_emprestimos', label: 'Gerir Empréstimos' },
    { id: 'ver_financeiro', label: 'Ver Financeiro' },
    { id: 'gerir_equipe', label: 'Gerir Equipe' },
];

const Equipe = () => {
    const { user } = useAuth();
    const { toast } = useToast();
    const [membros, setMembros] = useState([]);
    const [limites, setLimites] = useState({ usado: 0, total: 0 });
    const [loading, setLoading] = useState(true);
    const [inviteOpen, setInviteOpen] = useState(false);
    const [inviting, setInviting] = useState(false);

    // Manual Creation Mode
    const [mode, setMode] = useState('email'); // 'email' or 'manual'

    // Form state
    const [inviteData, setInviteData] = useState({
        nome: '',
        email: '',
        cargo: 'Colaborador',
        senha: '', // Only for manual
        permissoes: []
    });

    const carregarEquipe = async () => {
        try {
            setLoading(true);
            const data = await equipeAPI.listarEquipe();
            // Backend agora retorna { membros: [], limites: {} }
            // Mas para compatibilidade se retornar array direto (antigo)
            if (Array.isArray(data)) {
                setMembros(data);
                setLimites({ usado: data.length, total: 99 });
            } else {
                setMembros(data.membros || []);
                setLimites(data.limites || { usado: 0, total: 0 });
            }
        } catch (error) {
            toast({
                variant: "destructive",
                title: "Erro ao carregar equipe",
                description: error.response?.data?.detail || "Erro desconhecido"
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        carregarEquipe();
    }, []);

    const handlePermissionChange = (permId) => {
        setInviteData(prev => {
            const current = prev.permissoes;
            if (current.includes(permId)) {
                return { ...prev, permissoes: current.filter(p => p !== permId) };
            } else {
                return { ...prev, permissoes: [...current, permId] };
            }
        });
    };

    const handleInvite = async (e) => {
        e.preventDefault();
        setInviting(true);
        try {
            // Se modo for email, limpa senha antes de enviar para não ir lixo
            const payload = { ...inviteData };
            if (mode === 'email') delete payload.senha;

            await equipeAPI.convidarMembro(payload);

            toast({
                title: mode === 'email' ? "Convite enviado!" : "Membro cadastrado!",
                description: mode === 'email'
                    ? `Email enviado para ${inviteData.email}`
                    : `Usuário ${inviteData.nome} criado com sucesso.`
            });
            setInviteOpen(false);
            setInviteData({ nome: '', email: '', cargo: 'Colaborador', senha: '', permissoes: [] });
            carregarEquipe();
        } catch (error) {
            toast({
                variant: "destructive",
                title: "Erro ao processar",
                description: error.response?.data?.detail || "Erro ao adicionar membro"
            });
        } finally {
            setInviting(false);
        }
    };

    const handleRemove = async (id, nome) => {
        if (!window.confirm(`Tem certeza que deseja remover ${nome} da equipe?`)) return;

        try {
            await equipeAPI.removerMembro(id);
            toast({
                title: "Membro removido",
                description: `${nome} foi removido da equipe.`
            });
            carregarEquipe();
        } catch (error) {
            toast({
                variant: "destructive",
                title: "Erro ao remover",
                description: error.response?.data?.detail
            });
        }
    };

    // Calcular progresso do limite
    const limitPercentage = limites.total > 0 ? (limites.usado / limites.total) * 100 : 0;
    const isLimitReached = limites.total > 0 && limites.usado >= limites.total;

    if (loading) {
        return <div className="flex justify-center p-8"><Loader2 className="h-8 w-8 animate-spin" /></div>;
    }

    return (
        <Layout>
            <Header
                title="Minha Equipe"
                subtitle="Gerencie os membros da sua equipe e permissões."
                action={
                    <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                        <DialogTrigger asChild>
                            <Button disabled={isLimitReached}>
                                <Plus className="mr-2 h-4 w-4" />
                                {isLimitReached ? 'Limite Atingido' : 'Adicionar Membro'}
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-2xl">
                            <DialogHeader>
                                <DialogTitle>Adicionar Novo Membro</DialogTitle>
                                <DialogDescription>
                                    Escolha como deseja adicionar o colaborador.
                                </DialogDescription>
                            </DialogHeader>

                            <Tabs defaultValue="email" onValueChange={setMode} className="w-full">
                                <TabsList className="grid w-full grid-cols-2">
                                    <TabsTrigger value="email">Convidar por Email</TabsTrigger>
                                    <TabsTrigger value="manual">Cadastro Manual</TabsTrigger>
                                </TabsList>

                                <form onSubmit={handleInvite} className="mt-4">
                                    <div className="space-y-4">
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="grid gap-2">
                                                <Label htmlFor="nome">Nome Completo</Label>
                                                <Input
                                                    id="nome"
                                                    value={inviteData.nome}
                                                    onChange={(e) => setInviteData({ ...inviteData, nome: e.target.value })}
                                                    required
                                                />
                                            </div>
                                            <div className="grid gap-2">
                                                <Label htmlFor="cargo">Cargo / Função</Label>
                                                <Input
                                                    id="cargo"
                                                    value={inviteData.cargo}
                                                    onChange={(e) => setInviteData({ ...inviteData, cargo: e.target.value })}
                                                    placeholder="Ex: Vendedor"
                                                />
                                            </div>
                                        </div>

                                        <div className="grid gap-2">
                                            <Label htmlFor="email">Email Corporativo</Label>
                                            <Input
                                                id="email"
                                                type="email"
                                                value={inviteData.email}
                                                onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
                                                required
                                                placeholder="nome@empresa.com"
                                            />
                                        </div>

                                        {mode === 'manual' && (
                                            <div className="grid gap-2 p-4 bg-muted/50 rounded-lg border">
                                                <Label htmlFor="senha" className="flex items-center gap-2">
                                                    <Key className="h-4 w-4" /> Senha de Acesso
                                                </Label>
                                                <Input
                                                    id="senha"
                                                    type="password"
                                                    value={inviteData.senha}
                                                    onChange={(e) => setInviteData({ ...inviteData, senha: e.target.value })}
                                                    required={mode === 'manual'}
                                                    placeholder="Defina a senha inicial"
                                                    description="O usuário poderá alterar depois."
                                                />
                                                <p className="text-xs text-muted-foreground">
                                                    Você precisará informar esta senha ao funcionário.
                                                </p>
                                            </div>
                                        )}

                                        <div className="space-y-2">
                                            <Label className="flex items-center gap-2">
                                                <Shield className="h-4 w-4" /> Permissões de Acesso
                                            </Label>
                                            <div className="grid grid-cols-2 gap-2 border p-3 rounded-md">
                                                {PERMISSOES_DISPONIVEIS.map((perm) => (
                                                    <div key={perm.id} className="flex items-center space-x-2">
                                                        <Checkbox
                                                            id={perm.id}
                                                            checked={inviteData.permissoes.includes(perm.id)}
                                                            onCheckedChange={() => handlePermissionChange(perm.id)}
                                                        />
                                                        <label
                                                            htmlFor={perm.id}
                                                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                                                        >
                                                            {perm.label}
                                                        </label>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    <DialogFooter className="mt-6">
                                        <Button type="submit" disabled={inviting}>
                                            {inviting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : (
                                                mode === 'email' ? <Mail className="mr-2 h-4 w-4" /> : <User className="mr-2 h-4 w-4" />
                                            )}
                                            {mode === 'email' ? 'Enviar Convite' : 'Criar Usuário'}
                                        </Button>
                                    </DialogFooter>
                                </form>
                            </Tabs>
                        </DialogContent>
                    </Dialog>
                }
            />

            <div className="p-4 sm:p-6 space-y-6">
                <div className="flex items-center gap-4 text-sm bg-muted/30 p-4 rounded-lg border">
                    <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Uso do Plano:</span>
                        <span className="font-medium">{limites.usado} / {limites.total === 999999 ? 'Ilimitado' : limites.total} membros</span>
                    </div>
                    {limites.total < 999999 && (
                        <div className="h-2 w-32 bg-secondary rounded-full overflow-hidden">
                            <div
                                className={`h-full ${isLimitReached ? 'bg-red-500' : 'bg-primary'}`}
                                style={{ width: `${Math.min(limitPercentage, 100)}%` }}
                            />
                        </div>
                    )}
                </div>

                {/* Desktop View */}
                <div className="hidden md:block rounded-md border bg-card">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Nome</TableHead>
                                <TableHead>Email</TableHead>
                                <TableHead>Cargo</TableHead>
                                <TableHead>Permissões</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="text-right">Ações</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {membros.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                        Nenhum membro na equipe. Adicione alguém para começar!
                                    </TableCell>
                                </TableRow>
                            ) : (
                                membros.map((membro) => (
                                    <TableRow key={membro.id}>
                                        <TableCell className="font-medium">{membro.nome}</TableCell>
                                        <TableCell>{membro.email}</TableCell>
                                        <TableCell>{membro.cargo || '-'}</TableCell>
                                        <TableCell>
                                            <div className="flex flex-wrap gap-1">
                                                {(membro.permissoes || []).slice(0, 3).map(p => (
                                                    <Badge key={p} variant="outline" className="text-xs">
                                                        {PERMISSOES_DISPONIVEIS.find(pd => pd.id === p)?.label || p}
                                                    </Badge>
                                                ))}
                                                {(membro.permissoes || []).length > 3 && (
                                                    <Badge variant="outline" className="text-xs">+{membro.permissoes.length - 3}</Badge>
                                                )}
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            {membro.convite_pendente ? (
                                                <Badge variant="secondary">Pendente</Badge>
                                            ) : membro.ativo ? (
                                                <Badge variant="default" className="bg-green-600">Ativo</Badge>
                                            ) : (
                                                <Badge variant="destructive">Inativo</Badge>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleRemove(membro.id, membro.nome)}
                                                title="Remover / Cancelar Convite"
                                            >
                                                <Trash2 className="h-4 w-4 text-red-500" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>

                {/* Mobile View */}
                <div className="md:hidden space-y-4">
                    {membros.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground bg-card rounded-lg border p-4">
                            Nenhum membro na equipe. Adicione alguém para começar!
                        </div>
                    ) : (
                        membros.map((membro) => (
                            <div key={membro.id} className="bg-card rounded-lg border p-4 space-y-3 shadow-sm">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h3 className="font-semibold text-lg">{membro.nome}</h3>
                                        <p className="text-sm text-muted-foreground">{membro.email}</p>
                                        <p className="text-xs text-muted-foreground mt-1">{membro.cargo || 'Sem cargo'}</p>
                                    </div>
                                    {membro.convite_pendente ? (
                                        <Badge variant="secondary">Pendente</Badge>
                                    ) : membro.ativo ? (
                                        <Badge variant="default" className="bg-green-600">Ativo</Badge>
                                    ) : (
                                        <Badge variant="destructive">Inativo</Badge>
                                    )}
                                </div>

                                <div className="pt-2 border-t">
                                    <p className="text-xs font-medium text-muted-foreground mb-2">Permissões:</p>
                                    <div className="flex flex-wrap gap-1">
                                        {(membro.permissoes || []).length === 0 ? (
                                            <span className="text-xs text-muted-foreground italic">Nenhuma</span>
                                        ) : (
                                            membro.permissoes.map(p => (
                                                <Badge key={p} variant="outline" className="text-xs">
                                                    {PERMISSOES_DISPONIVEIS.find(pd => pd.id === p)?.label || p}
                                                </Badge>
                                            ))
                                        )}
                                    </div>
                                </div>

                                <div className="pt-2 flex justify-end">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="text-red-500 hover:text-red-600 hover:bg-red-50"
                                        onClick={() => handleRemove(membro.id, membro.nome)}
                                    >
                                        <Trash2 className="h-4 w-4 mr-2" />
                                        Remover da Equipe
                                    </Button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </Layout>
    );
};

export default Equipe;
