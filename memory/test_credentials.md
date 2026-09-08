# Test Credentials — GestorCred

## Admin / Conta A (perfil=admin, plano=enterprise, owner independente)
- Email: diego.haidmann@gmail.com
- Senha: Teste@2026

## Conta B (perfil=usuario, owner independente — para testar isolamento entre contas)
- Email: adilsonsoares203@gmail.com
- Senha: Teste@2026

Notes:
- Login: POST /api/auth/login  body: {"email","senha","turnstile_token"}. Turnstile é chave de teste Cloudflare (1x0000...) que aceita qualquer token.
- Senhas definidas via reset (bcrypt) para testes. Campo no Mongo: usuarios.senha_hash
- Templates WhatsApp são escopados por get_user_context (dono da conta): isolados entre contas; compartilhados dentro de uma equipe (owner + funcionários).
