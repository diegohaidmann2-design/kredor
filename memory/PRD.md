# Kredor / GestorCred — PRD

## Problema / Origem
App de gestão de empréstimos a juros clonado do repositório `diegohaidmann2-design/kredor`, rodando em modo desenvolvimento no preview Emergent. Stack: FastAPI + React (CRA/craco) + MongoDB.

## Ambiente
- Host atual do preview (este pod): `https://58322996-762c-4c69-a190-240071e81d8b.preview.emergentagent.com`
- `REACT_APP_BACKEND_URL` (frontend/.env), `APP_URL` e `CORS_ORIGINS` (backend/.env) devem apontar para o host do pod atual. IMPORTANTE: o frontend/.env versionado no git traz `gestorcred-staging-2...`; ao reabrir o projeto num pod novo é preciso re-substituir pelo host do preview atual.
- DB: `gestorcred`.
- Storage: Emergent Object Storage (EMERGENT_LLM_KEY setado). NÃO possui API de delete (soft-delete no DB é a fonte da verdade).
- Turnstile: chaves de TESTE (site 1x...AA / secret 1x...AA) — widget passa sozinho.

## Personas
- Dono/credor (login) — gerencia clientes, empréstimos, cobranças, aprova cadastros.
- Cliente final (sem login) — preenche ficha pública, futuramente aceita empréstimo.

## Implementado (com datas)
- 2026-06: Clone + subida do app; correção de dependências (frontend: crypto-js, date-fns-tz, jspdf, jspdf-autotable, qrcode.react).
- 2026-06: Import do banco `gestorcred` a partir do backup.
- 2026-06: **Bug raiz (CORS/host):** app servido em `kredor-preview` mas `REACT_APP_BACKEND_URL`/`env-config.js` apontavam para outro host → CORS bloqueava as chamadas → toast "Não foi possível carregar configurações". Corrigido: frontend aponta para o host canônico (mesma origem) e CORS_ORIGINS inclui ambos os hosts. Service worker: env-config.js agora network-first + CACHE_NAME v1.0.1.
- 2026-06: **Melhorias no cadastro público:** validação Cloudflare Turnstile no `POST /cadastro-publico/solicitar/{token}` (frontend + backend); limpeza de anexos do storage ao rejeitar/excluir ficha (`delete_object` + `_apagar_anexos_storage`). TTL index de `rate_limits` já existia.
- Testado (testing_agent iteration_3): 10/10 backend + frontend OK.
- 2026-06 (sessão atual): Ajuste do domínio do preview no `.env` (front+back) — o frontend estava com `gestorcred-staging-2` e todas as chamadas de API caíam por CORS (login/dashboard quebrados). Corrigido para o host do pod atual; app 100% funcional de novo.
- 2026-06 (sessão atual): **Modal profissional de cobrança em /pagamentos.** O botão "Cobrar" (por parcela) agora abre um modal (`components/pagamentos/CobrancaModal.jsx`) com: seleção de modelo (auto-seed de templates de cobrança + opção "Mensagem padrão"), pré-visualização estilo WhatsApp com a mensagem final renderizada (dados reais da parcela) e botão de envio. Backend: `enviar-cobranca-parcela` aceita `template_id`; novo `GET .../preview`. Seed de usuários de teste executado (ver test_credentials.md).

## Backlog / P0-P2
- P1: **Aceite de empréstimo reaproveitando a ficha pública** (assinatura + termos do contrato/CCB). Proposta definida; aguardando escolha de escopo do usuário.
- P2: Alinhar APP_URL ao host canônico (hoje é sobrescrito pelo supervisor com o alias; links de cadastro usam o alias, mas o preview canonicaliza no navegador).
- P2: Refatorar `cadastro_publico.py` (público vs admin) e inicializar `_arquivos_pendentes = {}` no topo.
- P2: Testar fluxo do DONO (aprovar/rejeitar) — precisa de credenciais de login (senhas do backup são desconhecidas).

## Próximas tarefas
1. Confirmar escopo do aceite de empréstimo e implementar.
2. (Se necessário) resetar senha de uma conta para permitir login/testes do lado dono.
