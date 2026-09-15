import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import Header from '../components/Header';
import { useAuth } from '../context/AuthContext';
import { useModal } from '../components/Modal';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { User, Mail, Calendar, CreditCard, Shield, Lock, Briefcase, Loader2, Check } from 'lucide-react';
import { formatarData } from '../utils/formatters';
import { authAPI } from '../api/api';
import { toast } from '../hooks/use-toast';

const NOME_MINIMO = 2;
const NOME_MAXIMO = 120;

const Perfil = () => {
  const { user, refreshUser } = useAuth();
  const modal = useModal();
  const navigate = useNavigate();
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState('');
  const [salvando, setSalvando] = useState(false);

  // Cargo e permissões do membro de equipe. Vêm de /auth/permissoes porque o membro não
  // alcança GET /equipe (é do dono) — e os rótulos saem do servidor, que é quem concede.
  const [vinculoEquipe, setVinculoEquipe] = useState(null);
  const ehMembroDeEquipe = !!user?.owner_id;

  // Estado para 2FA
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [senha, setSenha] = useState('');
  const [loading2FA, setLoading2FA] = useState(false);

  // Estado para Alterar Senha
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
  const [senhaAtual, setSenhaAtual] = useState('');
  const [novaSenha, setNovaSenha] = useState('');
  const [confirmarNovaSenha, setConfirmarNovaSenha] = useState('');
  const [loadingSenha, setLoadingSenha] = useState(false);

  useEffect(() => {
    if (user) {
      setNome(user.nome || '');
      setTwoFactorEnabled(user.two_factor_enabled || false);
    }
  }, [user]);

  // Carregar status do 2FA
  useEffect(() => {
    const loadTwoFactorStatus = async () => {
      try {
        const response = await authAPI.getStatus2FA();
        setTwoFactorEnabled(response.data.two_factor_enabled);
      } catch (error) {
        toast({ title: 'Erro', description: "Não foi possível carregar status 2FA.", variant: 'destructive' });
        console.error('Erro ao carregar status 2FA:', error);
      }
    };

    loadTwoFactorStatus();
  }, []);

  // Cargo e permissões: é o único lugar do sistema em que o membro descobre o que pode fazer.
  useEffect(() => {
    if (!ehMembroDeEquipe) return;
    let ativo = true;
    (async () => {
      try {
        const { data } = await authAPI.permissoes();
        if (ativo) setVinculoEquipe(data.equipe || null);
      } catch (error) {
        // silencioso: é informação complementar do perfil; a tela funciona sem ela e um
        // aviso aqui competiria com o conteúdo principal da página.
        console.error('Erro ao carregar vínculo de equipe:', error);
      }
    })();
    return () => { ativo = false; };
  }, [ehMembroDeEquipe]);

  const handleSalvar = useCallback(async () => {
    const limpo = nome.trim();

    // Mesma régua do servidor (AtualizarPerfilRequest): aqui só para não fazer a viagem.
    if (limpo.length < NOME_MINIMO) {
      modal.error('Nome inválido', `O nome deve ter pelo menos ${NOME_MINIMO} caracteres.`);
      return;
    }
    if (limpo.length > NOME_MAXIMO) {
      modal.error('Nome muito longo', `O nome deve ter no máximo ${NOME_MAXIMO} caracteres.`);
      return;
    }
    if (limpo === user?.nome) {
      setEditando(false);
      return;
    }

    setSalvando(true);
    try {
      await authAPI.atualizarPerfil({ nome: limpo });
      // refreshUser antes de sair do modo de edição: sem isto a tela volta a mostrar o nome
      // antigo por um instante, que foi exatamente como o botão parecia perder o dado.
      await refreshUser();
      setEditando(false);
      toast({ title: 'Perfil atualizado', description: 'Seu nome foi alterado com sucesso.' });
    } catch (error) {
      modal.error(
        'Erro ao salvar',
        error.response?.data?.detail || 'Não foi possível salvar o seu perfil agora.'
      );
    } finally {
      setSalvando(false);
    }
  }, [nome, user, refreshUser, modal]);

  const handleCancelar = () => {
    setNome(user?.nome || '');   // descarta o que foi digitado
    setEditando(false);
  };

  // Função para alternar 2FA
  const handleToggle2FA = async () => {
    if (!twoFactorEnabled) {
      // Ativar 2FA - pedir senha
      setShowPasswordModal(true);
    } else {
      // Desativar 2FA - pedir senha
      modal.warning(
        'Desativar Autenticação de Dois Fatores',
        'Você tem certeza que deseja desativar o 2FA? Isso tornará sua conta menos segura.',
        {
          confirmText: 'Sim, Desativar',
          cancelText: 'Cancelar',
          onConfirm: () => setShowPasswordModal(true)
        }
      );
    }
  };

  // Confirmar alteração com senha
  const handleConfirmToggle2FA = async () => {
    if (!senha) {
      modal.error('Senha Obrigatória', 'Por favor, digite sua senha para continuar.');
      return;
    }

    setLoading2FA(true);

    try {
      const response = await authAPI.toggle2FA({
        enabled: !twoFactorEnabled,
        senha
      });

      setTwoFactorEnabled(!twoFactorEnabled);
      setShowPasswordModal(false);
      setSenha('');

      // Atualizar usuário
      await refreshUser();

      modal.success(
        twoFactorEnabled ? '2FA Desativado' : '2FA Ativado',
        response.data.message ||
        (twoFactorEnabled
          ? 'Autenticação de dois fatores desativada com sucesso.'
          : 'Autenticação de dois fatores ativada! Na próxima vez que fizer login, você receberá um código por email.')
      );
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Erro ao alterar configuração de 2FA. Tente novamente.';
      modal.error('Erro', errorMsg);
    } finally {
      setLoading2FA(false);
    }
  };

  const handleAlterarSenha = async () => {
    if (!senhaAtual || !novaSenha || !confirmarNovaSenha) {
      modal.error('Campos Obrigatórios', 'Por favor, preencha todos os campos.');
      return;
    }

    if (novaSenha !== confirmarNovaSenha) {
      modal.error('Senhas não conferem', 'A nova senha e a confirmação devem ser iguais.');
      return;
    }

    if (novaSenha.length < 8) {
      modal.error('Senha Curta', 'A nova senha deve ter pelo menos 8 caracteres, com letras e números.');
      return;
    }

    setLoadingSenha(true);

    try {
      await authAPI.alterarSenha({
        senha_atual: senhaAtual,
        nova_senha: novaSenha
      });

      setShowChangePasswordModal(false);
      setSenhaAtual('');
      setNovaSenha('');
      setConfirmarNovaSenha('');

      modal.success('Sucesso', 'Sua senha foi alterada com sucesso!');
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Erro ao alterar senha. Verifique sua senha atual.';
      modal.error('Erro', errorMsg);
    } finally {
      setLoadingSenha(false);
    }
  };

  // Antes era `return null`: tela branca enquanto o /auth/me não voltava.
  if (!user) return <Loading message="Carregando perfil..." />;

  return (
    <Layout>
      <Header
        title="Meu Perfil"
        subtitle="Gerencie suas informações pessoais"
      />

      <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-6">
        {/* Informações Pessoais */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-5 h-5" />
              Informações Pessoais
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                Nome
              </label>
              {editando ? (
                <>
                  <input
                    type="text"
                    value={nome}
                    onChange={(e) => setNome(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSalvar();
                      if (e.key === 'Escape') handleCancelar();
                    }}
                    minLength={NOME_MINIMO}
                    maxLength={NOME_MAXIMO}
                    autoFocus
                    className="w-full px-3 py-2 border border-border rounded-lg bg-background"
                    data-testid="input-perfil-nome"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Este nome aparece nos contratos, nos recibos e no convite que você envia
                    para a sua equipe.
                  </p>
                </>
              ) : (
                <p className="text-lg font-medium" data-testid="perfil-nome">{user.nome}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                <Mail className="w-4 h-4 inline mr-2" />
                Email
              </label>
              <p className="text-lg" data-testid="perfil-email">{user.email}</p>
              <p className="text-xs text-muted-foreground mt-1">
                O email é o seu acesso ao sistema e não pode ser alterado aqui. Para trocá-lo,
                fale com o suporte.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                <Calendar className="w-4 h-4 inline mr-2" />
                Membro desde
              </label>
              <p className="text-lg" data-testid="perfil-membro-desde">{formatarData(user.created_at)}</p>
            </div>

            {editando ? (
              <div className="flex gap-3 pt-4">
                <Button onClick={handleSalvar} disabled={salvando} data-testid="salvar-perfil">
                  {salvando
                    ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Salvando...</>
                    : <><Check className="w-4 h-4 mr-2" /> Salvar</>}
                </Button>
                <Button variant="outline" onClick={handleCancelar} disabled={salvando}>
                  Cancelar
                </Button>
              </div>
            ) : (
              <Button onClick={() => setEditando(true)} data-testid="editar-perfil">
                Editar Perfil
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Vínculo de equipe (só para membro) */}
        {ehMembroDeEquipe && (
          <Card data-testid="card-vinculo-equipe">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Briefcase className="w-5 h-5" />
                Meu acesso
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2">
                  Cargo
                </label>
                <p className="text-lg font-medium" data-testid="perfil-cargo">
                  {vinculoEquipe?.cargo || user.cargo || 'Sem cargo definido'}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2">
                  O que você pode fazer
                </label>
                {(vinculoEquipe?.permissoes || []).length === 0 ? (
                  <p className="text-sm text-amber-600 dark:text-amber-500" data-testid="perfil-sem-permissoes">
                    O dono da conta ainda não liberou nenhuma área para você.
                  </p>
                ) : (
                  <ul className="space-y-1" data-testid="perfil-permissoes">
                    {vinculoEquipe.permissoes.map((perm) => (
                      <li key={perm.id} className="flex items-center gap-2 text-sm">
                        <Check className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        {perm.label}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <p className="text-xs text-muted-foreground pt-2 border-t">
                Quem define o seu cargo e as suas permissões é o dono da conta, em Minha Equipe.
                A assinatura também é dele — você não precisa de plano próprio.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Plano e Assinatura (do dono da conta; o membro usa a assinatura dele) */}
        {!ehMembroDeEquipe && (
        <Card data-testid="card-plano">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-5 h-5" />
              Plano e Assinatura
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                Plano Atual
              </label>
              <p className="text-lg font-semibold capitalize">
                {user.plano}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                Status
              </label>
              <p className="text-lg">
                {user.plano_ativo ? (
                  <span className="text-green-600 dark:text-green-400">✓ Ativo</span>
                ) : (
                  <span className="text-red-600 dark:text-red-400">✗ Inativo</span>
                )}
              </p>
            </div>

            {user.data_expiracao_plano && (
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2">
                  Expira em
                </label>
                <p className="text-lg">{formatarData(user.data_expiracao_plano)}</p>
              </div>
            )}

            <Button
              variant="outline"
              onClick={() => navigate('/assinatura')}
              className="mt-4"
              data-testid="gerenciar-assinatura"
            >
              Gerenciar Assinatura
            </Button>
          </CardContent>
        </Card>
        )}

        {/* Segurança */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Segurança
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Autenticação de Dois Fatores */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="text-lg font-semibold">Autenticação de Dois Fatores (2FA)</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Adicione uma camada extra de segurança à sua conta. Quando ativado, você receberá um código por email ao fazer login.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 mt-4 p-4 bg-muted/30 rounded-lg">
                <div className="flex-shrink-0">
                  {twoFactorEnabled ? (
                    <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                      <Shield className="w-5 h-5 text-green-600 dark:text-green-400" />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                      <Shield className="w-5 h-5 text-gray-400" />
                    </div>
                  )}
                </div>

                <div className="flex-1">
                  <p className="font-medium">
                    {twoFactorEnabled ? 'Ativado' : 'Desativado'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {twoFactorEnabled
                      ? 'Sua conta está protegida com 2FA'
                      : 'Ative para maior segurança'
                    }
                  </p>
                </div>

                <Button
                  variant={twoFactorEnabled ? 'outline' : 'default'}
                  onClick={handleToggle2FA}
                  data-testid="toggle-2fa"
                >
                  {twoFactorEnabled ? 'Desativar' : 'Ativar'}
                </Button>
              </div>

              {twoFactorEnabled && (
                <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <p className="text-xs text-blue-700 dark:text-blue-400">
                    ✓ Ao fazer login, você receberá um código de 6 dígitos por email. O código expira em 10 minutos e você tem 3 tentativas para inserí-lo corretamente.
                  </p>
                </div>
              )}
            </div>

            <div className="pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => setShowChangePasswordModal(true)}
                data-testid="abrir-alterar-senha"
              >
                <Lock className="w-4 h-4 mr-2" />
                Alterar Senha
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Modal de confirmação de senha para 2FA */}
        {showPasswordModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6 space-y-4">
              <h3 className="text-xl font-bold">
                {twoFactorEnabled ? 'Desativar' : 'Ativar'} 2FA
              </h3>

              <p className="text-sm text-muted-foreground">
                Por segurança, por favor confirme sua senha para continuar.
              </p>

              <div className="space-y-2">
                <Label htmlFor="senha-2fa">Senha Atual</Label>
                <Input
                  id="senha-2fa"
                  type="password"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  placeholder="Digite sua senha"
                  onKeyDown={(e) => e.key === 'Enter' && handleConfirmToggle2FA()}
                />
              </div>

              <div className="flex gap-3 pt-4">
                <Button
                  onClick={handleConfirmToggle2FA}
                  disabled={loading2FA || !senha}
                  className="flex-1"
                >
                  {loading2FA ? 'Processando...' : 'Confirmar'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowPasswordModal(false);
                    setSenha('');
                  }}
                  disabled={loading2FA}
                  className="flex-1"
                >
                  Cancelar
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Modal de Alterar Senha */}
        {showChangePasswordModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6 space-y-4 shadow-xl">
              <div className="flex items-center gap-2 mb-2">
                <Lock className="w-5 h-5 text-primary" />
                <h3 className="text-xl font-bold">Alterar Senha</h3>
              </div>

              <p className="text-sm text-muted-foreground">
                Para sua segurança, não compartilhe sua senha com ninguém.
              </p>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="senha-atual">Senha Atual</Label>
                  <Input
                    id="senha-atual"
                    type="password"
                    value={senhaAtual}
                    onChange={(e) => setSenhaAtual(e.target.value)}
                    placeholder="Sua senha atual"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="nova-senha">Nova Senha</Label>
                  <Input
                    id="nova-senha"
                    type="password"
                    value={novaSenha}
                    onChange={(e) => setNovaSenha(e.target.value)}
                    placeholder="Mínimo 8 caracteres"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmar-nova-senha">Confirmar Nova Senha</Label>
                  <Input
                    id="confirmar-nova-senha"
                    type="password"
                    value={confirmarNovaSenha}
                    onChange={(e) => setConfirmarNovaSenha(e.target.value)}
                    placeholder="Repita a nova senha"
                    onKeyDown={(e) => e.key === 'Enter' && handleAlterarSenha()}
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <Button
                  onClick={handleAlterarSenha}
                  disabled={loadingSenha || !senhaAtual || !novaSenha || !confirmarNovaSenha}
                  className="flex-1"
                >
                  {loadingSenha ? 'Alterando...' : 'Alterar Senha'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowChangePasswordModal(false);
                    setSenhaAtual('');
                    setNovaSenha('');
                    setConfirmarNovaSenha('');
                  }}
                  disabled={loadingSenha}
                  className="flex-1"
                >
                  Cancelar
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Perfil;
