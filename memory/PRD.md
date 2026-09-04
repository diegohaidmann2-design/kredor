# GestorCred — PRD / Estado do Projeto

## Problem Statement (original)
"importei um projeto, rode o iniciar.sh e coloque tudo no ar e importe o banco anexado"

## Descrição
Sistema de Gestão de Empréstimos a Juros (SaaS multi-tenant). Backend FastAPI + MongoDB, Frontend React (CRACO). Inclui empréstimos, parcelas, pagamentos, clientes, score, cobrança WhatsApp, portal do cliente, assinaturas/checkout (Stripe/Asaas/MercadoPago), auditoria, 2FA, scheduler de jobs.

## Arquitetura
- Backend: `/app/backend` (uvicorn `server:app`, porta 8001, prefixo `/api`)
- Frontend: `/app/frontend` (porta 3000)
- DB: MongoDB local, `DB_NAME=gestorcred`
- Config em `backend/config.py` via `.env`

## Estado atual (2026-09-04)
- ✅ `.env` de backend e frontend criados (valores fornecidos pelo usuário).
- ✅ Banco importado do backup `backup-20260902-182538` → `gestorcred` (8459 documentos; 4 usuários, 43 clientes, 81 empréstimos).
- ✅ Serviços rodando via supervisor (mongodb, backend, frontend).
- ✅ Health-check OK: `/api/` retorna 200 (local e URL pública); login valida credenciais (401 p/ senha errada).
- ✅ Landing page renderiza corretamente na URL pública.

## Integrações
- EMERGENT_LLM_KEY configurada (assistente IA).
- LOSDADOS API configurada (consulta de dados).
- STRIPE em modo teste (`sk_test_emergent`); webhooks/SMTP/WhatsApp sem chaves reais (desativados).

## Backlog / Próximos passos
- Configurar chaves reais de pagamento/SMTP/WhatsApp quando for para produção.
- Deploy definitivo (Deploy da Emergent) quando o usuário desejar.

## Feature: Consultas CNPJ e Telefone (2026-09-04)
- Backend `services/losdados_service.py`: refatorado com helper `_consulta_get`; adicionadas `validar_cnpj`, `validar_telefone`, `consultar_cnpj`, `consultar_telefone`.
- Rotas `routes/consultas.py`: novos endpoints `POST /api/consultas/cnpj` e `POST /api/consultas/telefone` (salvam no histórico); `obter` agora retorna `documento`.
- PDF `services/consulta_pdf.py`: cabeçalho adapta por tipo (cpf/cnpj/telefone).
- Frontend `pages/Consultas.js`: módulos CNPJ e Telefone ativados; `CompanyHero` (dossiê da empresa) e lista de pessoas do telefone com botão "Consultar CPF"; histórico filtra por módulo.
- Verificado e2e: CNPJ (Banco do Brasil), Telefone (61 pessoas), PDF gerado p/ ambos, histórico e validações.

## Feature: Consulta por Nome (2026-09-04)
- Backend: `validar_nome`/`consultar_nome` (endpoint LosDados `/consulta/nome2`); rota `POST /api/consultas/nome` (tipo `nome`, salva no histórico).
- Frontend: módulo Nome ativado (input de texto), lista de pessoas encontradas com CPF, nascimento, sexo, local, nome da mãe, badge de situação cadastral e botão "Consultar CPF completo".
- Verificado e2e: busca "MARIA SILVA" → 300 resultados; validação de nome curto (400).

