import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { equipeAPI } from '../api/equipe';
import { useToast } from '../hooks/use-toast';
import Layout from '../components/Layout';
import Header from '../components/Header';
import { PageHeader } from '../components/uikit';
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
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Checkbox } from "../components/ui/checkbox";
import {
    Loader2, Plus, Trash2, Mail, Shield, User, Key, Check,
    MoreHorizontal, RotateCcw, Send, UserCheck,
} from 'lucide-react';

// Mínimo espelhado de services/auth.validar_forca_senha: a régua de verdade é do servidor,
// isto só evita a viagem até lá para o caso óbvio.
const SENHA_MINIMA = 8;

const FORM_VAZIO = { nome: '', email: '', cargo: 'Colaborador', senha: '', permissoes: [] };

const erroDe = (error, padrao) => {
    const detalhe = error?.response?.data?.detail;
    if (typeof detalhe === 'string') return detalhe;
    if (detalhe?.mensagem) return detalhe.mensagem;
    return padrao;
};

const Equipe = () => {
    const { user } = useAuth();
    const { toast } = useToast();
    const [membros, setMembros] = useState([]);
    const [limites, setLimites] = useState({ usado: 0, total: 0, ilimitado: false });
    // As permissões vêm do servidor (GET /equipe): tela e backend não podem divergir sobre o
    // que existe — uma lista fixa aqui já deixou checkboxes que nada honrava.
    const [permissoesDisponiveis, setPermissoesDisponiveis] = useState([]);
    const [loading, setLoading] = useState(true);
    const [inviteOpen, setInviteOpen] = useState(false);
    const [inviting, setInviting] = useState(false);
    const [acaoEmCurso, setAcaoEmCurso] = useState(null);

    // Modo de criação: convite por email ou senha definida na hora
    const [mode, setMode] = useState('email');
    const [inviteData, setInviteData] = useState(FORM_VAZIO);

    // Edição de permissões de um membro já criado
    const [editando, setEditando] = useState(null);
    const [permissoesEdicao, setPermissoesEdicao] = useState([]);
    const [salvandoPermissoes, setSalvandoPermissoes] = useState(false);

    const rotuloDe = useCallback(
        (id) => permissoesDisponiveis.find((p) => p.id === id)?.label || id,
        [permissoesDisponiveis]
    );

    const carregarEquipe = useCallback(async ({ silencioso = false } = {}) => {
        try {
            if (!silencioso) setLoading(true);
            const data = await equipeAPI.listarEquipe();
            setMembros(data.membros || []);
            setLimites(data.limites || { usado: 0, total: 0, ilimitado: false });
            setPermissoesDisponiveis(data.permissoes_disponiveis || []);
        } catch (error) {
            toast({
                variant: "destructive",
                title: "Erro ao carregar equipe",
                description: erroDe(error, "Não foi possível carregar a equipe agora."),
            });
        } finally {
            setLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        carregarEquipe();
    }, [carregarEquipe]);

    const alternar = (lista, permId) => (
        lista.includes(permId) ? lista.filter((p) => p !== permId) : [...lista, permId]
    );

    const handleInvite = async (e) => {
        e.preventDefault();

        if (mode === 'manual' && inviteData.senha.length < SENHA_MINIMA) {
            toast({
                variant: "destructive",
                title: "Senha muito curta",
                description: `A senha do membro precisa de pelo menos ${SENHA_MINIMA} caracteres, com letras e números.`,
            });
            return;
        }

        setInviting(true);
        try {
            const payload = { ...inviteData };
            if (mode === 'email') delete payload.senha;

            const resposta = await equipeAPI.convidarMembro(payload);

            // O servidor avisa quando o email de convite não saiu — antes a tela dizia
            // "Convite enviado" para um email que nunca foi entregue.
            const falhouEmail = mode === 'email' && resposta?.convite_enviado === false;
            toast({
                variant: falhouEmail ? "destructive" : undefined,
                title: falhouEmail
                    ? "Membro criado, convite não enviado"
                    : (mode === 'email' ? "Convite enviado!" : "Membro cadastrado!"),
                description: resposta?.message
                    || (mode === 'email' ? `Email enviado para ${inviteData.email}` : `Usuário ${inviteData.nome} criado.`),
            });
            setInviteOpen(false);
            setInviteData(FORM_VAZIO);
            carregarEquipe({ silencioso: true });
        } catch (error) {
            toast({
                variant: "destructive",
                title: "Erro ao adicionar membro",
                description: erroDe(error, "Não foi possível adicionar o membro."),
            });
        } finally {
            setInviting(false);
        }
    };

    const executar = async (id, chamada, titulo, recarregar = true) => {
        setAcaoEmCurso(id);
        try {
            const resposta = await chamada();
            toast({ title: titulo, description: resposta?.message });
            if (recarregar) await carregarEquipe({ silencioso: true });
        } catch (error) {
            toast({
                variant: "destructive",
                title: "Não foi possível concluir",
                description: erroDe(error, "Tente novamente em alguns instantes."),
            });
        } finally {
            setAcaoEmCurso(null);
        }
    };

    const handleRemove = (membro) => {
        const pergunta = membro.convite_pendente
            ? `Cancelar o convite de ${membro.nome}?`
            : `Desativar o acesso de ${membro.nome}? Ele perde o acesso imediatamente e você pode reativar depois.`;
        if (!window.confirm(pergunta)) return;
        executar(membro.id, () => equipeAPI.removerMembro(membro.id), "Acesso removido");
    };

    const handleReativar = (membro) =>
        executar(membro.id, () => equipeAPI.reativarMembro(membro.id), "Membro reativado");

    const handleReenviar = (membro) =>
        executar(membro.id, () => equipeAPI.reenviarConvite(membro.id), "Convite reenviado");

    const abrirEdicao = (membro) => {
        setEditando(membro);
        setPermissoesEdicao(membro.permissoes || []);
    };

    const salvarPermissoes = async () => {
        if (!editando) return;
        setSalvandoPermissoes(true);
        try {
            await equipeAPI.atualizarPermissoes(editando.id, { permissoes: permissoesEdicao });
            toast({
                title: "Permissões atualizadas",
                description: `${editando.nome} agora tem ${permissoesEdicao.length} permissão(ões).`,
            });
            setEditando(null);
            carregarEquipe({ silencioso: true });
        } catch (error) {
            toast({
                variant: "destructive",
                title: "Erro ao salvar permissões",
                description: erroDe(error, "Não foi possível salvar as permissões."),
            });
        } finally {
            setSalvandoPermissoes(false);
        }
    };

    const semEquipeNoPlano = limites.total === 0 && !limites.ilimitado;
    const limiteAtingido = !limites.ilimitado && limites.total > 0 && limites.usado >= limites.total;
    const percentual = limites.ilimitado || limites.total <= 0
        ? 0
        : Math.min(100, (limites.usado / limites.total) * 100);

    const CaixaDePermissoes = ({ selecionadas, onToggle, testid }) => (
        <div className="grid sm:grid-cols-2 gap-2 border p-3 rounded-md" data-testid={testid}>
            {permissoesDisponiveis.length === 0 ? (
                <p className="text-sm text-muted-foreground">Carregando permissões...</p>
            ) : (
                permissoesDisponiveis.map((perm) => {
                    const bloqueada = perm.delegavel === false;
                    return (
                        <div key={perm.id} className="flex items-start space-x-2">
                            <Checkbox
                                id={`${testid}-${perm.id}`}
                                checked={selecionadas.includes(perm.id)}
                                disabled={bloqueada}
                                onCheckedChange={() => onToggle(perm.id)}
                            />
                            <label
                                htmlFor={`${testid}-${perm.id}`}
                                className={`text-sm font-medium leading-snug ${bloqueada ? 'text-muted-foreground' : 'cursor-pointer'}`}
                                title={bloqueada ? 'Somente o dono da conta pode conceder esta permissão' : undefined}
                            >
                                {perm.label}
                            </label>
                        </div>
                    );
                })
            )}
        </div>
    );

    const Status = ({ membro }) => {
        if (membro.convite_pendente) {
            return membro.convite_expirado
                ? <Badge variant="destructive">Convite expirado</Badge>
                : <Badge variant="secondary">Convite pendente</Badge>;
        }
        return membro.ativo
            ? <Badge variant="default" className="bg-green-600">Ativo</Badge>
            : <Badge variant="destructive">Inativo</Badge>;
    };

    const Permissoes = ({ membro, limite = 3 }) => {
        const lista = membro.permissoes || [];
        if (lista.length === 0) {
            return (
                <span className="text-xs text-amber-600 dark:text-amber-500 italic">
                    Nenhuma — sem acesso aos dados
                </span>
            );
        }
        return (
            <div className="flex flex-wrap gap-1">
                {lista.slice(0, limite).map((p) => (
                    <Badge key={p} variant="outline" className="text-xs">{rotuloDe(p)}</Badge>
                ))}
                {lista.length > limite && (
                    <Badge variant="outline" className="text-xs">+{lista.length - limite}</Badge>
                )}
            </div>
        );
    };

    const AcoesMembro = ({ membro }) => (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant="ghost"
                    size="icon"
                    disabled={acaoEmCurso === membro.id}
                    data-testid={`acoes-membro-${membro.id}`}
                    title="Ações"
                >
                    {acaoEmCurso === membro.id
                        ? <Loader2 className="h-4 w-4 animate-spin" />
                        : <MoreHorizontal className="h-4 w-4" />}
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuItem onSelect={() => setTimeout(() => abrirEdicao(membro), 50)}>
                    <Shield className="h-4 w-4 mr-2" /> Editar permissões
                </DropdownMenuItem>
                {membro.convite_pendente && (
                    <DropdownMenuItem onSelect={() => setTimeout(() => handleReenviar(membro), 50)}>
                        <Send className="h-4 w-4 mr-2" /> Reenviar convite
                    </DropdownMenuItem>
                )}
                {!membro.convite_pendente && !membro.ativo && (
                    <DropdownMenuItem onSelect={() => setTimeout(() => handleReativar(membro), 50)}>
                        <RotateCcw className="h-4 w-4 mr-2" /> Reativar acesso
                    </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                    className="text-red-600 focus:text-red-600"
                    onSelect={() => setTimeout(() => handleRemove(membro), 50)}
                >
                    <Trash2 className="h-4 w-4 mr-2" />
                    {membro.convite_pendente ? 'Cancelar convite' : 'Desativar acesso'}
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );

    if (loading) {
        return (
            <Layout>
                <div className="flex justify-center p-8"><Loader2 className="h-8 w-8 animate-spin" /></div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="container mx-auto px-4 sm:px-6 py-8 space-y-6 font-satoshi">
                <PageHeader title="Minha Equipe" subtitle="Cada membro entra com usuário e senha próprios e vê apenas o que você liberar." testId="equipe-title" />
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex items-center gap-4 text-sm bg-muted/30 p-4 rounded-lg border flex-1">
                        <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-muted-foreground" />
                            <span className="text-muted-foreground">Membros:</span>
                            <span className="font-medium" data-testid="uso-membros">
                                {limites.usado}
                                {limites.ilimitado ? ' (ilimitado)' : ` / ${limites.total}`}
                            </span>
                        </div>
                        {!limites.ilimitado && limites.total > 0 && (
                            <div className="h-2 w-32 bg-secondary rounded-full overflow-hidden">
                                <div
                                    className={`h-full ${limiteAtingido ? 'bg-red-500' : 'bg-primary'}`}
                                    style={{ width: `${percentual}%` }}
                                />
                            </div>
                        )}
                    </div>

                    <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                        <DialogTrigger asChild>
                            <Button
                                disabled={semEquipeNoPlano || limiteAtingido}
                                data-testid="botao-adicionar-membro"
                                title={semEquipeNoPlano
                                    ? 'Seu plano não inclui membros de equipe'
                                    : (limiteAtingido ? 'Limite de membros do plano atingido' : undefined)}
                            >
                                <Plus className="h-4 w-4 mr-2" /> Adicionar membro
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                            <DialogHeader>
                                <DialogTitle>Adicionar novo membro</DialogTitle>
                                <DialogDescription>
                                    Escolha como o colaborador vai definir a senha de acesso.
                                </DialogDescription>
                            </DialogHeader>

                            <Tabs value={mode} onValueChange={setMode} className="w-full">
                                <TabsList className="grid w-full grid-cols-2">
                                    <TabsTrigger value="email">
                                        <Mail className="h-4 w-4 mr-2" /> Convidar por email
                                    </TabsTrigger>
                                    <TabsTrigger value="manual">
                                        <Key className="h-4 w-4 mr-2" /> Definir senha agora
                                    </TabsTrigger>
                                </TabsList>
                            </Tabs>

                            <form onSubmit={handleInvite} className="mt-4">
                                <div className="space-y-4">
                                    <div className="grid sm:grid-cols-2 gap-4">
                                        <div className="grid gap-2">
                                            <Label htmlFor="nome">Nome completo</Label>
                                            <Input
                                                id="nome"
                                                value={inviteData.nome}
                                                onChange={(e) => setInviteData({ ...inviteData, nome: e.target.value })}
                                                required
                                                data-testid="input-membro-nome"
                                            />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label htmlFor="cargo">Cargo / função</Label>
                                            <Input
                                                id="cargo"
                                                value={inviteData.cargo}
                                                onChange={(e) => setInviteData({ ...inviteData, cargo: e.target.value })}
                                                placeholder="Ex: Vendedor"
                                                data-testid="input-membro-cargo"
                                            />
                                        </div>
                                    </div>

                                    <div className="grid gap-2">
                                        <Label htmlFor="email">Email</Label>
                                        <Input
                                            id="email"
                                            type="email"
                                            value={inviteData.email}
                                            onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
                                            required
                                            placeholder="nome@empresa.com"
                                            data-testid="input-membro-email"
                                        />
                                    </div>

                                    {mode === 'manual' && (
                                        <div className="grid gap-2 p-4 bg-muted/50 rounded-lg border">
                                            <Label htmlFor="senha" className="flex items-center gap-2">
                                                <Key className="h-4 w-4" /> Senha de acesso
                                            </Label>
                                            <Input
                                                id="senha"
                                                type="password"
                                                value={inviteData.senha}
                                                onChange={(e) => setInviteData({ ...inviteData, senha: e.target.value })}
                                                required={mode === 'manual'}
                                                minLength={SENHA_MINIMA}
                                                autoComplete="new-password"
                                                placeholder="Mínimo de 8 caracteres, com letras e números"
                                                data-testid="input-membro-senha"
                                            />
                                            <p className="text-xs text-muted-foreground">
                                                Informe esta senha ao funcionário — ele pode trocá-la depois em
                                                Configurações.
                                            </p>
                                        </div>
                                    )}

                                    <div className="space-y-2">
                                        <Label className="flex items-center gap-2">
                                            <Shield className="h-4 w-4" /> Permissões de acesso
                                        </Label>
                                        <CaixaDePermissoes
                                            selecionadas={inviteData.permissoes}
                                            onToggle={(id) => setInviteData((prev) => ({
                                                ...prev, permissoes: alternar(prev.permissoes, id),
                                            }))}
                                            testid="permissoes-novo-membro"
                                        />
                                        <p className="text-xs text-muted-foreground">
                                            Sem nenhuma marcada, o membro entra no sistema mas não vê dado nenhum.
                                            Pagamentos, configurações e a carteira de saldo são sempre só suas.
                                        </p>
                                    </div>
                                </div>

                                <DialogFooter className="mt-6">
                                    <Button type="submit" disabled={inviting} data-testid="salvar-membro">
                                        {inviting
                                            ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Salvando...</>
                                            : <><Check className="h-4 w-4 mr-2" /> {mode === 'email' ? 'Enviar convite' : 'Cadastrar membro'}</>}
                                    </Button>
                                </DialogFooter>
                            </form>
                        </DialogContent>
                    </Dialog>
                </div>

                {semEquipeNoPlano && (
                    <div
                        className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm"
                        data-testid="aviso-plano-sem-equipe"
                    >
                        Seu plano atual não inclui membros de equipe. Faça upgrade para dividir o
                        acesso sem compartilhar a sua senha.
                    </div>
                )}

                {/* Desktop */}
                <div className="hidden md:block rounded-xl ring-1 ring-border bg-card overflow-hidden">
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
                                        Nenhum membro na equipe. Adicione alguém para começar.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                membros.map((membro) => (
                                    <TableRow key={membro.id} data-testid={`membro-${membro.id}`}>
                                        <TableCell className="font-medium">{membro.nome}</TableCell>
                                        <TableCell>{membro.email}</TableCell>
                                        <TableCell>{membro.cargo || '-'}</TableCell>
                                        <TableCell><Permissoes membro={membro} /></TableCell>
                                        <TableCell><Status membro={membro} /></TableCell>
                                        <TableCell className="text-right">
                                            <AcoesMembro membro={membro} />
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>

                {/* Mobile */}
                <div className="md:hidden space-y-4">
                    {membros.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground bg-card rounded-lg border p-4">
                            Nenhum membro na equipe. Adicione alguém para começar.
                        </div>
                    ) : (
                        membros.map((membro) => (
                            <div
                                key={membro.id}
                                className="bg-card rounded-lg border p-4 space-y-3 shadow-sm"
                                data-testid={`membro-card-${membro.id}`}
                            >
                                <div className="flex justify-between items-start gap-2">
                                    <div className="min-w-0">
                                        <h3 className="font-semibold text-lg truncate">{membro.nome}</h3>
                                        <p className="text-sm text-muted-foreground truncate">{membro.email}</p>
                                        <p className="text-xs text-muted-foreground mt-1">{membro.cargo || 'Sem cargo'}</p>
                                    </div>
                                    <div className="flex items-center gap-1 shrink-0">
                                        <Status membro={membro} />
                                        <AcoesMembro membro={membro} />
                                    </div>
                                </div>

                                <div className="pt-2 border-t">
                                    <p className="text-xs font-medium text-muted-foreground mb-2">Permissões:</p>
                                    <Permissoes membro={membro} limite={99} />
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Edição de permissões */}
            <Dialog open={!!editando} onOpenChange={(aberto) => !aberto && setEditando(null)}>
                <DialogContent className="max-w-xl">
                    <DialogHeader>
                        <DialogTitle>Permissões de {editando?.nome}</DialogTitle>
                        <DialogDescription>
                            A mudança vale na próxima requisição do membro — não é preciso pedir que
                            ele saia e entre de novo.
                        </DialogDescription>
                    </DialogHeader>

                    <CaixaDePermissoes
                        selecionadas={permissoesEdicao}
                        onToggle={(id) => setPermissoesEdicao((prev) => alternar(prev, id))}
                        testid="permissoes-edicao"
                    />

                    <DialogFooter className="mt-4">
                        <Button variant="outline" onClick={() => setEditando(null)}>Cancelar</Button>
                        <Button
                            onClick={salvarPermissoes}
                            disabled={salvandoPermissoes}
                            data-testid="salvar-permissoes"
                        >
                            {salvandoPermissoes
                                ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Salvando...</>
                                : <><UserCheck className="h-4 w-4 mr-2" /> Salvar permissões</>}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </Layout>
    );
};

export default Equipe;
