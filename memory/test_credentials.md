# Credenciais de Teste - Gestor Cred

Banco: `gestorcred_dev`

## Administrador Principal (Enterprise)
- **Email**: diego.haidmann@gmail.com
- **Senha**: muda2025
- **Perfil**: admin / plano enterprise (trial 365 dias)

## Administrador do Sistema (Enterprise)
- **Email**: admin@gestorcerd.com
- **Senha**: admin123
- **Perfil**: admin / plano enterprise

## Usuário Comum (Profissional)
- **Email**: usuario@teste.com
- **Senha**: senha123
- **Perfil**: usuario / plano profissional (30 dias)

## Endpoint de Login
`POST /api/auth/login`
Body JSON: `{"email": "...", "senha": "..."}` (note: campo é `senha`, não `password`)

Login validado via API em 09/06/2026 — retornou `access_token` + `refresh_token` corretamente.

## Atualização 10/06/2026
- Banco em uso real por adilsonsoares203@gmail.com (senha desconhecida)
- Senha de diego.haidmann@gmail.com foi ALTERADA pelo usuário (muda2025 não funciona mais)
- usuario@teste.com / senha123 foi RECRIADO (perfil usuario, plano profissional) com dados de teste em /pagamentos
