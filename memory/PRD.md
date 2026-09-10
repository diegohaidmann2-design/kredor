# GestorCred / Kredor — PRD

## Problema / Objetivo
Projeto importado (SaaS de gestão de empréstimos e cobrança automática via PIX/WhatsApp).
Pedido do usuário: rodar `iniciar.sh`, colocar tudo no ar e importar o banco anexado.

## Arquitetura
- Backend: FastAPI (`/app/backend`, entrada `server.py` -> `main.py`), scheduler APScheduler (RUN_SCHEDULER=true).
- Frontend: React (`/app/frontend`).
- DB: MongoDB local (`gestorcred`).
- Integrações no código: Stripe, MercadoPago, SyncPay (PIX), LosDados, SMTP, Turnstile, Evolution API (WhatsApp), Emergent LLM.

## O que foi feito (2026-09-10)
- Criados `backend/.env` e `frontend/.env` com as variáveis fornecidas pelo usuário.
  - `REACT_APP_BACKEND_URL` e `APP_URL` preenchidos com a URL pública do preview (não podem ficar vazios neste ambiente).
- Instaladas dependências do backend (requirements.txt); node_modules já presente.
- Serviços no ar via supervisor: backend (200), frontend (200), mongodb, scheduler (16 jobs).
- Corrigidos 14 erros de lint (imports duplicados F811) em auth.py, emprestimos.py, parcelas.py, whatsapp.py, superadmin.py.
- Banco importado de `backup-20260910-121145.tar.gz` (mongodump) via `mongorestore --drop`:
  8862 documentos. Coleções principais: usuarios(8), clientes(47), emprestimos(91),
  parcelas(346), pagamentos(211), carteiras(3).

## Observações
- Senhas dos usuários vêm do dump (bcrypt) — não conhecidas. Ver `memory/test_credentials.md`.
- `FIELD_ENCRYPTION_KEY` fornecida pelo usuário deve corresponder à do dump para decriptar campos sensíveis (ex.: CPF).

## Correção pós-import (2026-09-10)
- Bug: GET /api/emprestimos retornava 500 (`KeyError: valor_principal_centavos`) porque o backup
  usava schema antigo (reais: `valor_principal`) e o código espera `*_centavos`.
- Fix: executado `backend/scripts/migrar_para_centavos.py` — 91 empréstimos, 346 parcelas, 211 pagamentos
  convertidos. 0 empréstimos restantes sem `valor_principal_centavos`.
- Verificado pelo testing_agent: 13/13 backend testes OK (login, listagem, sem_prazo, /abertos/resumo,
  parcelas/pendentes, pagamentos, dashboard) — 100%.
- Atenção: senha de `diego.haidmann@gmail.com` foi redefinida para `Teste@2026` durante o teste
  (o hash original não pôde ser restaurado). Trocar em produção.

## Correção parcela paga aparecendo como atrasada (2026-09-10)
- Bug: na tela /pagamentos, parcela totalmente paga (valor_pago >= valor_total) aparecia como
  "R$ 0,00 ATRASADO". Causa: dados com status inconsistente + `_calcular_valores` só ignorava
  parcelas com status=="pago".
- Fix em `services/juros_mora_service.py`: guard em `_calcular_valores` (vp>=vt>0 => sem atraso/mora)
  e auto-heal em `atualizar_todas_parcelas_atrasadas` (status -> "pago"). Heal one-time no banco (2 parcelas).
- Bugs latentes corrigidos em `routes/parcelas.py`: recursão em `GET /parcelas/resumo-juros-mora`
  (função chamava a si mesma; agora usa alias do service) e handler DELETE duplicado removido.
- Verificado pelo testing_agent: 10/10 backend OK (100%).

## Atalho "Receber Pagamento" no menu do empréstimo (2026-09-10)
- Adicionado item "Receber Pagamento" no menu "..." da tela Empréstimos (frontend/src/pages/Emprestimos.js),
  visível para empréstimos ativos/inadimplentes (todos os tipos), oculto em quitados.
- Abre modal que lista parcelas em aberto, pré-preenche o saldo e permite registrar pagamento
  total OU parcial (reusa POST /api/pagamentos). Parcial => parcela vira "parcial" e mostra saldo restante.
- Decisão do usuário: registro parcial SIMPLES (mantém total/juros). Obs: em empréstimos inadimplentes
  o saldo pode variar levemente pois multa/mora são recalculadas após o pagamento.
- Verificado pelo testing_agent (frontend): 6/6 cenários OK (100%).

## Backlog / Próximos passos
- Validar login com uma conta real (senha do usuário) e navegar pelo dashboard.
- Configurar SMTP e webhooks de pagamento (Stripe/MercadoPago/SyncPay) se for para produção.
