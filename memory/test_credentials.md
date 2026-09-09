# Credenciais de Teste — Kredor

## Admin de TESTE (criado para QA — pode usar livremente)
- Email: qa.admin@kredor.com.br
- Senha: QaAdmin@2026
- Perfil: admin | Plano: enterprise (acesso total ao Super Admin)

## Usuários REAIS (restaurados do backup de produção — senhas desconhecidas, NÃO usar)
- diego.haidmann@gmail.com (perfil: admin, dono)
- adilsonsoares203@gmail.com, rogeriomoura504@gmail.com, fredrichuriel@gmail.com, janainadamascenofr@gmail.com

Login endpoint: POST /api/auth/login  body: {"email","senha","turnstile_token"}
Turnstile em modo teste (site key 1x0000...AA sempre passa; secret 1x0000...AA).

Dados restaurados: 5 usuários (+1 qa.admin), 44 clientes, 86 empréstimos, 11 configurações.
