import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import BannerEmailNaoVerificado from './BannerEmailNaoVerificado';
import BannerTrialExpirando from './BannerTrialExpirando';
import { assinaturasAPI, authAPI } from '../api/api';

const AssinaturaWrapper = ({ children }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [statusAssinatura, setStatusAssinatura] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      carregarStatusAssinatura();
    }
  }, [user]);

  const carregarStatusAssinatura = async () => {
    try {
      // Usar a API centralizada
      const response = await assinaturasAPI.obterMinha();

      // Se a resposta for válida e tiver dados
      if (response && response.data) {
        setStatusAssinatura(response.data);
      }
    } catch (err) {
      // silencioso: verificação de assinatura em segundo plano; o 402 já redireciona e outras falhas não devem interromper o uso
      console.error('Erro ao carregar status:', err);
      
      // Tratamento específico para 402 (Pagamento necessário)
      if (err.response && err.response.status === 402) {
        const data = err.response.data;
        if (data.detail?.tipo === 'trial_expirado' || data.detail?.tipo === 'assinatura_vencida') {
          navigate('/assinatura-expirada');
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleReenviarEmail = async () => {
    try {
      if (!user?.email) {
        throw new Error('Email do usuário não encontrado');
      }
      
      await authAPI.reenviarVerificacao(user.email);
    } catch (err) {
      // silencioso: re-lança o erro para quem chamou exibir o retorno ao usuário
      console.error('Erro ao reenviar email:', err);
      throw err;
    }
  };

  if (loading || !statusAssinatura) {
    return children;
  }

  // Admins e Superadmins não precisam verificar email
  const isAdmin = user?.perfil === 'admin';
  const deveVerificarEmail = !isAdmin && !statusAssinatura.email_verificado;

  return (
    <>
      {/* Banner de email não verificado */}
      {deveVerificarEmail && (
        <BannerEmailNaoVerificado onReenviar={handleReenviarEmail} />
      )}

      {/* Banner de trial expirando */}
      {statusAssinatura.tipo === 'trial' && 
       statusAssinatura.expirando && 
       !statusAssinatura.expirado &&
       statusAssinatura.email_verificado && (
        <BannerTrialExpirando diasRestantes={statusAssinatura.dias_restantes} />
      )}

      {/* Conteúdo da página */}
      {children}
    </>
  );
};

export default AssinaturaWrapper;
