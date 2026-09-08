# Credenciais de Teste — GestorCred

## Usuário Admin (dono dos dados restaurados, inclui HUDSON e RODRIGO)
- Email: diego.haidmann@gmail.com
- Senha: Teste@2026
- Perfil: admin

Observação: senha redefinida para testes (o backup de produção tinha senha desconhecida).
Login endpoint: POST /api/auth/login  body: {"email","senha","turnstile_token"}
Turnstile em modo teste (site key 1x0000...AA sempre passa).
