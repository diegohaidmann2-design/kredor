# Plano de Profissionalização e Centralização de Configurações

Este plano visa remover todas as URLs e domínios fixos (hardcoded) do código-fonte, garantindo que o sistema seja configurável inteiramente através de variáveis de ambiente (.env), seguindo as melhores práticas de mercado (12-Factor App).

## 1. Centralização no Frontend
*   **Nova Configuração**: Criar um arquivo `src/config/env.js` que servirá como a única fonte de verdade para o Frontend.
*   **Runtime Config**: Garantir que o sistema leia de `window._env_` (injetado pelo Docker em tempo de execução) ou `process.env` (tempo de build), sem fallbacks de texto fixo no código.
*   **Refatoração**: Substituir todas as importações e usos esparsos de URLs pela referência a este novo arquivo de configuração.

## 2. Padronização no Backend
*   **Configuração de CORS**: No arquivo `backend/config.py`, adicionaremos a variável `CORS_ORIGINS`, que lerá uma lista de domínios permitidos da ENV.
*   **Segurança**: No `backend/main.py`, substituiremos o `allow_origins=["*"]` pela variável configurada, restringindo o acesso apenas aos domínios do seu projeto em produção.
*   **URLs Dinâmicas**: Garantir que links gerados pelo backend (como para e-mails ou gateways) usem uma `BASE_URL` definida na ENV.

## 3. Configuração via Docker (Single Source of Truth)
*   **Docker Compose**: Centralizar no `docker-compose.yml` a definição de:
    *   `REACT_APP_BACKEND_URL`: Para o frontend saber onde está a API.
    *   `CORS_ORIGINS`: Para o backend saber quem pode acessá-lo.
*   **Ambiente Local vs Produção**: Facilitar a troca entre ambientes mudando apenas o arquivo `.env` da máquina.

## 4. Auditoria e Limpeza
*   **Busca Global**: Executar uma varredura (grep) em todo o repositório para garantir que nenhum `localhost`, `127.0.0.1` ou domínio `.cloud` tenha ficado esquecido dentro de arquivos `.js`, `.py` ou `.html`.
*   **Verificação de Cache**: Garantir que o `env-config.js` seja servido com headers de `no-cache` para evitar que o navegador use configurações antigas após uma mudança na ENV.

## Meta
Ao final deste plano, você poderá mudar o domínio do sistema inteiro (Frontend e Backend) alterando **apenas as variáveis de ambiente no seu servidor**, sem precisar editar uma única linha de código.

**Posso prosseguir com a implementação desta estrutura profissional?**