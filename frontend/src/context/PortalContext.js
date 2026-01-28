import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const PortalContext = createContext();

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

export const PortalProvider = ({ children }) => {
  const [cliente, setCliente] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('portal_token'));
  const [loading, setLoading] = useState(false);

  // Configurar axios com token
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  const login = async (cpf_cnpj, codigo_acesso) => {
    setLoading(true);
    try {
      const response = await axios.post(`${BACKEND_URL}/api/portal/login`, {
        cpf_cnpj,
        codigo_acesso
      });
      
      const { access_token, cliente: clienteData } = response.data;
      
      setToken(access_token);
      setCliente(clienteData);
      localStorage.setItem('portal_token', access_token);
      localStorage.setItem('portal_cliente', JSON.stringify(clienteData));
      
      return { success: true };
    } catch (error) {
      console.error('Erro no login:', error);
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Erro ao fazer login' 
      };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setCliente(null);
    localStorage.removeItem('portal_token');
    localStorage.removeItem('portal_cliente');
    delete axios.defaults.headers.common['Authorization'];
  };

  const solicitarCodigo = async (cpf_cnpj, email) => {
    setLoading(true);
    try {
      await axios.post(`${BACKEND_URL}/api/portal/solicitar-codigo`, {
        cpf_cnpj,
        email
      });
      return { success: true, message: 'Código enviado para o email!' };
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Erro ao solicitar código' 
      };
    } finally {
      setLoading(false);
    }
  };

  const alterarCodigo = async (codigo_atual, codigo_novo, codigo_novo_confirmacao) => {
    setLoading(true);
    try {
      await axios.put(`${BACKEND_URL}/api/portal/alterar-codigo`, {
        codigo_atual,
        codigo_novo,
        codigo_novo_confirmacao
      });
      return { success: true, message: 'Código alterado com sucesso!' };
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Erro ao alterar código' 
      };
    } finally {
      setLoading(false);
    }
  };

  // Restaurar sessão ao carregar
  useEffect(() => {
    const savedCliente = localStorage.getItem('portal_cliente');
    if (savedCliente && token) {
      setCliente(JSON.parse(savedCliente));
    }
  }, [token]);

  const value = {
    cliente,
    token,
    loading,
    isAuthenticated: !!token,
    login,
    logout,
    solicitarCodigo,
    alterarCodigo
  };

  return <PortalContext.Provider value={value}>{children}</PortalContext.Provider>;
};

export const usePortal = () => {
  const context = useContext(PortalContext);
  if (!context) {
    throw new Error('usePortal must be used within a PortalProvider');
  }
  return context;
};
