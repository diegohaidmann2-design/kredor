import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import Header from '../components/Header';
import { useAuth } from '../context/AuthContext';
import { useModal } from '../components/Modal';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { User, Mail, Calendar, CreditCard, Shield, Lock } from 'lucide-react';
import { formatarData } from '../utils/formatters';
import { authAPI } from '../api/api';
import { toast } from '../hooks/use-toast';

const Perfil = () => {
  const { user, refreshUser } = useAuth();
  const modal = useModal();
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState('');

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

  const handleSalvar = async () => {
    // TODO: Implementar atualização de perfil
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

  if (!user) return null;

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
                <input
                  type="text"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  className="w-full px-3 py-2 border border-border rounded-lg bg-background"
                />
              ) : (
                <p className="text-lg font-medium">{user.nome}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                <Mail className="w-4 h-4 inline mr-2" />
                Email
              </label>
              <p className="text-lg">{user.email}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                <Calendar className="w-4 h-4 inline mr-2" />
                Membro desde
              </label>
              <p className="text-lg">{formatarData(user.created_at)}</p>
            </div>

            {editando ? (
              <div className="flex gap-3 pt-4">
                <Button onClick={handleSalvar}>Salvar</Button>
                <Button variant="outline" onClick={() => setEditando(false)}>
                  Cancelar
                </Button>
              </div>
            ) : (
              <Button onClick={() => setEditando(true)}>
                Editar Perfil
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Plano e Assinatura */}
        <Card>
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
              onClick={() => window.location.href = '/assinatura'}
              className="mt-4"
            >
              Gerenciar Assinatura
            </Button>
          </CardContent>
        </Card>

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
              <Button variant="outline" onClick={() => setShowChangePasswordModal(true)}>
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
