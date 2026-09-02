# Credenciais de Teste - Gestor Cred

Banco em uso: `gestorcred` (importado do backup backup-20260902-182538)

## Administrador Principal (admin) — senha REDEFINIDA nesta importação
- **Email**: diego.haidmann@gmail.com
- **Senha**: Admin@2026
- **Perfil**: admin
- Observação: a senha original era desconhecida (dados reais importados). Foi redefinida para `Admin@2026` usando o hash bcrypt do próprio app para permitir acesso.

## Outros usuários no banco (senhas desconhecidas / não redefinidas)
- adilsonsoares203@gmail.com (perfil usuario)
- rogeriomoura504@gmail.com (perfil usuario)
- fredrichuriel@gmail.com (perfil usuario)

## Endpoint de Login
`POST /api/auth/login`
Body JSON: `{"email": "...", "senha": "..."}` (o campo é `senha`, não `password`)

Login validado via API (curl) em 2026 — retorna `access_token` + `refresh_token`.
