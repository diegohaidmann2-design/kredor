# Test Credentials — GestorCred

Banco importado do backup do usuário (`backup-20260905-155351.tar.gz`, mongodump BSON).
DB: `gestorcred` | 5 usuários, 44 clientes, 86 empréstimos.

## Usuários no banco importado (senhas pertencem ao usuário — NÃO alteradas)
- diego.haidmann@gmail.com  (perfil: admin, plano: enterprise)
- adilsonsoares203@gmail.com (usuario, enterprise)
- rogeriomoura504@gmail.com (usuario, profissional)
- fredrichuriel@gmail.com (usuario, trial)
- janainadamascenofr@gmail.com (usuario, trial)

## Reset de senha do admin (fallback)
Se precisar de acesso admin com senha conhecida, rodar:
`cd /app/backend && /root/.venv/bin/python scripts/seed_admin.py`
→ define diego.haidmann@gmail.com / Admin@2026 (idempotente, só reseta a senha do admin).
