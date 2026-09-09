# Credenciais de Teste — GestorCred

## Usuário Admin (dados reais restaurados do backup-20260905-155351)
- Email: diego.haidmann@gmail.com
- Perfil: admin
- Senha: DESCONHECIDA (senha real do dono, do backup de produção). Os valores de teste
  anteriores (Admin@2026 / Teste@2026) foram SOBRESCRITOS ao restaurar os dados reais.
  Para testar, peça ao dono a senha OU redefina via script sob solicitação explícita.

## Outros usuários (perfil=usuario, senhas reais desconhecidas)
- adilsonsoares203@gmail.com
- rogeriomoura504@gmail.com
- fredrichuriel@gmail.com
- janainadamascenofr@gmail.com

Login endpoint: POST /api/auth/login  body: {"email","senha","turnstile_token"}
Turnstile em modo teste (site key 1x0000...AA sempre passa).

Dados restaurados: 5 usuários, 44 clientes, 86 empréstimos, 11 configurações.
