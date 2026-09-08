# Credenciais / Contas

Banco atual restaurado do backup **20260905-155351**.

## Conta ADMIN de teste (senha definida pela equipe)
- **Email:** diego.haidmann@gmail.com
- **Senha:** GestorTest@2026
- perfil: admin | plano: enterprise | email verificado | ativo
- Vê a seção "Super Admin" no Sidebar (Usuários, Assinaturas, Carteiras & Preços, etc.)
- Login exige turnstile_token (Turnstile de teste aceita qualquer token, ex.: "dummy")

## Outros usuários (senha original do backup — desconhecida)
- adilsonsoares203@gmail.com — usuario / enterprise
- rogeriomoura504@gmail.com — usuario / profissional
- fredrichuriel@gmail.com — usuario / trial (email NÃO verificado)
- janainadamascenofr@gmail.com — usuario / trial

## Turnstile (proteção anti-bot login/cadastro)
- Frontend: REACT_APP_TURNSTILE_SITE_KEY=1x00000000000000000000AA (site key de teste, sempre passa)
- Backend: TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA (secret de teste, sempre aprova)
