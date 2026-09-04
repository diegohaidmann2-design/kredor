# Credenciais de Teste - GestorCred

Banco em uso: `gestorcred` — **RESTAURADO do backup real** `backup-20260902-182538`
(8459 documentos: 4 usuários, 43 clientes, 81 empréstimos, 307 parcelas, 195 pagamentos).

## Administrador Principal (admin) — senha REDEFINIDA nesta restauração
- **Email**: diego.haidmann@gmail.com
- **Senha**: Admin@2026
- **Perfil**: admin / plano enterprise
- Observação: a senha original do backup era desconhecida (dados reais). Redefinida para `Admin@2026` via `scripts/seed_admin.py`.

## Outros usuários no banco (senhas originais do backup / desconhecidas)
- adilsonsoares203@gmail.com (usuario, enterprise)
- rogeriomoura504@gmail.com (usuario, profissional)
- fredrichuriel@gmail.com (usuario, trial)

## Endpoint de Login
`POST /api/auth/login`
Body JSON: `{"email": "...", "senha": "..."}` (o campo é `senha`, não `password`)
Login validado via API — retorna `access_token` + `refresh_token`.

## Utilitários
- Recriar/resetar senha do admin: `cd /app/backend && python scripts/seed_admin.py`
- Restaurar backup mongodump: `mongorestore --uri="mongodb://localhost:27017" --db=gestorcred <pasta>/gestorcred`
