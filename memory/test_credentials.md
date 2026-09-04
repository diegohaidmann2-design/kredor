# Credenciais / Contas

## Banco de dados
- MongoDB local: mongodb://localhost:27017
- DB_NAME: gestorcred (restaurado do backup backup-20260902-182538)

## Conta de TESTE (QA) — use para testes automatizados
- Email: qa.consultas@teste.com
- Senha: Teste@123
- Plano: trial (ativo). perfil: usuario. Sem clientes/empréstimos (conta nova).

## Contas de usuário existentes (restauradas do backup)
As senhas estão com hash no banco e NÃO são conhecidas. Use as credenciais reais do proprietário.
- diego.haidmann@gmail.com  (plano: enterprise, perfil: admin)
- adilsonsoares203@gmail.com (plano: enterprise)
- rogeriomoura504@gmail.com  (plano: profissional)
- fredrichuriel@gmail.com    (plano: trial)

Login endpoint: POST /api/auth/login  body: {"email": "...", "senha": "..."}

## Módulo de Consultas (LosDados)
- Endpoints backend: POST /api/consultas/cpf {cpf}, GET /api/consultas/historico, GET /api/consultas/{id}, DELETE /api/consultas/{id}
- Chave da API em backend/.env (LOSDADOS_API_KEY) — NUNCA exposta ao frontend.
- CPFs válidos para teste (retornam dados reais de sandbox): 11144477735, 111.444.777-35
- CPF inválido (deve dar erro 400): 12345678900
