# GestorCred — PRD / Estado do Projeto

## Problema original
Importar projeto existente (GestorCred — gestão de empréstimos e cobrança PIX/WhatsApp),
subir todos os serviços via iniciar.sh e restaurar o banco de dados anexado.

## Arquitetura
- Backend: FastAPI (`/app/backend`, entrypoint `server.py` -> `main.py`), rotas em `/app/backend/routes`
- Frontend: React (`/app/frontend`)
- Banco: MongoDB local, DB `gestorcred`
- Scheduler habilitado (RUN_SCHEDULER=true)

## Feito (2026-09-08)
- Criados `backend/.env` e `frontend/.env` conforme env fornecido pelo usuário.
  - APP_URL e REACT_APP_BACKEND_URL preenchidos com a URL de preview do ambiente.
- Restaurado dump MongoDB do backup `backup-20260905-155351` no DB `gestorcred`
  (897 documentos, 0 falhas). Coleções: usuarios(5), clientes(44), emprestimos(86), etc.
- Instaladas dependências Python faltantes (bleach + requirements.txt).
- Serviços rodando: mongodb, backend (HTTP 200 em /api/), frontend (landing carrega).

## Observações
- Usuários vieram do backup de produção (campo `senha_hash`, `perfil`, `plano`). As senhas
  são as originais do backup — desconhecidas por nós. Se houver problema de login, resetar senha.

## Backlog / Próximos
- P2: Resetar senha de admin caso necessário.
