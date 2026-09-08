# Credenciais / Contas

⚠️ Banco atual restaurado do backup **20260905-155351** (importado a pedido do usuário).
As senhas neste dump são as ORIGINAIS dos usuários (hash do backup) — a senha de teste
`GestorTest@2026` NÃO se aplica a este banco (era de outro dump). Login via API retorna
401 até que uma senha conhecida seja definida.

## Usuários no banco (senha original desconhecida — hash do backup)
- diego.haidmann@gmail.com — enterprise (dono da conexão WhatsApp)
- adilsonsoares203@gmail.com — enterprise
- rogeriomoura504@gmail.com — profissional
- fredrichuriel@gmail.com — trial
- janainadamascenofr@gmail.com — trial

## Turnstile (proteção anti-bot login/cadastro)
- Frontend: REACT_APP_TURNSTILE_SITE_KEY=1x00000000000000000000AA (site key de teste, sempre passa)
- Backend: TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA (secret de teste, sempre aprova)
