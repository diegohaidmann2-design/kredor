// Configuração de ambiente para runtime.
//
// IMPORTANTE: NÃO fixe uma URL aqui. Em produção o docker-entrypoint.sh regenera
// este arquivo a partir da variável REACT_APP_BACKEND_URL do container.
//
// Valor vazio é o padrão seguro: config/env.js cai para process.env (build/.env)
// e, na ausência dele, para window.location.origin (mesma origem que serve o app).
// Assim nunca apontamos para o domínio de outro ambiente por engano.
window._env_ = {
  REACT_APP_BACKEND_URL: ''
};
