# Credenciais de Teste — Kredor

## Estado atual (backup-20260909-195922 restaurado em 2026-09-09)
- NÃO existe usuário de QA neste backup (qa.admin@kredor.com.br foi perdido no restore).
- Para testar login, criar um admin de teste (script/seed) ou pedir ao usuário para resetar uma senha.

## Usuários REAIS (restaurados do backup de produção — senhas desconhecidas, NÃO usar)
- diego.haidmann@gmail.com (perfil: admin, dono)
- adilsonsoares203@gmail.com, rogeriomoura504@gmail.com, fredrichuriel@gmail.com,
  janainadamascenofr@gmail.com, diego.haidmann2@gmail.com, danielcarlos775@gmail.com

Login endpoint: POST /api/auth/login  body: {"email","senha","turnstile_token"}
Turnstile em modo teste (site key 1x00000000000000000000AA sempre passa; secret 1x0000000000000000000000000000000AA).
