# Credenciais de Teste - Gestor Cred

Banco em uso: `gestorcred` (recriado via seeder — backup original não estava mais disponível no ambiente)

## Administrador Principal (admin)
- **Email**: diego.haidmann@gmail.com
- **Senha**: muda2025
- **Perfil**: admin

## Admin do Sistema (admin)
- **Email**: admin@gestorcerd.com
- **Senha**: admin123
- **Perfil**: admin

## Usuário Comum (usuario)
- **Email**: usuario@teste.com
- **Senha**: senha123
- **Perfil**: usuario

## Endpoint de Login
`POST /api/auth/login`
Body JSON: `{"email": "...", "senha": "..."}` (o campo é `senha`, não `password`)

Login validado via API (curl) — retorna `access_token` + `refresh_token`.
