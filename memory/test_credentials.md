# Credenciais de Teste - Gestor Cred

Banco em uso: `gestorcred` (RESTAURADO do backup backup-20260902-182538 — 8459 documentos: 43 clientes, 81 empréstimos, 307 parcelas, 195 pagamentos, 4 usuários)

## Administrador Principal (admin) — senha REDEFINIDA nesta restauração
- **Email**: diego.haidmann@gmail.com
- **Senha**: Admin@2026
- **Perfil**: admin
- Observação: a senha original era desconhecida (dados reais). Redefinida para `Admin@2026`.

## Outros usuários no banco (senhas originais desconhecidas / não redefinidas)
- adilsonsoares203@gmail.com (perfil usuario)
- rogeriomoura504@gmail.com (perfil usuario)
- fredrichuriel@gmail.com (perfil usuario)

## Endpoint de Login
`POST /api/auth/login`
Body JSON: `{"email": "...", "senha": "..."}` (o campo é `senha`, não `password`)

Login validado via API (curl) — retorna `access_token` + `refresh_token`.
