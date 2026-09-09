/**
 * Centralização de variáveis de ambiente do Frontend.
 * Este arquivo lê as variáveis injetadas em tempo de execução pelo Docker (window._env_)
 * ou em tempo de build (process.env).
 */

const getEnv = (key, defaultValue = "") => {
  return (
    (window._env_ && window._env_[key]) || 
    process.env[key] || 
    defaultValue
  );
};

export const BACKEND_URL = getEnv("REACT_APP_BACKEND_URL");
export const APP_NAME = getEnv("REACT_APP_NAME", "Kredor");

// Se a URL do backend não estiver definida, avisar no console em desenvolvimento
if (!BACKEND_URL && process.env.NODE_ENV !== "production") {
  console.warn(
    "⚠️ REACT_APP_BACKEND_URL não definida. As chamadas de API podem falhar."
  );
}

const config = {
  BACKEND_URL,
  APP_NAME,
};

export default config;
