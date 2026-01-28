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
      // A rota original era /api/auth/reenviar-verificacao
      // Vamos assumir que existe no authAPI ou fazer chamada direta via axios se não existir
      // Verificando api.js, não existe 'reenviarVerificacao' explicitamente, mas podemos adicionar ou usar axios direto
      // Para manter consistência, vamos adicionar ao api.js se possível, mas aqui vamos usar a estrutura segura
      
      // Como não vi no api.js, vou adicionar lá primeiro, mas por enquanto vou deixar comentado como fazer
      // await authAPI.reenviarVerificacao();
      
      // Fallback seguro usando fetch com URL correta
      const token = localStorage.getItem('token');
      const BACKEND_URL = (window._env_ && window._env_.REACT_APP_BACKEND_URL) || 
                          process.env.REACT_APP_BACKEND_URL || 
                          'http://localhost:8001';
                          
      const response = await fetch(
        `${BACKEND_URL}/api/auth/reenviar-verificacao`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Erro ao reenviar email');
      }
    } catch (err) {
      console.error('Erro ao reenviar email:', err);
      throw err;
    }
  };

  if (loading || !statusAssinatura) {
    return children;
  }

  // Admins e Superadmins não precisam verificar email
  const isAdmin = user?.perfil === 'admin' || user?.perfil === 'superadmin';
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
