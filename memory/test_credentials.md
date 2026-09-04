# Credenciais de Teste - GestorCred

Banco em uso: `gestorcred` (recriado neste pod após import — dados originais NÃO vieram junto).
Populado com dados de demonstração (20 clientes, 37 empréstimos, 431 parcelas, 53 pagamentos).

## Administrador Principal (admin)
- **Email**: diego.haidmann@gmail.com
- **Senha**: Admin@2026
- **Perfil**: admin
- **Plano**: enterprise (ativo, e-mail verificado)

## Endpoint de Login
`POST /api/auth/login`
Body JSON: `{"email": "...", "senha": "..."}` (o campo é `senha`, não `password`)
Retorna `access_token` + `refresh_token`. Validado via API (curl) e no frontend.

## Como recriar o admin (idempotente)
`cd /app/backend && python scripts/seed_admin.py`

## Como popular dados de demonstração
`cd /app/backend && DB_NAME=gestorcred python scripts/popular_dados_teste.py`
