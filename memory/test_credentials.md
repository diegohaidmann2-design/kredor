# Test Credentials — GestorCred

## Admin (perfil=admin, plano=enterprise)
- Email: diego.haidmann@gmail.com
- Senha: Teste@2026
- Login endpoint: POST /api/auth/login  body: {"email","senha","turnstile_token"}
- Turnstile: usa chave de teste Cloudflare (1x0000...) que sempre passa; qualquer token é aceito.

Notes:
- Senha definida via reset (bcrypt) para testes. Demais usuários do backup têm senha desconhecida.
- Field name para senha no Mongo: usuarios.senha_hash
