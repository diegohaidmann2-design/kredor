import React, { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import { authAPI } from '../api/api';

const AuthContext = createContext();

// Motivo do logout, lido e apagado pela tela de login. Sobrevive ao redirecionamento.
export const MOTIVO_LOGOUT_KEY = 'motivo_logout';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [recursos, setRecursos] = useState(null); // limites/recursos efetivos do plano
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const idleLogoutTimerRef = useRef(null);
  const tokenExpiryTimerRef = useRef(null);
  const lastActivityWriteAtRef = useRef(0);

  const IDLE_TIMEOUT_MS = (() => {
    const minutes = Number(process.env.REACT_APP_IDLE_TIMEOUT_MINUTES);
    if (Number.isFinite(minutes) && minutes > 0) return minutes * 60 * 1000;
    return 30 * 60 * 1000;
  })();
  const ACTIVITY_THROTTLE_MS = 15 * 1000;
  const ACTIVITY_KEY = 'last_activity_at';

  const parseJwtExpMs = useCallback((jwt) => {
    if (!jwt || typeof jwt !== 'string') return null;
    const parts = jwt.split('.');
    if (parts.length !== 3) return null;
    try {
      const payloadJson = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
      const payload = JSON.parse(payloadJson);
      const expSeconds = Number(payload?.exp);
      if (!Number.isFinite(expSeconds) || expSeconds <= 0) return null;
      return expSeconds * 1000;
    } catch {
      return null;
    }
  }, []);

  const clearSessionTimers = useCallback(() => {
    if (idleLogoutTimerRef.current) {
      clearTimeout(idleLogoutTimerRef.current);
      idleLogoutTimerRef.current = null;
    }
    if (tokenExpiryTimerRef.current) {
      clearTimeout(tokenExpiryTimerRef.current);
      tokenExpiryTimerRef.current = null;
    }
  }, []);

  // `motivo` sobrevive ao redirecionamento para a tela de login, que o exibe e apaga. Sem isso,
  // quem é derrubado por um acesso em outro dispositivo cai no login sem saber por quê.
  const logout = useCallback((motivo = null) => {
    clearSessionTimers();
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem(ACTIVITY_KEY);
    try {
      if (motivo) localStorage.setItem(MOTIVO_LOGOUT_KEY, motivo);
      else localStorage.removeItem(MOTIVO_LOGOUT_KEY);
    } catch (e) {
      // silencioso: armazenamento indisponível (aba privada) não impede o logout.
    }
    setToken(null);
    setUser(null);
  }, [clearSessionTimers]);

  const touchActivity = useCallback(() => {
    const now = Date.now();
    if (now - lastActivityWriteAtRef.current < ACTIVITY_THROTTLE_MS) return;
    lastActivityWriteAtRef.current = now;
    localStorage.setItem(ACTIVITY_KEY, String(now));
  }, []);

  const scheduleIdleLogout = useCallback(() => {
    if (!token) return;

    const arm = (lastActivityAt) => {
      const msUntilLogout = IDLE_TIMEOUT_MS - (Date.now() - lastActivityAt);
      if (msUntilLogout <= 0) {
        logout();
        return;
      }

      if (idleLogoutTimerRef.current) clearTimeout(idleLogoutTimerRef.current);
      idleLogoutTimerRef.current = setTimeout(() => {
        const rawAgain = localStorage.getItem(ACTIVITY_KEY);
        const lastAgain = rawAgain ? Number(rawAgain) : NaN;
        const lastAt = Number.isFinite(lastAgain) && lastAgain > 0 ? lastAgain : 0;
        if (!lastAt) {
          logout();
          return;
        }
        const inactiveFor = Date.now() - lastAt;
        if (inactiveFor >= IDLE_TIMEOUT_MS) {
          logout();
          return;
        }
        arm(lastAt);
      }, Math.min(msUntilLogout, 60 * 1000));
    };

    const raw = localStorage.getItem(ACTIVITY_KEY);
    const last = raw ? Number(raw) : NaN;
    const lastActivityAt = Number.isFinite(last) && last > 0 ? last : Date.now();
    if (!raw) localStorage.setItem(ACTIVITY_KEY, String(lastActivityAt));

    arm(lastActivityAt);
  }, [IDLE_TIMEOUT_MS, logout, token]);

  const scheduleTokenExpiryLogout = useCallback(() => {
    if (!token) return;
    const expMs = parseJwtExpMs(token);
    if (!expMs) return;
    const msUntilExpiry = expMs - Date.now();
    if (msUntilExpiry <= 0) {
      logout();
      return;
    }
    if (tokenExpiryTimerRef.current) clearTimeout(tokenExpiryTimerRef.current);
    tokenExpiryTimerRef.current = setTimeout(() => {
      logout();
    }, Math.max(0, msUntilExpiry - 10 * 1000));
  }, [logout, parseJwtExpMs, token]);

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
      const detalhe = error.response?.data?.detail;
      logout(typeof detalhe === 'string' && detalhe.includes('outro dispositivo') ? detalhe : null);
      return false;
    }
  }, [logout]);

  const loadUser = useCallback(async () => {
    try {
      const response = await authAPI.getMe();
      setUser(response.data);
    } catch (error) {
      console.error('Erro ao carregar usuário:', error);
      const detalhe = error.response?.data?.detail;
      // Conta assumida em outro dispositivo: renovar não resolve (o refresh também é recusado),
      // e o usuário precisa ler o motivo.
      if (error.response?.status === 401 && typeof detalhe === 'string' && detalhe.includes('outro dispositivo')) {
        logout(detalhe);
        return;
      }
      // Tentar renovar token antes de fazer logout
      const renovado = await renovarToken();
      if (!renovado) {
        logout();
      }
    } finally {
      setLoading(false);
    }
  }, [logout, renovarToken]);

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

  useEffect(() => {
    if (!token) {
      clearSessionTimers();
      return;
    }

    const activityEvents = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'pointerdown'];
    const handleActivity = () => {
      touchActivity();
      scheduleIdleLogout();
    };
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        touchActivity();
        scheduleIdleLogout();
      }
    };
    const handleFocus = () => {
      touchActivity();
      scheduleIdleLogout();
    };
    const handleStorage = (e) => {
      if (e.key === ACTIVITY_KEY) scheduleIdleLogout();
      if (e.key === 'token') scheduleTokenExpiryLogout();
    };

    touchActivity();
    scheduleIdleLogout();
    scheduleTokenExpiryLogout();

    activityEvents.forEach((ev) => window.addEventListener(ev, handleActivity, { passive: true }));
    document.addEventListener('visibilitychange', handleVisibility);
    window.addEventListener('focus', handleFocus);
    window.addEventListener('storage', handleStorage);

    return () => {
      activityEvents.forEach((ev) => window.removeEventListener(ev, handleActivity));
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('storage', handleStorage);
      clearSessionTimers();
    };
  }, [ACTIVITY_KEY, clearSessionTimers, scheduleIdleLogout, scheduleTokenExpiryLogout, token, touchActivity]);

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

  const login = async (email, senha, turnstileToken) => {
    try {
      const response = await authAPI.login({ email, senha, turnstile_token: turnstileToken });
      
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

  // Função para forçar atualização do token (útil após checkout)
  const updateToken = useCallback((newToken) => {
    if (newToken) {
      localStorage.setItem('token', newToken);
      setToken(newToken);
    }
  }, []);

  // Busca os recursos/limites efetivos do plano sempre que o usuário muda.
  // Autoridade é o backend (/auth/meus-recursos); a UI só usa para ocultar selos.
  useEffect(() => {
    let cancelado = false;
    if (!user) {
      setRecursos(null);
      return;
    }
    authAPI.meusRecursos()
      .then((res) => { if (!cancelado) setRecursos(res.data); })
      .catch(() => { if (!cancelado) setRecursos(null); });
    return () => { cancelado = true; };
  }, [user]);

  return (
    <AuthContext.Provider value={{ 
      user, 
      setUser, // Exportar setUser para uso na verificação 2FA
      recursos,
      token,
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
