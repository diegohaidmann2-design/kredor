# GestorCred — Sistema de Gestão de Empréstimos a Juros

## Contexto
Projeto importado (existente). FastAPI (backend) + React 19 (frontend) + MongoDB.
Objetivo desta sessão: subir a aplicação no ar e restaurar o banco de dados anexado.

## Estado (2026-09-08)
- `.env` de backend e frontend criados com as variáveis fornecidas pelo usuário.
  - `DB_NAME=gestorcred`, `MONGO_URL=mongodb://localhost:27017`.
  - `REACT_APP_BACKEND_URL` e `APP_URL` apontam para o pod atual: https://cred-system-dev.preview.emergentagent.com (o APP_URL fornecido pelo usuário era de outro pod).
- Banco restaurado a partir de `backup-20260905-155351` via mongorestore (897 documentos, 0 falhas).
  - 5 usuários, 44 clientes, 86 empréstimos, 129 notificações, etc.
- Serviços rodando via supervisor: mongodb, backend (8001), frontend (3000). Backend `/api/` e `/health` respondem 200.
- Scheduler ativo (RUN_SCHEDULER=true), 15 jobs agendados.
- Landing page carrega corretamente.

## Observações
- Senhas dos usuários vêm do backup (hash), desconhecidas. Login requer credenciais originais ou reset.
- Integrações configuradas por env: EMERGENT_LLM_KEY, LosDados, Stripe (test), Turnstile (chave de teste). SMTP vazio (email desativado).

## Backlog / Next
- Validar fluxos de login/dashboard end-to-end com credenciais válidas.
- Configurar SMTP se envio de email for necessário.
- Configurar webhooks/secrets de pagamento (Stripe/MercadoPago) para produção.

## Módulo WhatsApp — análise e correções (2026-09-08)
Integração: Evolution API (não-oficial) em http://207.58.153.83:8080, config em db.configuracoes tipo 'evolution_api'.

### Bugs encontrados e corrigidos
1. numero_telefone ficava null ao conectar — lia de /connectionState (só retorna state). Fix: helper obter_numero_conectado() via /fetchInstances (ownerJid). Conexão atual: 5527999507920.
2. Envio pegava instância ANTIGA deletada (deleted:true) → 404 'instance does not exist'. Fix: filtro deleted:{$ne:True} + ativo em whatsapp_service.py (enviar_mensagem/documento).
3. Horário comercial e dia da semana avaliados em UTC. Fix: _agora_local() converte para America/Sao_Paulo (campo timezone configurável) em whatsapp_anti_spam_service.py.

### Cenários testados (entregues aos números de teste 5527988292633 e 5515953748288)
- Texto direto (service) OK | Texto via API autenticada OK (testing agent, 100%) | PDF/documento OK | Fila/anti-spam OK
- NÃO testável por falta de dados: cobrança-de-parcela e confirmação-de-pagamento (db.parcelas=0, db.pagamentos=0).

### Observações (não bloqueantes)
- POST /whatsapp/mensagens/enviar: campo 'tipo' aceita apenas cobranca|lembrete|confirmacao|manual (usar 'manual' p/ texto livre).
- Envio manual não passa pelo anti-spam (pode burlar horário). api_key da Evolution em texto no banco.
- Emprestimos (86) existem mas parcelas não foram geradas (coleção vazia).

## Atualizações (Jun/2026)
- **Turnstile (fix):** adicionada REACT_APP_TURNSTILE_SITE_KEY no frontend; widget renderiza 1x e faz reset() ao alternar Login/Cadastro. Verificado.
- **Sidebar Admin (fix):** cada página monta seu próprio <Layout>, remontando o Sidebar e resetando scroll/estado. Corrigido persistindo scrollTop (module var + useLayoutEffect em Sidebar.js) e isOpen em localStorage (SidebarContext.js). Item ativo já era baseado na rota (location.pathname). Verificado (scroll mantido em navegações admin).
- **Preview em tempo real (feature):** modal Novo Empréstimo agora tem layout 2 colunas (form + painel EmprestimoPreview.js). O preview reutiliza a MESMA lógica do backend via POST /api/emprestimos/simular (adicionado data_inicio opcional em SimulacaoRequest). Empréstimo aberto usa juros_periodo = principal*(taxa/100), espelhando o backend. Verificado.
- **DB:** restaurado backup 20260905-155351. Admin de teste: diego.haidmann@gmail.com / GestorTest@2026.
