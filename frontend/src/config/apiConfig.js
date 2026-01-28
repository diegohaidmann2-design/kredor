// src/config/apiConfig.js
const BACKEND_URL =
    process.env.REACT_APP_BACKEND_URL ||
    (window._env_ && window._env_.REACT_APP_BACKEND_URL) ||
    'http://backend:8001';
export default BACKEND_URL;
