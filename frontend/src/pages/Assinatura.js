import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import Loading from '../components/Loading';
import { useAuth } from '../context/AuthContext';
import { useModal } from '../components/Modal';
import { assinaturasAPI } from '../api/api';
import { formatarMoeda, formatarData } from '../utils/formatters';

const Assinatura = () => {
  const { user } = useAuth();
  const isMember = !!user?.owner_id;

  const [assinatura, setAssinatura] = useState(null);
  const [planos, setPlanos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [error, setError] = useState('');
  const modal = useModal();



  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = async () => {
    try {
      setLoading(true);

      // Carregar assinatura atual E planos do banco
      const [assinaturaResponse, planosResponse] = await Promise.all([
        assinaturasAPI.obter(),
        assinaturasAPI.listarPlanos()
      ]);

      setAssinatura(assinaturaResponse.data);
      setPlanos(planosResponse.data.filter(p => p.id !== 'trial')); // Remover trial da lista

    } catch (err) {
      console.error('Erro ao carregar dados:', err);
    } finally {
      setLoading(false);
    }
  };

  const carregarAssinatura = async () => {
    try {
      setLoading(true);
      const response = await assinaturasAPI.obter();
      setAssinatura(response.data);
    } catch (err) {
      console.error('Erro ao carregar assinatura:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAssinar = async (planoId) => {
    try {
      setProcessando(true);
      setError('');

      // Redirecionar diretamente para o checkout transparente
      // O usuário já está logado, então vai poder escolher PIX ou Cartão
      window.location.href = `/checkout-transparente/${planoId}?upgrade=true`;

    } catch (err) {
      console.error('Erro ao iniciar checkout:', err);
      setError('Erro ao processar. Tente novamente.');
    } finally {
      setProcessando(false);
    }
  };

  const handleCancelar = () => {
    modal.confirm(
      'Cancelar Assinatura',
      'Tem certeza que deseja cancelar sua assinatura? Você será rebaixado para o plano Trial.',
      async () => {
        try {
          setProcessando(true);
          setError('');
          await assinaturasAPI.cancelar();
          modal.success('Assinatura Cancelada', 'Sua assinatura foi cancelada com sucesso.');
          carregarAssinatura();
        } catch (err) {
          console.error('Erro ao cancelar:', err);
          modal.error('Erro', 'Não foi possível cancelar sua assinatura. Tente novamente.');
        } finally {
          setProcessando(false);
        }
      }
    );
  };

  if (loading) return <Loading message="Carregando informações..." />;

  const planoAtual = assinatura?.plano || 'trial';
  const diasRestantes = assinatura?.dias_restantes_trial || 0;
  const statusAtivo = assinatura?.status === 'ativo' || assinatura?.status === 'ativa' || assinatura?.plano_ativo;

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground" data-testid="assinatura-title">
            Assinatura
          </h1>
          <p className="text-muted-foreground mt-1">Gerencie seu plano e pagamentos</p>
        </div>

        {isMember && (
          <div className="mb-6 bg-blue-500/10 border border-blue-500/30 text-blue-400 px-4 py-3 rounded-lg flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Seu plano é gerenciado pelo administrador da conta. Você não pode alterar assinaturas.</span>
          </div>
        )}

        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Status Atual */}
        <div className="bg-card rounded-lg border border-border p-6 mb-8" data-testid="status-assinatura">
          <h2 className="text-xl font-bold text-foreground mb-4">Status da Assinatura</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-muted-foreground">Plano Atual</p>
              <p className="text-2xl font-bold text-foreground capitalize">
                {planoAtual === 'trial' ? 'Período de Avaliação' :
                  planoAtual === 'basico' ? 'Básico' :
                    planoAtual === 'profissional' ? 'Profissional' :
                      planoAtual === 'enterprise' ? 'Enterprise' : planoAtual}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${statusAtivo ? 'bg-emerald-500/20 text-emerald-400' :
                assinatura?.status === 'trial' ? 'bg-blue-500/20 text-blue-400' :
                  'bg-slate-500/20 text-slate-400'
                }`}>
                {statusAtivo ? 'Ativo' :
                  assinatura?.status === 'trial' ? `Trial (${diasRestantes} dias)` :
                    'Inativo'}
              </span>
            </div>
            {(assinatura?.data_fim || assinatura?.data_expiracao) && statusAtivo && (
              <div>
                <p className="text-sm text-muted-foreground">Válido até</p>
                <p className="text-lg font-semibold text-foreground">
                  {formatarData(assinatura.data_fim || assinatura.data_expiracao)}
                </p>
              </div>
            )}
          </div>


          {statusAtivo && planoAtual !== 'trial' && !isMember && (
            <div className="mt-6 pt-6 border-t border-border">
              <Button
                onClick={handleCancelar}
                variant="secondary"
                disabled={processando}
                testId="cancelar-assinatura-button"
              >
                Cancelar Assinatura
              </Button>
            </div>
          )}
        </div>

        {/* Planos */}
        <h2 className="text-2xl font-bold text-foreground mb-6">
          {planoAtual === 'trial' ? 'Escolha seu Plano' : 'Alterar Plano'}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {planos.map((plano) => (
            <div
              key={plano.id}
              className={`bg-card rounded-lg border-2 p-6 relative ${plano.popular ? 'border-purple-500' : 'border-border'
                } ${planoAtual === plano.id ? 'ring-2 ring-primary' : ''}`}
              data-testid={`plano-${plano.id}`}
            >
              {plano.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-purple-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                    MAIS POPULAR
                  </span>
                </div>
              )}

              {planoAtual === plano.id && (
                <div className="absolute -top-3 right-4">
                  <span className="bg-emerald-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                    ATUAL
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-xl font-bold text-foreground mb-2">{plano.nome}</h3>
                <p className="text-muted-foreground text-sm mb-4">{plano.descricao}</p>
                <div className="flex items-baseline justify-center">
                  <span className="text-4xl font-bold text-foreground">
                    {formatarMoeda(plano.preco)}
                  </span>
                  <span className="text-muted-foreground ml-1">/mês</span>
                </div>
              </div>

              <ul className="space-y-3 mb-6">
                {plano.recursos.map((recurso, i) => (
                  <li key={i} className="flex items-center text-sm text-foreground">
                    <svg className={`w-5 h-5 mr-2 ${plano.cor === 'blue' ? 'text-blue-500' :
                      plano.cor === 'purple' ? 'text-purple-500' :
                        'text-amber-500'
                      }`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    {recurso}
                  </li>
                ))}
              </ul>



              {!isMember && (
                <Button
                  onClick={() => handleAssinar(plano.id)}
                  variant={plano.popular ? 'primary' : 'secondary'}
                  className="w-full"
                  disabled={processando || planoAtual === plano.id}
                  testId={`assinar-${plano.id}-button`}
                >
                  {planoAtual === plano.id ? 'Plano Atual' :
                    processando ? 'Processando...' :
                      'Assinar'}
                </Button>
              )}
            </div>
          ))}
        </div>

        {/* Info sobre pagamentos */}
        <div className="mt-8 bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
          <h3 className="font-semibold text-blue-400 mb-2 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            Informações sobre pagamento
          </h3>
          <ul className="text-sm text-blue-400/80 space-y-1">
            <li>• Pagamentos processados com segurança via Stripe</li>
            <li>• Renovação automática mensal</li>
            <li>• Cancele a qualquer momento sem multa</li>
            <li>• Garantia de reembolso em 7 dias</li>
          </ul>
        </div>
      </div>
    </Layout >
  );
};

export default Assinatura;
