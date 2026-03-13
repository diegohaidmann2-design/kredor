import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { authAPI } from '../api/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  // Função para renovar o token usando refresh_token
  const renovarToken = useCallback(async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      return false;
    }
    
    try {
      const response = await authAPI.refresh(refreshToken);
      const { access_token } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      return true;
    } catch (error) {
      console.error('Erro ao renovar token:', error);
      // Se falhar, fazer logout
      logout();
      return false;
    }
  }, []);

  const loadUser = useCallback(async () => {
    try {
      const response = await authAPI.getMe();
      setUser(response.data);
    } catch (error) {
      console.error('Erro ao carregar usuário:', error);
      // Tentar renovar token antes de fazer logout
      const renovado = await renovarToken();
      if (!renovado) {
        logout();
      }
    } finally {
      setLoading(false);
    }
  }, [renovarToken]);

  // Função para recarregar dados do usuário (útil após mudanças no admin)
  const refreshUser = useCallback(async () => {
    if (token) {
      try {
        const response = await authAPI.getMe();
        setUser(response.data);
        return { success: true };
      } catch (error) {
        console.error('Erro ao atualizar usuário:', error);
        // Tentar renovar token
        await renovarToken();
        return { success: false };
      }
    }
    return { success: false };
  }, [token, renovarToken]);

  useEffect(() => {
    if (token) {
      loadUser();
    } else {
      setLoading(false);
    }
  }, [token, loadUser]);

  // Listener para detectar mudanças no localStorage (ex: quando token é salvo no checkout)
  useEffect(() => {
    const handleStorageChange = () => {
      const newToken = localStorage.getItem('token');
      if (newToken && newToken !== token) {
        setToken(newToken);
      }
    };

    // Escutar eventos de storage
    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [token]);

  // Renovar token a cada 7 horas (token expira em 8h)
  useEffect(() => {
    if (token) {
      const interval = setInterval(() => {
        renovarToken();
      }, 7 * 60 * 60 * 1000); // 7 horas
      
      return () => clearInterval(interval);
    }
  }, [token, renovarToken]);

  // Atualizar dados do usuário a cada 5 minutos (para pegar mudanças do admin)
  useEffect(() => {
    if (token) {
      const interval = setInterval(() => {
        refreshUser();
      }, 5 * 60 * 1000); // 5 minutos
      
      return () => clearInterval(interval);
    }
  }, [token, refreshUser]);

  const login = async (email, senha) => {
    try {
      const response = await authAPI.login({ email, senha });
      
      // Verificar se requer 2FA
      if (response.data.requires_2fa) {
        return { 
          success: true, 
          requires_2fa: true, 
          email: response.data.email 
        };
      }
      
      // Login normal (sem 2FA)
      const { access_token, refresh_token, usuario } = response.data;
      
      // Salvar ambos os tokens
      localStorage.setItem('token', access_token);
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token);
      }
      
      setToken(access_token);
      setUser(usuario);
      
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Erro ao fazer login'
      };
    }
  };

  const registro = async (data) => {
    try {
      await authAPI.registro(data);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Erro ao registrar'
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    setToken(null);
    setUser(null);
  };

  // Função para forçar atualização do token (útil após checkout)
  const updateToken = useCallback((newToken) => {
    if (newToken) {
      localStorage.setItem('token', newToken);
      setToken(newToken);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ 
      user, 
      setUser, // Exportar setUser para uso na verificação 2FA
      loading, 
      login, 
      registro, 
      logout, 
      refreshUser,
      updateToken,
      isAuthenticated: !!user 
    }}>
      {children}
    </AuthContext.Provider>
  );
};
