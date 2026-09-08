# GestorCred — PRD / Estado do Projeto

## Problema original
Importar projeto existente (GestorCred — gestão de empréstimos e cobrança PIX/WhatsApp),
subir todos os serviços via iniciar.sh e restaurar o banco de dados anexado.

## Arquitetura
- Backend: FastAPI (`/app/backend`, entrypoint `server.py` -> `main.py`), rotas em `/app/backend/routes`
- Frontend: React (`/app/frontend`)
- Banco: MongoDB local, DB `gestorcred`
- Scheduler habilitado (RUN_SCHEDULER=true)

## Feito (2026-09-08)
- Criados `backend/.env` e `frontend/.env` conforme env fornecido pelo usuário.
  - APP_URL e REACT_APP_BACKEND_URL preenchidos com a URL de preview do ambiente.
- Restaurado dump MongoDB do backup `backup-20260905-155351` no DB `gestorcred`
  (897 documentos, 0 falhas). Coleções: usuarios(5), clientes(44), emprestimos(86), etc.
- Instaladas dependências Python faltantes (bleach + requirements.txt).
- Serviços rodando: mongodb, backend (HTTP 200 em /api/), frontend (landing carrega).

## Observações
- Usuários vieram do backup de produção (campo `senha_hash`, `perfil`, `plano`). As senhas
  são as originais do backup — desconhecidas por nós. Se houver problema de login, resetar senha.

## Backlog / Próximos
- P2: Resetar senha de admin caso necessário.

## Sessão 2 (2026-09-08) — Ajustes na tela de Empréstimos
- Item 2 (feito e testado): coluna TAXA/PRAZO nos empréstimos SEM prazo agora mostra
  "🔄 Aberto" + a porcentagem de juros ("15% / mês" ou "5% / sem"). Desktop e mobile.
  Helper getTaxaSemPrazoLabel em Emprestimos.js.
- Fix defensivo: getTaxaComPrazoLabel evita render "null% / nullm" em registros legados.
- Item 1 (análise): as ações Prorrogar/Amortizar/Incorporar/Quitar Aberto são exclusivas
  de empréstimos sem_prazo/apenas_juros (backend valida e recusa outros). Não se aplicam
  ao HUDSON (juros_simples, prazo fixo), que já tem Pagar/Editar/Detalhes/PDF/Excluir.
- Senha de teste do admin diego.haidmann@gmail.com redefinida para Teste@2026 (ver test_credentials.md).

## Sessão 3 (2026-09-08) — Prorrogar empréstimos de PRAZO FIXO
- Feito e testado (testing agent 8/8 backend + frontend OK):
  - Backend: POST /api/emprestimos/{id}/prorrogar agora ramifica por metodo_calculo.
    Para métodos de prazo fixo (juros_simples/compostos/tabela_price/sac) chama
    _prorrogar_prazo_fixo (routes/emprestimos.py ~2657): mantém parcelas pagas,
    soft-deleta as em aberto e re-amortiza o SALDO de capital em (abertas + N) parcelas
    via gerar_parcelas_simulacao; atualiza total_parcelas, prazo e valor_total_com_juros.
    Branch legado 'apenas_juros' preservado (regressão OK).
  - Frontend (Emprestimos.js): opção 'Prorrogar Empréstimo' agora aparece para qualquer
    método (status ativo/inadimplente); modal com texto condicional (re-amortização vs apenas_juros).
- Teste E2E validado: pagamento -> prorrogação (parcelas recalculadas, pagas mantidas) -> quitação.
- Testes: /app/backend/tests/test_prorrogacao_prazo_fixo.py (criam/limpam dados próprios).

## Sessão 4 (2026-09-08) — Prévia + Histórico + Recibo de Prorrogação
- Feito e testado (testing agent: frontend 100%, pytest 5/5):
  - PRÉVIA: POST /api/emprestimos/{id}/prorrogar/preview (reusa _calcular_plano_prazo_fixo)
    mostra no modal o novo cronograma (parcelas + valor de cada + novo total com juros) antes de confirmar.
  - HISTÓRICO: cada prorrogação faz $push em emprestimo.historico_prorrogacoes (data, períodos,
    parcelas antes/depois, saldo, valor parcela). Exibido no modal Detalhes.
  - RECIBO: GET /{id}/recibo-prorrogacao/{prorrogacao_id} (PDF com novo cronograma) e
    POST .../whatsapp (envio via Evolution API — NÃO conectada neste ambiente: retorna erro amigável).
- Fix P0: adicionado `historico_prorrogacoes: List[dict]` ao model Emprestimo (response_model
  estava removendo o campo). Corrigido default para lista vazia (null quebrava o $push).
- Testes: /app/backend/tests/test_prorrogacao_melhorias.py (5/5).
