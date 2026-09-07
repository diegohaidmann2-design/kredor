# Test Credentials — GestorCred

Banco importado do backup do usuário (`backup-20260905-155351.tar.gz`, mongodump BSON).
DB: `gestorcred` | 5 usuários, 44 clientes, 86 empréstimos.

## Conta de TESTE QA (use esta para testes — não altera contas reais)
- Email: `qa.teste@gestorcred.com`
- Senha: `Teste@2026`
- Perfil: admin | plano: enterprise
- Recriar: `cd /app/backend && /root/.venv/bin/python scripts/seed_qa_user.py`

## Cloudflare Turnstile
- Habilitado (backend tem `TURNSTILE_SECRET_KEY` de teste `1x0000000000000000000000000000000AA`).
- Frontend usa a site key de teste `1x00000000000000000000AA` (`REACT_APP_TURNSTILE_SITE_KEY`).
- Modo teste = widget sempre passa automaticamente.

## Usuários reais no banco importado (senhas pertencem ao usuário — NÃO alteradas)
- diego.haidmann@gmail.com  (perfil: admin, plano: enterprise)
- adilsonsoares203@gmail.com (usuario, enterprise)
- rogeriomoura504@gmail.com (usuario, profissional)
- fredrichuriel@gmail.com (usuario, trial)
- janainadamascenofr@gmail.com (usuario, trial)

## Reset de senha do admin real (fallback — sobrescreve senha do Diego)
`cd /app/backend && /root/.venv/bin/python scripts/seed_admin.py`
→ define diego.haidmann@gmail.com / Admin@2026 (idempotente).
