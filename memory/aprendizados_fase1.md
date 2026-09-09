# Aprendizados Fase 1
- `db.parcelas` (Motor) cria objeto novo a cada acesso: monkeypatch tem que ser na classe AsyncIOMotorCollection.
- Motor amarra client ao 1º event loop: em testes use um único loop (não asyncio.run por teste).
- Rename mecânico de campos: regex \b(nome)\b(?!_centavos) + revisão manual de saídas sem sufixo (dashboard, prorrogação, ajustes).
- grep linha-a-linha de `session=` dá falso positivo em chamadas multilinha -> usar scripts/checar_session_em_transacao.py (AST).
