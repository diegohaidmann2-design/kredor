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

// URL do backend. Se não houver valor explícito (env-config.js/.env), usa a MESMA origem
// que serve o frontend (window.location.origin).
const _explicitBackendUrl = getEnv("REACT_APP_BACKEND_URL");
export const BACKEND_URL =
  _explicitBackendUrl ||
  (typeof window !== "undefined" && window.location ? window.location.origin : "");
export const APP_NAME = getEnv("REACT_APP_NAME", "Kredor");

const config = {
  BACKEND_URL,
  APP_NAME,
};

export default config;
