# Kredor — Plano de Correções Técnicas

> **Para quem executa (humano ou agente de IA):** este documento é uma especificação, não uma sugestão.
> Cada tarefa tem **critério de aceite verificável**. Não marque uma tarefa como concluída sem rodar
> o comando de verificação e colar a saída real.
>
> Leia a seção **REGRAS PERMANENTES** antes de escrever qualquer linha de código. Ela existe porque
> os erros listados lá **já aconteceram neste repositório** e não podem se repetir.
>
> **Sobre as referências `arquivo:linha`:** todas foram validadas em **10/09/2026** contra o commit
> `170fed7`. Elas envelhecem a cada commit. Onde o documento oferece um comando para **gerar** a
> lista (tarefas 2.1, 2.3, 3.3), use o comando — ele é a fonte de verdade, não o número no texto.
> Se uma referência não bater com o que você vê no arquivo, gere a lista de novo antes de concluir
> que a tarefa mudou de escopo.

---

## Sumário

- [Regras permanentes](#regras-permanentes)
- [Como reportar progresso](#como-reportar-progresso)
- [FASE 1 — Bloqueadores](#fase-1--bloqueadores)
  - [1.1 Rotacionar credencial exposta](#11-rotacionar-credencial-exposta)
  - [1.2 Segredos obrigatórios em produção](#12-segredos-obrigatórios-em-produção)
  - [1.3 Dinheiro em centavos inteiros](#13-dinheiro-em-centavos-inteiros)
  - [1.4 Replica set e transações](#14-replica-set-e-transações)
- [FASE 1.5 — Correções da Fase 1](#fase-15--correções-da-fase-1)
  - [1.5.1 Valores negativos em empréstimos pequenos](#151-valores-negativos-em-empréstimos-pequenos)
  - [1.5.2 `transacao()` degrada em silêncio](#152-transacao-degrada-em-silêncio)
  - [1.5.3 `pytest-asyncio` ausente](#153-pytest-asyncio-ausente--testes-que-não-rodam)
  - [1.5.4 Ponto cego do checker de `session=`](#154-ponto-cego-do-checker-de-session)
  - [1.5.5 Build Docker do frontend quebrado](#155-build-docker-do-frontend-quebrado-node-18-vs-yarnlock)
- [FASE 2 — Operabilidade](#fase-2--operabilidade)
  - [2.1 Logging estruturado](#21-logging-estruturado)
  - [2.2 Datas como Date do BSON](#22-datas-como-date-do-bson)
  - [2.3 Eliminar consultas dentro de laço (N+1)](#23-eliminar-consultas-dentro-de-laço-n1)
  - [2.4 `exc_info=True` quebra o log de erro](#24-exc_infotrue-quebra-o-log-de-erro)
  - [2.5 Testes de race condition falham na suíte](#25-testes-de-race-condition-falham-na-suíte)
  - [2.6 Migração escreve valores não-inteiros em `_centavos`](#26-migração-escreve-valores-não-inteiros-em-campos-_centavos)
  - [2.7 Autorização: `perfil="superadmin"` é valor morto](#27-autorização-perfilsuperadmin-é-um-valor-morto-e-armadilhado)
  - [2.8 Resíduos da 2.7 — 8 guardas escaparam](#28-resíduos-da-tarefa-27--8-guardas-escaparam-e-perfil-sem-validação)
  - [2.9 Convite de equipe grava senha no campo errado](#29-convite-de-equipe-grava-a-senha-no-campo-errado-e-não-passa-pelo-modelo)
- [FASE 3 — Manutenibilidade](#fase-3--manutenibilidade)
  - [3.1 Um único gateway de pagamento](#31-um-único-gateway-de-pagamento)
  - [3.2 Limpeza de arquivos mortos](#32-limpeza-de-arquivos-mortos)
  - [3.3 Quebrar ciclos de import](#33-quebrar-ciclos-de-import)
  - [3.4 Fonte única do cálculo financeiro](#34-fonte-única-do-cálculo-financeiro)
  - [3.4.1 Endpoint público de simulação sem limite (DoS)](#341-endpoint-público-de-simulação-sem-limite-de-entrada-dos)
  - [3.5 Frontend](#35-frontend)
    - [3.5(c) Erro engolido em `catch`](#35c-erro-engolido-em-catch)
    - [3.5(d) Quebrar componentes grandes](#35d-quebrar-componentes-grandes)
- [Checklist final](#checklist-final)

---

## Regras permanentes

Estas regras valem para **todo** código novo e para todo código que você tocar.

### R1 — Dinheiro nunca é `float`

```python
# ERRADO — proibido
valor_total: float = 0.0
valor = round(principal * taxa, 2)

# CERTO
valor_total_centavos: int = 0
```

Motivo: `0.1 + 0.2 != 0.3` em ponto flutuante binário. Em sistema de crédito isso vira divergência
contábil. Já existe resíduo de R$ 0,01 no cálculo Price atual.

### R2 — Arredondar **uma vez só**, no final

```python
# ERRADO — arredonda 12x e acumula erro
for i in range(meses):
    parcelas.append({"valor": round(pmt, 2)})

# CERTO — calcula em centavos, distribui o resto na última parcela
base = total_centavos // meses
resto = total_centavos - (base * meses)
parcelas = [base] * meses
parcelas[-1] += resto
```

### R3 — Proibido `print()` em código de aplicação

Use `logger` de `services/logging_service.py`. Todo log precisa carregar `usuario_id` quando existir.

```python
# ERRADO
print(f"✅ Parcela #{n} gerada")

# CERTO
logger.info("Parcela gerada automaticamente", data={"usuario_id": usuario_id, "numero": n})
```

Exceção: scripts em `backend/scripts/` e `backend/utils/dev-tools/` podem usar `print()`.

### R4 — Proibido `import` dentro de função

Se houver ciclo de import, **quebre o ciclo** (extraia o tipo/função compartilhada para um módulo
neutro). Não empurre o import para dentro da função. Existem 214 ocorrências hoje; não crie a 215ª.

Exceção única e permitida: import pesado e raramente usado (ex.: geração de PDF), **com comentário
explicando o motivo real**.

### R5 — Proibido criar arquivos `_v2`, `.backup`, `.bak`, `_old`, `_new`

O git é o histórico. Se precisa reescrever, reescreva no lugar. Se precisa de duas implementações
convivendo, isso é um problema de design que deve ser resolvido, não versionado no nome do arquivo.

### R6 — Comentários descrevem o **domínio**, nunca o processo

```python
# ERRADO
# Fix #8: Operação atômica com filtro de status para evitar race condition
# Notificação removida: (CÓDIGO REMOVIDO)

# CERTO
# Filtro por status na própria query garante que dois pagamentos simultâneos
# não baixem a mesma parcela duas vezes.
```

Nunca deixe comentário descrevendo código que foi apagado. Apague o comentário junto.

### R7 — Nenhum segredo entra no git

Senhas, tokens, chaves de API e credenciais de teste vão em `.env` (que está no `.gitignore`).
Nunca em `.md`, nunca em comentário, nunca em teste.

### R8 — Toda query filtra por `usuario_id`

Sem exceção nas coleções multi-tenant (`clientes`, `emprestimos`, `parcelas`, `pagamentos`,
`contratos`, `notificacoes`). Se uma query administrativa precisa cruzar tenants, deixe explícito
no nome da função (`..._todos_tenants`) e restrinja por perfil.

### R9 — Não invente escopo

Faça **exatamente** a tarefa descrita. Não refatore de passagem, não "melhore" arquivos vizinhos,
não adicione features. Se encontrar outro problema, anote na seção de observações da tarefa e siga.

### R10 — Não declare conclusão sem prova

Rode o comando de verificação da tarefa e cole a saída. Se um teste falhou, diga que falhou e mostre
a saída. Nunca escreva "corrigido e testado" sem ter executado.

### R11 — Se a coleção tem modelo Pydantic, crie o documento pelo modelo

Nunca monte um dict literal para inserir numa coleção que já tem um modelo de entidade.

```python
# ERRADO — dict literal numa coleção que tem modelo
novo_membro = {
    "id": str(uuid.uuid4()),
    "nome": dados.nome,
    "perfil": "usuario",
    "senha": hashed_password,      # <- nome divergente passa sem ninguém notar
}
await db.usuarios.insert_one(novo_membro)

# CERTO — o modelo é a fonte da forma do documento
membro = Usuario(nome=dados.nome, perfil="usuario", owner_id=current_user.id, ...)
doc = membro.model_dump()
doc["senha_hash"] = hashed_password    # credencial fica fora do modelo, por design
await db.usuarios.insert_one(doc)
```

O padrão correto já existe no repositório, use como referência:
`routes/clientes.py:47-54` e `routes/auth.py:81-92`.

**Por que esta regra existe:** as tarefas **2.8** e **2.9** têm a mesma assinatura — código que
contorna a abstração. Na 2.8 foram guardas de autorização que não usaram a fonte única; na 2.9 foi um
dict literal que não usou o modelo `Usuario`, e foi assim que o campo `senha` divergiu de
`senha_hash` sem ninguém notar, deixando **18 dos 32 campos** do modelo ausentes no documento.

**Onde a regra NÃO se aplica:** coleções de log, auditoria e telemetria que não têm modelo de
entidade — `jobs_execucoes`, `backup_logs`, `whatsapp_mensagens_log`, `logs_planos`,
`login_attempts`, `login_attempts_ip`, `tokens_revogados`, `regua_envios`, `uploads`,
`carteira_recargas`. Dict literal ali é adequado; criar modelo só para elas seria escopo inventado
(regra R9).

**Violações medidas em 10/09/2026 — são 3:**

| Local | Coleção | Modelo que deveria usar |
|---|---|---|
| `routes/equipe.py:87` | `usuarios` | `Usuario` (tarefa 2.9) |
| `routes/assinaturas.py:1871` | `notificacoes` | `Notificacao` |
| `services/notificacao_service.py:307` | `notificacoes` | `Notificacao` |

Caso à parte: `routes/assinaturas.py:1669` e `:2127` inserem em `transacoes_checkout`, que **não tem
modelo de entidade** — `models/transacao.py` só define os enums `StatusTransacao`,
`MetodoPagamento` e `MotivoRecusa`. Esses enums existem e não são usados para validar a escrita.
Criar o modelo dessa entidade é trabalho legítimo, mas não é coberto por nenhuma tarefa deste
documento; anote e siga (R9).

Localizar candidatos a violação:

```bash
cd backend && grep -rn "insert_one({" routes/ services/ jobs/ \
  | grep -oP "db\.\K[a-z_]+" | sort | uniq -c | sort -rn
```

Para cada coleção listada, confirme em `backend/models/` se existe um modelo de entidade
correspondente. Se existir, é violação.

---

## Como reportar progresso

Ao concluir cada tarefa, escreva no PR/commit:

```
Tarefa: 1.3
Arquivos alterados: <lista>
Critério de aceite: <cole a saída real do comando de verificação>
Observações: <problemas encontrados fora do escopo, se houver>
```

---

## Linha de base

Medição inicial em **09/09/2026** (commit `0c5d4cd`) e última remedição em **10/09/2026**
(commit `0c796b2`, após Fases 1, 1.5, 2.1, 2.4, 2.5, 2.6, 2.7, 3.1 e 3.2). Use estes números para
saber se você realmente mexeu o ponteiro.

| Tarefa | Métrica | Inicial | Atual | Meta | |
|---|---|---:|---:|---:|:--|
| 1.1 | `test_credentials.md` versionado | 1 | **0** | 0 | ✅ |
| 1.2 | Segredo JWT com env vazia | `''` | **`RuntimeError`** | `RuntimeError` | ✅ |
| 1.3 | Campos monetários `float` nos modelos | 25 | **0** | 0 | ✅ |
| 1.3 | `round()` em `calculos.py` | 20 | **0** | 0 | ✅ |
| 1.4 | Estado do replica set | `standalone` | **1** (primário) | 1 | ✅ |
| 1.4 | Operações sem `session=` em transação | — | **0** | 0 | ✅ |
| 1.5.1 | Valores negativos na grade de 2.700 casos | 37 | **0** | 0 | ✅ |
| 1.5.2 | `transacao()` avisa/falha sem replica set | não | **sim** | sim | ✅ |
| 1.5.3 | `pytest-asyncio` + `pytest.ini` | não | **sim** | sim | ✅ |
| 1.5.4 | Checker de `session=` com allowlist | não | **sim** | sim | ✅ |
| 1.5.5 | `node:20-alpine` no repositório | não | **sim** | sim | ✅ |
| **2.1** | **`print()` em `routes/services/jobs`** | **296** | **0** | 0 | ✅ |
| 2.2 | `.isoformat()` antes do insert | 357 | 318 | 0 | ⏳ |
| 2.2 | `datetime.utcnow()` | 35 | 30 | 0 | ⏳ |
| 2.3 | Queries dentro de laço | 48 | 45 | 0 | ⏳ |
| **2.4** | **`--- Logging error ---` ao logar com `exc_info=True`** | sim | **não** | não | ✅ |
| **2.5** | **Testes de race condition falhando na suíte** | 1 | **0** (3 passed, 2 execuções) | 0 | ✅ |
| **2.6** | **Campos `_centavos` com tipo != inteiro** | — | **0** | 0 | ✅ |
| **2.6** | **`int(round(` no dashboard** | 2 | **0** | 0 | ✅ |
| **2.7** | **Guardas de admin com literal duplicado** | 19 | **0** (fonte única) | 0 | ✅ |
| **2.7** | **Camadas que discordam sobre `superadmin`** | frontend sim / backend não | **valor eliminado** | consistente | ✅ |
| **2.8** | **Guardas `not in (...)` fora da fonte única** | 8 | **0** | 0 | ✅ |
| **2.8** | **`perfil` validado no painel administrativo** | não | **sim** (`Literal`) | sim | ✅ |
| **2.8** | **Perfil inválido no banco devolve** | 500 | **401** | 401 | ✅ |
| **2.9** | **Caminhos que gravam a senha em campo divergente** | 3 | **0** | 0 | ✅ |
| **2.9** | **`verificar_senha` com hash inválido** | levanta | **`False`** | `False` | ✅ |
| **3.4** | **Fórmula financeira no frontend** | 2 | **0** | 0 | ✅ |
| **3.5** | **`process.env.REACT_APP_BACKEND_URL`** | 3 | **0** | 0 | ✅ |
| **3.4.1** | **Prazo acima do teto devolve** | 200 (processa) | **422** | 422 | ✅ |
| **R11** | **Criação de entidade com dict literal onde há modelo** | 3 | **0** | 0 | ✅ |
| 3.1 | Módulos de gateway de pagamento | 5 | **2** (sob estratégia de seleção) | 1 ou interface comum | ✅ |
| 3.2 | Arquivos `.backup`/`.bak`/`_v2` versionados | 3 | **0** | 0 | ✅ |
| 3.2 | Relatórios de IA versionados | 116 | **0** | 0 | ✅ |
| **3.3** | **`import` dentro de função** | 214 | **3** | < 20 | ✅ |
| **3.5(b)** | **`axios`/`fetch` direto em `pages/`** | 27 | **0** | 0 | ✅ |
| 3.5(c) | `catch` que só faz `console.error` | 91 | 92 | 0 | ⏳ |
| 3.5(d) | Arquivos do frontend > 800 linhas | 11 | 11 | 0 | ⏳ |

**Concluídas e verificadas em produção:** Fase 1, Fase 1.5, e as tarefas **2.1, 2.4, 2.5, 2.6, 2.7,
3.1 e 3.2**. Suíte com **2.882 testes passando, 0 falhas** (inclui as 2.865 propriedades de
precisão monetária, o rollback real de transação e os 3 de condição de corrida).

**Restam 4:** **2.2** (datas — 318 `isoformat()`, 30 `utcnow()`), **2.3** (45 queries em laço),
**3.5(c)** (92 `catch` sem toast) e **3.5(d)** (11 arquivos do frontend acima de 800 linhas).

> **Alinhamento sobre a 3.5(d), feito em 10/09/2026 a pedido de quem executa.** O critério original
> deste documento era **binário** ("maior arquivo < 800") e o número estava desatualizado (dizia 4
> arquivos, são **11**, somando 15.361 linhas). Quem executa apontou que critério binário sobre 11
> arquivos independentes torna progresso parcial invisível e empurra para uma mudança grande de uma
> vez — risco alto num app de dinheiro. **Estava certo: o defeito era da especificação.** A métrica
> passou a ser a **contagem decrescente** de arquivos acima de 800 linhas (11 → 0), um arquivo por
> commit, em ordem crescente de risco, com gate por arquivo. Ver 3.5(d).

> **Nota sobre a métrica de 2.4:** a contagem de `exc_info=True` **subiu** de 6 para 8, e isso está
> correto. A correção foi centralizada no `_log` (`logging_service.py:144`), então os call sites
> passaram a ser seguros — usar `exc_info=True` deixou de ser defeito. A métrica válida é a ausência
> de `--- Logging error ---` na saída, não a contagem de chamadas.

> **Nota sobre a 3.1:** sobraram **2** gateways (`asaas_service.py` e `syncpay.py`), não 1. É
> deliberado e aceito: `routes/assinaturas.py` implementa uma estratégia de seleção
> (`asaas_only` / `syncpay_only` / `rotacao` / `fallback`) com `gateway_primario` — exatamente a
> alternativa que o critério de aceite previa ("ou o número de implementações sob a interface
> comum"). Deixou de ser 5 módulos soltos com APIs divergentes.

> **Correção a este documento:** o patch que a versão anterior propunha para a tarefa 1.5.1
> (dividir o *total* e derivar o principal) era **pior** que o implementado. Medido sobre 940 casos
> válidos: a proposta deste documento reintroduzia **valor negativo em 18 casos**, enquanto a
> implementação escolhida pela equipe (dividir principal e juros separadamente) tem **zero**
> negativos. O custo é que a última parcela absorve os dois restos — desvio máximo de
> **R$ 6,37** num empréstimo de R$ 999.999,99 em 360x, e de **4 centavos** em R$ 1.000,00 em 12x.
> A troca está certa: garantia forte de não-negatividade vale mais que igualdade exata das parcelas.
> A seção 1.5.1 abaixo foi mantida como registro histórico do bug, mas **o patch sugerido lá não
> deve ser aplicado**.

Script para remedir tudo de uma vez:

```bash
cd /var/www/kredor
p(){ printf "%-46s" "$1"; }
p "1.1 test_credentials versionado";  git ls-files | grep -c "test_credentials"
p "1.3 campos float monetarios";      grep -rnE "valor.*: float|saldo.*: float" backend/models/ | grep -v taxa | wc -l
p "1.3 round() em calculos.py";       grep -c "round(" backend/services/calculos.py
p "1.4 replica set (myState)";        docker exec kredor_mongodb mongosh --quiet --eval 'try{print(rs.status().myState)}catch(e){print("standalone")}'
p "2.1 print() em app";               grep -rn "print(" backend/routes/ backend/services/ backend/jobs/ | wc -l
p "2.3 queries em laco (total)";      (cd backend && python3 scripts/checar_query_em_laco.py routes/*.py services/*.py jobs/*.py | grep -oP '^\S+: \K\d+' | awk '{s+=$1} END {print s}')
p "3.1 gateways de pagamento";        ls backend/services/ | grep -icE "asaas|mercadopago|pagseguro|syncpay"
p "3.2 arquivos mortos";              git ls-files | grep -cE "\.backup$|\.bak$|_v2\.py$"
p "3.3 imports em funcao";            grep -rnE "^\s+(from|import) " backend/routes/ backend/services/ backend/jobs/ | grep -v "^\s*#" | wc -l
p "3.4 formula no frontend";          grep -rnE "Math\.pow\(1 ?\+" frontend/src/ | grep -v node_modules | wc -l
p "3.5 maior arquivo do front";       (cd frontend && find src -name "*.js" | xargs wc -l | sort -rn | sed -n '2p' | awk '{print $1" linhas ("$2")"}')
p "3.5 axios/fetch em pages";         grep -rn "axios\.\|fetch(" frontend/src/pages/ | wc -l
p "3.5 process.env BACKEND_URL";      grep -rn "process.env.REACT_APP_BACKEND_URL" frontend/src/ | wc -l
```

> **Nota sobre o ambiente:** o host tem apenas `python3` (não existe `python`). Dentro do container
> `kredor_backend` existe `python` (3.11.15) e as dependências instaladas. Comandos que importam
> módulos do projeto precisam rodar via `docker exec kredor_backend python ...`.

---

# FASE 1 — Bloqueadores

> Não escale a base de clientes antes desta fase estar completa.

## 1.1 Rotacionar credencial exposta

**Severidade:** crítica
**Esforço:** 30 minutos

### Problema

`memory/test_credentials.md` está versionado no git e contém a senha de uma conta com **acesso total
de Super Admin**:

```
Email: qa.admin@kredor.com.br
Senha: (omitida — a regra R7 deste documento proíbe senha em arquivo versionado)
Perfil: admin | Plano: enterprise
```

O arquivo também lista e-mails reais de 5 usuários de produção.

### O que fazer

1. Trocar a senha da conta `qa.admin@kredor.com.br` no sistema (ou desativar a conta se não for mais
   necessária).
2. Remover o arquivo do controle de versão:
   ```bash
   git rm --cached memory/test_credentials.md
   echo "memory/test_credentials.md" >> .gitignore
   ```
3. Verificar se há outros segredos versionados:
   ```bash
   git ls-files | xargs grep -lniE "senha:|password:|secret|api[_-]?key" 2>/dev/null
   ```
4. Se o repositório já foi compartilhado com terceiros, purgar o arquivo do histórico com
   `git filter-repo --path memory/test_credentials.md --invert-paths` e forçar o push.

### O que NÃO fazer

- Não apenas edite o arquivo removendo a senha. O histórico do git mantém a versão antiga.
- Não substitua por um "exemplo" com senha falsa parecida. Use `.env.example` com valores vazios.

### Critério de aceite

```bash
git ls-files | grep -c "test_credentials" ; # deve retornar 0
```

E a senha antiga não deve mais autenticar em `POST /api/auth/login`.

---

## 1.2 Segredos obrigatórios em produção

**Severidade:** alta
**Esforço:** 1 hora

### Problema

`backend/config.py:34` tem fallback hardcoded para o segredo do JWT:

```python
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'sgej-secret-key')
```

Se a variável de ambiente sumir, a aplicação sobe **sem erro** usando um segredo público. Todo token
JWT passa a ser forjável por qualquer pessoa que leia este repositório.

Mesmo padrão em `backend/services/crypto_service.py:31`: quando `FIELD_ENCRYPTION_KEY` está ausente,
ele **gera uma chave aleatória** e segue. Resultado: os dados criptografados na inicialização anterior
ficam ilegíveis para sempre.

`backend/config.py:28` inclui `"*"` na lista de CORS de fallback, combinado com
`allow_credentials=True` em `backend/main.py:260` — combinação proibida pela especificação CORS.

### O que fazer

Em `backend/config.py`, criar um helper e usá-lo para os segredos:

```python
def _env_obrigatoria(nome: str) -> str:
    """Lê variável de ambiente. Em produção, ausência é erro fatal."""
    valor = os.environ.get(nome, "")
    if not valor:
        if os.environ.get("ENVIRONMENT") == "production":
            raise RuntimeError(
                f"{nome} não definida. Em produção não existe valor padrão para segredos."
            )
        return f"dev-only-{nome.lower()}"
    return valor


JWT_SECRET_KEY = _env_obrigatoria("JWT_SECRET_KEY")
```

Aplicar o mesmo a `FIELD_ENCRYPTION_KEY` em `crypto_service.py` — em produção, ausência deve ser
`RuntimeError`, nunca geração automática.

Remover `"*"` da lista de CORS de fallback em `config.py:28`.

### O que NÃO fazer

- Não use `assert` para isso (`assert` é removido com `python -O`).
- Não faça a validação só no `lifespan` do FastAPI. Tem que falhar no import, antes de qualquer
  worker aceitar requisição.

### Critério de aceite

```bash
docker exec -e ENVIRONMENT=production -e JWT_SECRET_KEY= kredor_backend python -c "import config" 2>&1 | tail -1
# Esperado: RuntimeError: JWT_SECRET_KEY não definida...
```

> O comando roda **dentro do container** porque as dependências (`motor`, `dotenv`) só existem lá.
> O host tem apenas `python3` e não tem os pacotes instalados.

Comportamento atual verificado (antes da correção) — as duas formas de falha:

| Situação | `os.environ.get('JWT_SECRET_KEY', 'sgej-secret-key')` retorna |
|---|---|
| Variável **ausente** | `'sgej-secret-key'` — segredo público deste repositório |
| Variável **vazia** (`JWT_SECRET_KEY=`) | `''` — segredo vazio |

**Atenção à pegadinha:** o segundo parâmetro de `os.environ.get()` só se aplica quando a chave está
**ausente**. Se a variável existir vazia, ele devolve string vazia e o default é ignorado. Por isso o
helper `_env_obrigatoria` testa `if not valor` (que pega ausente **e** vazia), e não
`if nome not in os.environ`.

E a aplicação atual deve continuar subindo normalmente (as variáveis já existem no `.env`).

---

## 1.3 Dinheiro em centavos inteiros

**Severidade:** crítica
**Esforço:** 3 a 5 dias
**Esta é a tarefa mais importante do documento.**

### Problema

Existem **37 campos monetários declarados como `float`** nos modelos. Nenhum uso de `Decimal` no
backend inteiro.

Consequência medida no cálculo real de `services/calculos.py` (R$ 10.000, 12x, 2% a.m.):

```
Soma das amortizações : 10000.01   (deveria ser 10000.00)
Resíduo               : +0.01
```

O código já tem gambiarra para esconder isso. Em `backend/routes/pagamentos.py:127`:

```python
novo_status = "pago" if novo_valor_pago >= (valor_total_devido - 0.005) else "parcial"
```

Essa tolerância de meio centavo existe **porque a soma em float não fecha**. Ela some quando o valor
for inteiro.

### Decisão de representação

**Use `int` representando centavos.** Não use `float`, não use `Decimal`, não use `Decimal128`.

Motivos:
- `int` do Python tem precisão arbitrária — não existe erro de representação.
- BSON armazena como `Int64`, comparação e ordenação em índice funcionam nativamente.
- JSON serializa sem ambiguidade.
- `Decimal128` do Mongo exige conversão em toda leitura (`.to_decimal()`) e é fácil esquecer.

### Convenção de nomes — obrigatória

**Renomeie os campos** adicionando o sufixo `_centavos`:

| Antes | Depois |
|---|---|
| `valor_principal` | `valor_principal_centavos` |
| `valor_total` | `valor_total_centavos` |
| `valor_pago` | `valor_pago_centavos` |
| `valor_juros` | `valor_juros_centavos` |
| `valor_multa` | `valor_multa_centavos` |
| `valor_juros_mora` | `valor_juros_mora_centavos` |
| `saldo_devedor` | `saldo_devedor_centavos` |
| `valor_total_com_juros` | `valor_total_com_juros_centavos` |
| `valor_total_juros` | `valor_total_juros_centavos` |

**Por que renomear é obrigatório:** se você mantiver o nome e trocar só o tipo, um lugar esquecido
lendo `valor_total` vai receber `10050` e tratar como R$ 10.050,00 em vez de R$ 100,50 — **e não vai
dar erro nenhum**. Renomeando, qualquer leitura esquecida quebra com `KeyError` na hora, alto e claro.

Campos de **taxa** (`taxa_juros_mensal`, `taxa_multa_atraso`, `taxa_juros_mora_diario`) continuam
`float` — são percentuais, não dinheiro.

### Onde converter

Converta **apenas na fronteira da API**:

- **Entrada:** o frontend envia reais (ex.: `100.50`) → converta para centavos no schema de request.
- **Interno:** todo cálculo, armazenamento e comparação em centavos inteiros.
- **Saída:** converta centavos → reais no schema de response, para o frontend não mudar.

Crie `backend/utils/dinheiro.py`:

```python
"""Conversão entre reais (fronteira da API) e centavos (representação interna)."""
from decimal import Decimal, ROUND_HALF_UP


def reais_para_centavos(valor: float | str | Decimal) -> int:
    """Converte um valor em reais para centavos inteiros.

    Usa Decimal na conversão para evitar que 100.50 vire 10049 por erro de float.
    """
    return int(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)


def centavos_para_reais(centavos: int) -> float:
    """Converte centavos inteiros para reais, para serialização na resposta da API."""
    return centavos / 100


def dividir_centavos(total: int, partes: int) -> list[int]:
    """Divide um total em N partes inteiras, jogando o resto na última.

    Garante que sum(resultado) == total exatamente.
    """
    if partes <= 0:
        raise ValueError("partes deve ser maior que zero")
    base = total // partes
    resultado = [base] * partes
    resultado[-1] += total - (base * partes)
    return resultado
```

### Regra do resíduo

Em `services/calculos.py`, todo método de amortização (Price, SAC, juros simples, juros compostos,
apenas juros) deve garantir:

```
soma(valor_principal_centavos de todas as parcelas) == valor_principal_centavos do empréstimo
```

Exatamente. Sem tolerância. O resto da divisão vai para a **última** parcela.

### Migração de dados existentes

O banco de produção atual está vazio (0 usuários), mas haverá restauração de backup. Escreva
`backend/scripts/migrar_para_centavos.py` que:

1. Percorre `emprestimos`, `parcelas`, `pagamentos`, `carteira_movimentos`, `transacoes_checkout`.
2. Para cada campo da tabela de nomes acima: lê o `float`, converte com `reais_para_centavos`,
   grava no campo novo com `$set`, e remove o antigo com `$unset`.
3. Usa `bulk_write` em lotes de 1000 — **não** um `update_one` por documento.
4. É **idempotente**: se o campo novo já existe, pula o documento.
5. Imprime no final: total de documentos migrados por coleção.

Antes de rodar em produção: `mongodump` da base completa.

### O que NÃO fazer

- **Não** deixe `round(x, 2)` em nenhum ponto do cálculo. Se sobrou um `round`, a tarefa não terminou.
- **Não** mantenha a tolerância `- 0.005` em `pagamentos.py:127`. Com inteiros, a comparação é `>=` exata.
- **Não** faça conversão dentro dos services. Só na fronteira (schema de request/response).
- **Não** misture: um campo é centavos **ou** reais, nunca "depende do contexto".
- **Não** use `float` como passo intermediário na conversão. `int(valor * 100)` perde um centavo em
  **4.586 dos 99.999** valores entre R$ 0,01 e R$ 999,99 (4,6% dos casos). Exemplos reais medidos:

  | Expressão | Resultado | Correto |
  |---|---|---|
  | `int(0.29 * 100)` | `28` | `29` |
  | `int(1.15 * 100)` | `114` | `115` |
  | `int(2.01 * 100)` | `200` | `201` |

  Por isso `reais_para_centavos` passa por `Decimal(str(valor))` antes de multiplicar.

### Critério de aceite

1. Nenhum campo monetário `float` nos modelos:
   ```bash
   cd backend && grep -rnE "valor.*: float|saldo.*: float" models/ | grep -v taxa
   # Esperado: nenhuma saída
   ```

2. Nenhum `round()` em `calculos.py`:
   ```bash
   grep -c "round(" backend/services/calculos.py
   # Esperado: 0
   ```

3. Teste novo `backend/tests/test_dinheiro.py` cobrindo, no mínimo:
   - `reais_para_centavos("100.50") == 10050`
   - `reais_para_centavos(0.1) + reais_para_centavos(0.2) == reais_para_centavos(0.3)`
   - `sum(dividir_centavos(10000_00, 12)) == 10000_00`
   - Para cada método de amortização: soma das amortizações == principal, exatamente.
   - Um empréstimo de R$ 10.000 em 12x a 2% a.m. fecha em centavos sem resíduo.

4. Suíte existente passando:
   ```bash
   cd backend && python -m pytest tests/ -q
   ```

---

## 1.4 Replica set e transações

**Severidade:** alta
**Esforço:** 1 dia

### Problema

O MongoDB roda como instância **standalone**. Nessa configuração, transação multi-documento é
**impossível** — não é "não usada", é indisponível. Confirmado: `grep -r start_transaction backend/`
retorna zero.

O registro de pagamento em `backend/routes/pagamentos.py` escreve, em sequência e sem atomicidade:

1. `pagamentos.insert_one`
2. `parcelas.find_one_and_update` (incrementa valor pago)
3. `parcelas.update_one` (define status)
4. `parcelas.insert` (gera próxima parcela, se empréstimo aberto)
5. `emprestimos.update_one` (marca quitado)
6. `auditoria.insert`
7. `scores_historico` (recálculo de score)

Se o processo cair entre os passos 1 e 3, fica um pagamento registrado com a parcela em aberto.

A prova de que isso já aconteceu são os scripts de reparo que existem no repositório:
`scripts/validar_integridade.py`, `scripts/corrigir_quitados_inconsistentes.py`,
`scripts/limpar_parcelas_duplicadas.py`.

### O que fazer

**Passo 1 — Converter o Mongo para replica set de 1 nó.**

Em `docker-compose.yml`, serviço `mongodb`:

```yaml
    command: ["mongod", "--replSet", "rs0", "--bind_ip_all"]
```

Inicializar uma única vez:

```bash
docker exec kredor_mongodb mongosh --quiet --eval \
  'rs.initiate({_id:"rs0", members:[{_id:0, host:"kredor_mongodb:27017"}]})'
```

Atualizar a `MONGO_URL` em `backend/.env`:

```
MONGO_URL=mongodb://kredor_mongodb:27017/kredor?replicaSet=rs0
```

Atualizar o healthcheck do serviço `mongodb` para verificar que o replica set está primário:

```yaml
      test: mongosh --quiet --eval 'rs.status().myState === 1' | grep -q true
```

> Replica set de 1 nó tem a mesma tolerância a falha de hardware que standalone (nenhuma). O ganho
> aqui é exclusivamente habilitar transações e change streams. Redundância real exige 3 nós e é
> assunto de outra etapa.

**Passo 2 — Envolver os caminhos de dinheiro em transação.**

Três fluxos, nesta ordem de prioridade:

1. `routes/pagamentos.py` → `registrar_pagamento`
2. `routes/pagamentos.py` → `estornar_pagamento`
3. `routes/emprestimos.py` → amortização e incorporação de juros

Padrão:

```python
async with await client.start_session() as sessao:
    async with sessao.start_transaction():
        await db.pagamentos.insert_one(doc, session=sessao)
        resultado = await db.parcelas.find_one_and_update(filtro, update, session=sessao)
        await db.emprestimos.update_one(filtro_emp, update_emp, session=sessao)
```

### O que NÃO fazer — leia com atenção

- **Toda** operação dentro do bloco `start_transaction()` precisa receber `session=sessao`.
  Uma operação sem o parâmetro executa **fora** da transação, silenciosamente, e você fica com
  atomicidade parcial — pior que não ter transação, porque parece que tem.
- **Não** coloque chamadas de rede (WhatsApp, e-mail, gateway de pagamento) dentro da transação.
  Transação segura locks. Enfileire o efeito colateral e dispare **depois** do commit.
- **Não** coloque o recálculo de score dentro da transação. Ele é derivado e pode ser reprocessado.
- **Não** aumente o escopo da transação "por segurança". Quanto menor, melhor.
- **Não** remova os scripts de reparo. Eles continuam úteis para dados legados.

### Critério de aceite

1. Replica set ativo:
   ```bash
   docker exec kredor_mongodb mongosh --quiet --eval 'rs.status().myState'
   # Esperado: 1
   ```

2. Transação funcional:
   ```bash
   docker exec kredor_backend python -c "
   import asyncio
   from config import client
   async def t():
       async with await client.start_session() as s:
           async with s.start_transaction():
               pass
       print('transacao ok')
   asyncio.run(t())"
   ```

3. Toda operação dentro de bloco transacional tem `session=`:
   ```bash
   cd backend && grep -A25 "start_transaction" routes/pagamentos.py | grep -E "await db\." | grep -v "session=" 
   # Esperado: nenhuma saída
   ```

4. Teste novo `backend/tests/test_transacao_pagamento.py`: simula falha no meio do fluxo (ex.:
   forçar exceção após o insert do pagamento) e verifica que **nada** foi persistido.

---

# FASE 1.5 — Correções da Fase 1

> Auditoria feita em **10/09/2026** sobre o commit `170fed7`, com o código rodando em produção na VPS.
> A Fase 1 foi entregue corretamente — a invariante central (`soma das amortizações == principal`)
> fecha em **2.700 de 2.700** combinações de principal × taxa × prazo testadas. Os itens abaixo são
> arestas encontradas nessa auditoria, não retrabalho.

## 1.5.1 Valores negativos em empréstimos pequenos

> ✅ **CONCLUÍDA em 10/09/2026** — 37 casos negativos → **0**, verificado independentemente sobre a
> grade de 2.700 combinações. Seção mantida como registro do bug.
>
> ⚠️ **O patch sugerido em "O que fazer" abaixo NÃO deve ser aplicado.** Ele estava errado: medido
> sobre 940 casos válidos, a proposta deste documento (dividir o total e derivar o principal)
> reintroduzia valor negativo em **18 casos**. A implementação escolhida pela equipe — dividir
> principal e juros separadamente — tem **zero** negativos. Ver a nota na
> [Linha de base](#linha-de-base).

**Severidade:** média
**Esforço:** meio dia

### Problema

Em empréstimos de **principal baixo com muitos períodos**, a última parcela recebe juros ou
amortização **negativos**. Medido com teste de propriedade sobre 2.700 casos: 37 produzem negativo.

Faixa afetada (medida):

| Principal | Casos com negativo |
|---|---:|
| R$ 0,50 | 11 |
| R$ 0,99 | 14 |
| R$ 1,00 | 10 |
| R$ 5,00 | 6 |
| R$ 10,00 | 2 |
| **R$ 50,00** | 6 |
| R$ 100,00 e acima | **0** |

Casos concretos reproduzíveis:

```
R$ 0,99 em 6x a 0,5% (juros simples, parcelas fixas):
  parcela 1: principal= 16  juros= 1  total= 17
  ...
  parcela 6: principal= 19  juros=-2  total= 17     <-- juros NEGATIVO

R$ 0,99 em 36x a 0,01% (Tabela Price):
  parcela 34: principal=  3  juros=0  saldo=0
  parcela 35: principal=  3  juros=0  saldo=0
  parcela 36: principal= -6  juros=0  saldo=0       <-- amortização NEGATIVA
```

### Duas causas distintas

**a) `_plano_parcelas_fixas` em `services/calculos.py`** divide `valor_total` e `principal`
**independentemente**, e cada `dividir_centavos` joga o próprio resto na última parcela. Quando os
dois restos divergem, `juros = totais[i] - principais[i]` fica negativo:

```python
totais     = dividir_centavos(valor_total, periodos)   # 102 em 6x -> [17,17,17,17,17,17]
principais = dividir_centavos(principal, periodos)     #  99 em 6x -> [16,16,16,16,16,19]
# juros da última = 17 - 19 = -2
```

**b) `calcular_tabela_price`** quando o `pmt` arredondado amortiza o saldo até zero **antes** do
último período. Nas parcelas restantes o saldo já é zero, `pmt - juros` continua positivo, o saldo
fica negativo, e a última parcela (`amortizacao = saldo`) herda o negativo acumulado.

### O que fazer

**Para (a)** — derive os juros do total, não divida os dois em paralelo:

```python
def _plano_parcelas_fixas(principal: int, valor_total: int, periodos: int) -> List[dict]:
    """Parcelas iguais: divide o TOTAL, e o principal de cada parcela sai do total menos os juros."""
    totais = dividir_centavos(valor_total, periodos)
    juros_total = valor_total - principal
    juros = dividir_centavos(juros_total, periodos)
    saldo = valor_total
    plano = []
    for i in range(periodos):
        saldo -= totais[i]
        plano.append(_parcela(i + 1, totais[i] - juros[i], juros[i], saldo))
    return plano
```

Assim `sum(juros) == juros_total` e `sum(principal) == principal` continuam exatos, e nenhum dos dois
pode ficar negativo (porque `juros_total >= 0` e `totais[i] >= juros[i]` quando o principal é válido).

**Para (b)** — pare de amortizar quando o saldo zerar:

```python
    for i in range(meses):
        juros = arredondar_centavos(saldo * taxa)
        if i == meses - 1:
            amortizacao = saldo
        else:
            amortizacao = min(pmt - juros, saldo)   # nunca amortiza mais que o saldo
        saldo -= amortizacao
```

**Para os dois** — valide a entrada. Um empréstimo não pode ter menos de 1 centavo de amortização
por período. Em `routes/emprestimos.py`, na criação e na simulação:

```python
if valor_principal_centavos < periodos:
    raise HTTPException(
        status_code=422,
        detail=f"Principal de R$ {valor_principal_centavos/100:.2f} não pode ser dividido em "
               f"{periodos} parcelas (mínimo de 1 centavo por parcela)."
    )
```

### O que NÃO fazer

- **Não** resolva com `max(0, valor)`. Isso esconde o problema e quebra a invariante da soma —
  o centavo desaparece e a soma deixa de fechar com o principal.
- **Não** trate como caso impossível. Este produto é de empréstimo informal; valores baixos
  acontecem. E mesmo que não acontecessem, a falha hoje é **silenciosa** (dinheiro negativo salvo no
  banco), não um erro visível.

### Critério de aceite

Adicione este teste em `tests/test_dinheiro.py`. Ele é o mesmo que encontrou o bug — **hoje ele
falha**; a tarefa está pronta quando passar.

```python
"""Propriedades dos métodos de amortização sobre a grade inteira de entradas."""
import pytest

from services.calculos import (
    calcular_juros_simples,
    calcular_sac,
    calcular_tabela_price,
    _plano_parcelas_fixas,
)

PRINCIPAIS = [1, 50, 99, 100, 500, 1000, 5000, 10_000, 100_000, 1_000_000, 99_999_999]
TAXAS = [0.0, 0.01, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
PRAZOS = [1, 2, 3, 6, 12, 24, 36, 60, 120, 360]

VALIDOS = [
    (p, t, n)
    for p in PRINCIPAIS
    for t in TAXAS
    for n in PRAZOS
    if p >= n  # precisa de pelo menos 1 centavo de amortização por parcela
]


def _conferir(parcelas: list[dict], principal: int, contexto: str) -> None:
    soma_principal = sum(x["valor_principal_centavos"] for x in parcelas)
    assert soma_principal == principal, (
        f"{contexto}: soma das amortizações {soma_principal} != principal {principal}"
    )
    for x in parcelas:
        assert x["valor_principal_centavos"] >= 0, f"{contexto}: amortização negativa em {x}"
        assert x["valor_juros_centavos"] >= 0, f"{contexto}: juros negativos em {x}"

    saldos = [x["saldo_devedor_centavos"] for x in parcelas]
    for i in range(1, len(saldos)):
        assert saldos[i] <= saldos[i - 1], f"{contexto}: saldo devedor cresceu — {saldos}"


@pytest.mark.parametrize("principal,taxa,prazo", VALIDOS)
def test_price_fecha_e_nao_fica_negativo(principal, taxa, prazo):
    _conferir(
        calcular_tabela_price(principal, taxa, prazo, 0),
        principal,
        f"price(p={principal}, t={taxa}, n={prazo})",
    )


@pytest.mark.parametrize("principal,taxa,prazo", VALIDOS)
def test_sac_fecha_e_nao_fica_negativo(principal, taxa, prazo):
    _conferir(
        calcular_sac(principal, taxa, prazo, 0),
        principal,
        f"sac(p={principal}, t={taxa}, n={prazo})",
    )


@pytest.mark.parametrize("principal,taxa,prazo", VALIDOS)
def test_parcelas_fixas_fecham_e_nao_ficam_negativas(principal, taxa, prazo):
    total, _ = calcular_juros_simples(principal, taxa, prazo)
    parcelas = _plano_parcelas_fixas(principal, total, prazo)
    contexto = f"fixas(p={principal}, t={taxa}, n={prazo})"
    _conferir(parcelas, principal, contexto)
    soma_total = sum(x["valor_total_centavos"] for x in parcelas)
    assert soma_total == total, f"{contexto}: soma dos totais {soma_total} != total {total}"
```

E, para as combinações **inválidas** (`principal < prazo`), um teste de que a API responde **422** —
não que ela calcula algo estranho.

Rodar:

```bash
cd /var/www/kredor
docker run --rm --network kredor_network --env-file backend/.env \
  -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' -e DB_NAME=kredor_test \
  -v /var/www/kredor/backend:/app -w /app --entrypoint python kredor-backend \
  -m pytest tests/test_dinheiro.py -q -p no:cacheprovider
# Esperado ao final da tarefa: 0 failed
```

> Referência de onde partimos: na auditoria de 10/09/2026 este teste acusou **37 falhas** em 2.700
> casos, todas de valor negativo — e **zero** falhas de soma. A invariante da soma já está correta;
> não a quebre ao corrigir os negativos.

---

## 1.5.2 `transacao()` degrada em silêncio

**Severidade:** média
**Esforço:** 1 hora

### Problema

`backend/utils/transacao.py` detecta se o servidor suporta transação e, em instância standalone,
abre só a sessão e segue **sem atomicidade** — sem log, sem aviso, sem nada:

```python
async with await client.start_session() as sessao:
    if await servidor_suporta_transacao():
        async with sessao.start_transaction():
            yield sessao
    else:
        yield sessao          # <- roda sem atomicidade, calado
```

A degradação graciosa é uma decisão de design defensável (permite rodar testes e dev em standalone).
O problema é o **silêncio**: se alguém subir em produção com Mongo standalone — ou se o
`?replicaSet=rs0` cair da `MONGO_URL` num deploy — o sistema roda achando que tem atomicidade e não
tem. Nada no log denuncia.

### O que fazer

1. Logar `warning` uma vez por processo, na primeira detecção:

```python
if not _suporta_transacao:
    logger.warning(
        "MongoDB sem replica set: caminhos de dinheiro rodando SEM atomicidade",
        data={"mongo_url_tem_replica_set": "replicaSet" in MONGO_URL},
    )
```

2. Em produção, **falhar** em vez de degradar:

```python
if not await servidor_suporta_transacao():
    if ENVIRONMENT == "production":
        raise RuntimeError(
            "Transações indisponíveis: MongoDB não está em replica set. "
            "Em produção os caminhos de dinheiro exigem atomicidade."
        )
```

### O que NÃO fazer

- Não remova a degradação em dev/teste. Ela é útil e os testes dependem dela (3 testes de
  `test_transacao_pagamento.py` são skipped quando não há replica set).

### Critério de aceite

```bash
# Em produção, sem replica set, tem que estourar:
docker exec -e ENVIRONMENT=production \
  -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor' kredor_backend \
  python -c "
import asyncio
from utils.transacao import transacao
async def t():
    async with transacao():
        pass
asyncio.run(t())" 2>&1 | tail -1
# Esperado: RuntimeError: Transações indisponíveis...
```

---

## 1.5.3 `pytest-asyncio` ausente — testes que não rodam

**Severidade:** média
**Esforço:** 1 hora

### Problema

`backend/requirements.txt` tem `pytest` e `pytest-xdist`, mas **não tem `pytest-asyncio`**.

Os 3 testes marcados com `@pytest.mark.asyncio` em `tests/test_race_condition_parcelas.py`
**não executam**. O pytest emite apenas um warning e segue:

```
PytestUnknownMarkWarning: Unknown pytest.mark.asyncio - is this a typo?
```

São justamente os testes de condição de corrida na geração de parcelas — cobertura falsa.

### O que fazer

1. Adicionar ao `requirements.txt`: `pytest-asyncio==0.24.0` (ou versão compatível com pytest 9).
2. Criar `backend/pytest.ini` (ou `pyproject.toml`) registrando o modo:
   ```ini
   [pytest]
   asyncio_mode = auto
   ```
3. Rodar os 3 testes e **conferir que passam de verdade**. Se algum falhar, é bug real que estava
   escondido — corrija antes de fechar a tarefa.

### Critério de aceite

```bash
cd backend && python3 -c "print(open('requirements.txt').read().count('pytest-asyncio'))"   # 1

# E os testes têm que RODAR (não "skipped", não warning de mark desconhecida):
docker run --rm --network kredor_network --env-file backend/.env \
  -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' -e DB_NAME=kredor_test \
  -v /var/www/kredor/backend:/app -w /app --entrypoint python kredor-backend \
  -m pytest tests/test_race_condition_parcelas.py -v -p no:cacheprovider 2>&1 | grep -c PASSED
# Esperado: >= 3, e nenhum PytestUnknownMarkWarning na saída
```

---

## 1.5.4 Ponto cego do checker de `session=`

**Severidade:** baixa
**Esforço:** 2 horas

### Problema

`backend/scripts/checar_session_em_transacao.py` é bem feito (AST, entende cadeia
`db.x.find(...).to_list()`), mas só detecta `await db.*` **escrito diretamente** no bloco
`async with transacao()`.

Ele **não vê** uma função chamada dentro do bloco que faça acesso ao banco por dentro. Hoje o único
caso desses está correto — `inserir_parcela_juros_aberto(..., session=sessao)` aceita e recebe a
sessão, e `recalcular_status_emprestimo` roda deliberadamente **fora** da transação (indentação 4,
com comentário explicando que é efeito derivado). Auditei os dois: estão certos.

O risco é de **regressão**: quem adicionar amanhã uma chamada de service dentro do bloco sem
propagar a sessão passa pelo checker sem alarme, e a operação roda fora da transação em silêncio.

### O que fazer

Estender o checker para, dentro de um bloco `async with transacao()`, listar **toda chamada de
função** que não seja `db.*` e verificar se ela recebe `session=`. Para as que não recebem, exigir
que estejam numa allowlist explícita no topo do script:

```python
# Funções que podem ser chamadas dentro de um bloco transacional SEM session=
# porque não tocam o banco, ou porque são efeito derivado intencional.
PERMITIDAS_SEM_SESSION = {
    "logger.info", "logger.warning", "arredondar_centavos", "dividir_centavos",
    # ...
}
```

Assim, adicionar uma chamada nova dentro da transação obriga uma decisão consciente: ou propaga a
sessão, ou entra na allowlist com justificativa.

### Critério de aceite

```bash
cd backend && python3 scripts/checar_session_em_transacao.py routes/*.py services/*.py
# Esperado: exit 0, e a saída deve reportar também as chamadas de função verificadas
```

Teste negativo: adicione temporariamente uma chamada de service sem `session=` dentro de um bloco
transacional e confirme que o checker **acusa**. Depois remova.

---

## 1.5.5 Build Docker do frontend quebrado (Node 18 vs yarn.lock)

**Severidade:** alta (bloqueia qualquer build limpo do repositório)
**Esforço:** 5 minutos

### Problema

O commit `170fed7` ("chore: atualizar lock do frontend") adicionou `frontend/yarn.lock`, que fixa
`react-router-dom@7.18.3`. Esse pacote declara `engines: {"node": ">=20.0.0"}`.

O `frontend/Dockerfile` usa `FROM node:18-alpine`. O build falha:

```
error react-router-dom@7.18.3: The engine "node" is incompatible with this module.
Expected version ">=20.0.0". Got "18.20.8"
error Found incompatible module.
```

Antes do lockfile existir, o Dockerfile caía no ramo `npm install --legacy-peer-deps`, que ignora a
restrição de engine. Com o lockfile, o ramo passa a ser `yarn install --frozen-lockfile`, que a
respeita. O ambiente `iniciar.sh` roda Node 20+, então isso não aparece por lá — só no Docker.

### O que fazer

Em `frontend/Dockerfile`:

```dockerfile
# Node 20: o yarn.lock fixa react-router-dom@7, que exige engine ">=20.0.0".
# Com node:18 o `yarn install --frozen-lockfile` falha com "Found incompatible module".
FROM node:20-alpine AS builder
```

Já aplicado na VPS (`/var/www/kredor/frontend/Dockerfile`) para desbloquear o deploy — mas **precisa
ir para o repositório**, senão volta a quebrar no próximo clone limpo.

### O que NÃO fazer

- **Não** use `yarn install --ignore-engines`. Isso mascara a incompatibilidade e instala um pacote
  em runtime que ele mesmo declara não suportar.
- **Não** volte o `react-router-dom` para a v6 só para manter o Node 18. Node 18 saiu de suporte em
  abril de 2025; a direção certa é subir o Node.

### Critério de aceite

```bash
cd /var/www/kredor && docker compose build frontend > /tmp/fe.log 2>&1; echo "exit=$?"
# Esperado: exit=0
```

> **Cuidado ao verificar:** `docker compose build | tail -50` devolve o exit code do `tail`, não do
> build — um build que falhou aparece como sucesso. Redirecione para arquivo e leia `$?`, como acima.

---

# FASE 2 — Operabilidade

## 2.1 Logging estruturado

**Severidade:** média
**Esforço:** 1 dia

### Problema

**289** chamadas de `print()` no código de aplicação (medido em 10/09/2026). Já existe um
`services/logging_service.py` com log estruturado em JSON — e ele é ignorado na maioria dos casos.

Com 2 workers gunicorn, `print(f"✅ Parcela #{n} gerada")` sai no stdout sem timestamp, sem nível,
sem `usuario_id` e sem forma de correlacionar com a requisição que o originou.

Concentração — atacar nesta ordem resolve mais da metade:

| Arquivo | `print()` |
|---|---:|
| `routes/assinaturas.py` | **60** |
| `jobs/notificacoes_job.py` | 24 |
| `services/two_factor_service.py` | 17 |
| `jobs/email_jobs.py` | 15 |
| `jobs/emprestimos_abertos_job.py` | 14 |
| `routes/auth.py` | 12 |
| (demais, espalhados) | 147 |

Remedir a concentração a qualquer momento:

```bash
cd backend && grep -rc "print(" routes/*.py services/*.py jobs/*.py \
  | grep -v ":0" | sort -t: -k2 -rn | head -10
```

### O que fazer

1. Substituir os `print()` em `routes/`, `services/` e `jobs/` por `logger` com nível adequado:
   - `logger.debug` — detalhe de diagnóstico
   - `logger.info` — evento de negócio concluído
   - `logger.warning` — situação anômala recuperável
   - `logger.error` — falha que exigiu abortar a operação

2. Sempre passar contexto:
   ```python
   logger.info("Parcela gerada automaticamente",
               data={"usuario_id": usuario_id, "emprestimo_id": emp_id, "numero": n})
   ```

3. Adicionar middleware de correlação em `main.py`: gerar um `request_id` (UUID) por requisição,
   colocar em `contextvars`, e o `logging_service` inclui automaticamente em todo log.

### O que NÃO fazer

- Não troque `print` por `logger.info` cegamente em massa. Avalie o nível de cada um. Mensagem de
  diagnóstico de loop vira `debug`, não `info`.
- Não logue dados sensíveis: senha, token, CPF completo, chave de API. CPF pode ser mascarado.
- Não remova as mensagens. Converta. Elas têm valor de diagnóstico.

### Critério de aceite

```bash
cd backend && grep -rn "print(" routes/ services/ jobs/ | wc -l
# Esperado: 0
```

E uma requisição real deve produzir logs com o mesmo `request_id`:

```bash
curl -s https://kredor.com.br/api/timezone-info > /dev/null
docker compose logs backend --tail=20 | grep request_id
```

---

## 2.2 Datas como Date do BSON

**Severidade:** média
**Esforço:** 2 dias

### Problema

**352** chamadas `.isoformat()` antes de inserir no Mongo (medido em 10/09/2026). As datas são
gravadas como **string**, não como `Date`. As comparações de intervalo funcionam por acidente —
ISO-8601 em UTC ordena lexicograficamente igual à ordem cronológica.

Quebra no momento em que entrar uma string com offset diferente (`-03:00` contra `Z`) ou um objeto
`Date` real misturado na mesma coleção.

Detalhe importante: os **modelos Pydantic já usam `datetime`** (`Parcela.data_vencimento: datetime`).
O problema é só na camada de escrita, que converte para string antes do `insert`. Ou seja, o tipo
correto já está declarado — falta parar de destruí-lo na gravação. Exceção a corrigir junto:
`ParcelaSimulacao.data_vencimento: str` em `models/emprestimo.py:32` está declarado como string.

Já existe parsing defensivo por causa disso, em `services/juros_mora_service.py:20-24` — o código
precisa checar o tipo em tempo de execução porque **não pode confiar no formato**:

```python
data_vencimento = parcela.get("data_vencimento")
if isinstance(data_vencimento, str):
    data_vencimento = datetime.fromisoformat(data_vencimento.replace('Z', '+00:00'))
data_venc_date = data_vencimento.date() if isinstance(data_vencimento, datetime) else data_vencimento
```

Esses `isinstance` são a assinatura do problema: a coleção **já tem tipos mistos**. Quando a tarefa
estiver concluída, essas checagens podem ser apagadas.

Além disso, com string você perde `$dateTrunc`, `$dateDiff` e agregação por período, e os índices
ficam maiores.

### O que fazer

1. Gravar `datetime` com timezone UTC diretamente. O driver converte para `Date` do BSON.
   ```python
   # ERRADO
   doc["data_vencimento"] = data.isoformat()
   # CERTO
   doc["data_vencimento"] = data.astimezone(timezone.utc)
   ```

2. Nas queries de intervalo, comparar com `datetime`, não com string:
   ```python
   {"data_vencimento": {"$lt": datetime.now(timezone.utc)}}
   ```

3. Converter para string **só na serialização da resposta** (o Pydantic já faz isso).

4. Escrever `backend/scripts/migrar_datas_para_bson.py`, idempotente, em lotes com `bulk_write`,
   convertendo os campos de data existentes de string para `Date`.

Campos afetados: `data_vencimento`, `data_pagamento`, `created_at`, `updated_at`, `data_inicio`,
`deleted_at`, `criado_em`, `expira_em`, `executado_em`, `data_acao`.

### O que NÃO fazer

- Não faça a migração de dados e a mudança de código em commits separados sem coordenar o deploy.
  Durante a janela, a coleção terá tipos mistos e as queries de intervalo vão retornar resultado
  errado. Ordem correta: deploy do código que **lê os dois formatos** → migração dos dados →
  deploy do código que **só escreve `Date`**.
- Não use `datetime.utcnow()` — ele retorna datetime *naive* (sem timezone) e é depreciado desde o
  Python 3.12. Use `datetime.now(timezone.utc)`. Há **35 ocorrências** hoje, concentradas em
  `routes/scheduler_admin.py` (padrão `datetime.utcnow().isoformat()`, que junta os dois problemas).
  Localize com:
  ```bash
  cd backend && grep -rn "utcnow()" routes/ services/ jobs/
  ```
  Misturar *naive* e *aware* é especialmente perigoso aqui: comparar os dois em Python levanta
  `TypeError`, e gravado no Mongo o *naive* é interpretado como UTC sem aviso.
- Não misture `now_sp()` e `now_utc()` no mesmo campo. Armazene sempre UTC; converta para
  America/Sao_Paulo apenas na apresentação.

### Critério de aceite

```bash
docker exec kredor_mongodb mongosh kredor --quiet --eval '
const campos = ["data_vencimento","created_at","data_pagamento"];
let erros = 0;
db.parcelas.find().limit(500).forEach(d => {
  campos.forEach(c => { if (d[c] !== undefined && !(d[c] instanceof Date)) erros++; });
});
print("campos de data que não são Date: " + erros);'
# Esperado: 0
```

---

## 2.3 Eliminar consultas dentro de laço (N+1)

**Severidade:** média-alta · **Esforço:** 2 dias · **Estado medido em 13/09/2026:** **35 em 14
arquivos** (eram 48 em 17; a rodada de 11/09 resolveu `analise.py` 4→0 e `emprestimos.py` 8→2)

> **Alinhamento em 13/09/2026.** O critério anterior era **binário** ("TOTAL: 0") sobre 35
> ocorrências em arquivos independentes — o mesmo defeito de especificação já corrigido na 3.5(d):
> resolver 30 de 35 dava o mesmo resultado que resolver nenhuma. Agora é **contagem decrescente**,
> um arquivo por commit. E há laço em que buscar em lote não agrega nada: o detector passou a
> aceitar justificativa declarada no código.

**Medição (única fonte de verdade — as linhas mudam a cada commit, gere a lista, não confie na
tabela):**

```bash
cd backend && python3 scripts/checar_query_em_laco.py routes/*.py services/*.py jobs/*.py \
  | grep -v ": 0 query"
# TOTAL: 35 não justificada(s), 0 justificada(s)
```

**Estado por arquivo (13/09/2026):**

| Arquivo | Qtd | Natureza |
|---|---:|---|
| `services/notificacao_service.py` | 5 | checagem de duplicidade por notificação + empréstimo/cliente por item |
| `jobs/emprestimos_abertos_job.py` | 4 | 4 queries por empréstimo aberto, no job diário |
| `routes/whatsapp.py` | 4 | cliente por log (linha 81) e 3 queries por conexão |
| `services/regua_cobranca_service.py` | 4 | **já tem cache** (`emp_cache`/`cli_cache`); o que resta é dedup e log por mensagem |
| `services/plano_service.py` | 3 | usuário por item; transação e assinatura por item |
| `jobs/email_jobs.py` | 2 | `update_one` por usuário em dois laços |
| `routes/emprestimos.py` | 2 | `update_one` por parcela na incorporação de juros (linhas 2663, 2677) |
| `routes/parcelas.py` | 2 | `count_documents` por parcela (130) e `update_one` por parcela (178) |
| `routes/superadmin.py` | 2 | usuário por item; assinaturas por item |
| `routes/whatsapp_templates.py` | 2 | laço sobre a **lista fixa** de templates padrão |
| `services/carteira_service.py` | 2 | laço sobre a **tabela fixa** de preços |
| `routes/clientes.py` | 1 | `portal_auth` por cliente na listagem |
| `jobs/inadimplencia_job.py` | 1 | cliente por empréstimo inadimplente |
| `jobs/resumo_whatsapp_job.py` | 1 | usuário por item |

**Ordem de trabalho (impacto decrescente, um arquivo por commit):** `notificacao_service.py`,
`emprestimos_abertos_job.py`, `whatsapp.py`, `clientes.py`, `parcelas.py`, `plano_service.py`,
`email_jobs.py`, `inadimplencia_job.py`, `resumo_whatsapp_job.py`, `superadmin.py`,
`emprestimos.py`, `regua_cobranca_service.py`. Os dois de lista fixa
(`whatsapp_templates.py`, `carteira_service.py`) são caso de justificativa, não de conversão.

### O que fazer

Três padrões, nesta ordem de preferência:

**a) Buscar em lote e montar dicionário** — serve para a maioria. `routes/dashboard.py` já faz
certo (`clientes_map`); use como referência.

```python
# ERRADO — uma query por item
for p in parcelas:
    cliente = await db.clientes.find_one({"id": p["cliente_id"]})

# CERTO — uma query para todos
ids = {p["cliente_id"] for p in parcelas}
docs = await db.clientes.find({"id": {"$in": list(ids)}, "usuario_id": usuario_id}).to_list(len(ids))
clientes = {c["id"]: c for c in docs}
for p in parcelas:
    cliente = clientes.get(p["cliente_id"])
```

**b) Escrita em lote** — para `insert_one`/`update_one` dentro de laço. `insert_many` quando os
documentos são novos; `bulk_write` com `UpdateOne` quando o update difere por documento.

```python
from pymongo import UpdateOne
operacoes = [UpdateOne({"id": p["id"]}, {"$set": {...}}) for p in parcelas]
if operacoes:
    await db.parcelas.bulk_write(operacoes, session=sessao)
```

> **`bulk_write` aceita `session=`.** Na rodada de 11/09 duas ocorrências de `emprestimos.py`
> ficaram de fora com a justificativa "está dentro de transação". **Essa justificativa não
> procede** e não será aceita: passe a sessão como em qualquer outra operação. A regra da R2
> (toda operação dentro de `async with transacao()` leva `session=`) continua valendo e é
> verificada por `scripts/checar_session_em_transacao.py`.

**c) `$lookup` na agregação** — só quando o join precisa acontecer antes de filtrar ou ordenar.

**Checagem de duplicidade em laço** (`notificacao_service.py`, `regua_cobranca_service.py`) resolve
carregando as chaves já existentes **uma vez** antes do laço e comparando em memória:

```python
chaves = {(n["emprestimo_id"], n["tipo"]) async for n in db.notificacoes.find(
    {"usuario_id": usuario_id, "tipo": {"$in": tipos}}, {"emprestimo_id": 1, "tipo": 1, "_id": 0})}
```

Atenção: isso muda a garantia contra corrida. Onde existe índice único protegendo o duplicado,
mantenha o `insert_many(..., ordered=False)` tratando `BulkWriteError` de chave duplicada em vez
de checar antes.

### Quando o laço não precisa virar lote

Laço que percorre **lista fixa escrita no código** (seed de templates padrão, tabela de preços):
N é constante e pequeno, e `bulk_write` só adiciona complexidade. Nesses casos escreva

```python
# lote-nao-se-aplica: tabela de preços fixa no código, N constante
for tipo, valor in PRECOS_PADRAO.items():
```

na linha do laço (cobre todas as queries dele), na linha da query ou logo acima dela. O detector
tira da contagem que reprova e mostra em "justificada(s)", com o motivo visível no código.

**Não** use justificativa em laço que percorre coleção do banco — ali o N cresce com o uso e é N+1
de verdade. São esperadas **no máximo 4 justificativas** (os dois arquivos de lista fixa); qualquer
uma além disso precisa vir explicada no relatório.

### O que NÃO fazer

- Não adicione cache para esconder a lentidão. Corrija a query.
- Não use `$lookup` como primeira opção.
- Não coloque `insert_many` com centenas de documentos numa transação sem avaliar o limite de 16 MB
  por operação; para lotes grandes, quebre em blocos de 1000.
- Não troque o comportamento junto: esta tarefa é só sobre **quantas** queries são feitas, não sobre
  **o que** o código decide. Se durante o trabalho aparecer um defeito de lógica, relate em vez de
  corrigir no mesmo commit.

### Critério de aceite

- `python3 scripts/checar_query_em_laco.py routes/*.py services/*.py jobs/*.py` →
  **`TOTAL: 0 não justificada(s)`**, com no máximo 4 justificadas. Contagem decrescente: cada commit
  baixa o número de pelo menos um arquivo e **nunca sobe** o de outro.
- `python3 scripts/checar_session_em_transacao.py` → 0 problemas.
- `python3 -m flake8 --select=F routes services jobs` → sem achado novo (hoje há 2 pré-existentes
  em `routes/pagamentos.py`).
- Suíte completa sem regressão: **2.945 passando** hoje. Cole o total antes e depois.
- Para cada arquivo tocado que tenha E2E correspondente (`tests/e2e_*.py`), rode e cole a saída:
  `e2e_painel_imputacao.py`, `e2e_pagamento_na_data.py`, `e2e_quitar_com_desconto.py`,
  `e2e_recibo_parcial.py`, `e2e_backup_restore.py`.
- Um arquivo por commit, na ordem da tabela acima.

## 2.10 Cobrança automática cobra o valor errado e persegue centavos

**Severidade:** alta (mensagem vai para o cliente final) · **Esforço:** algumas horas · **Risco:**
baixo em código, **alto em imagem** — o que sai daqui chega no WhatsApp do cliente

### Problema

`services/regua_cobranca_service.py`, no laço que decide os envios:

```python
valor_devido = (parc.get("valor_total_centavos", 0) or 0) - (parc.get("valor_pago_centavos", 0) or 0)
if valor_devido <= 0:
    continue
```

Dois defeitos, medidos em 13/09/2026:

1. **Ignora multa e juros de mora.** Todo o resto do sistema (painel, portal do cliente, relatório
   de inadimplência, recibo, registro de pagamento) usa `saldo_devedor_parcela()`, que é
   `total + multa + mora − pago − perdoado`. A régua é o único lugar que cobra só `total − pago`:
   numa parcela em atraso, **a mensagem pede menos do que o cliente deve**. Também ignora o perdão
   da quitação com desconto (embora hoje a parcela perdoada saia por status `pago`).
2. **Não tem piso.** Só descarta `valor_devido <= 0`. Uma parcela paga a menos por arredondamento
   dispara cobrança por **R$ 0,13** no WhatsApp do cliente. Caso real: as 8 parcelas de maio/junho
   quitadas com centavos a menos (ver seção de auditoria de 12/09/2026).

### O que fazer

1. **Trocar o cálculo pela fonte única:** `saldo_devedor_parcela(parc)` de
   `services/parcela_service`. Uma linha, mais o import. Isso corrige multa, mora e perdão de uma
   vez, e faz a régua concordar com o número que o credor vê na tela.

2. **Piso configurável, só para sobra de pagamento parcial:**

   ```python
   minimo = cfg.get("valor_minimo_centavos") or 0
   if (parc.get("valor_pago_centavos") or 0) > 0 and valor_devido < minimo:
       continue
   ```

   > **Por que o piso vale só quando houve pagamento parcial:** um piso geral silenciaria parcela
   > legítima de valor pequeno — empréstimo aberto de R$ 100 a 3% tem parcela de juros de R$ 3,00,
   > e ela **deve** ser cobrada. O que não deve virar mensagem é a **sobra** de uma parcela que o
   > cliente já pagou (os centavos do arredondamento). A condição `valor_pago > 0` separa os dois.

3. **Campo novo na configuração da régua**, com padrão **R$ 5,00**:
   - `DEFAULT_CONFIG` em `regua_cobranca_service.py`: `"valor_minimo_centavos": 500`
   - `CAMPOS_PERMITIDOS` já é derivado de `DEFAULT_CONFIG` — nada a fazer.
   - `salvar_config`: coerção do campo para `int` com piso 0 (junto das que já existem para
     `lembrete_dias_antes`/`atraso_dias`).
   - **`routes/regua_cobranca.py` hoje recebe `dados: dict`**, sem modelo. Troque por um modelo
     Pydantic baseado em `EntradaEmReais` (`utils/dinheiro`), para o frontend mandar **reais** e o
     backend guardar **centavos**, como no resto do sistema (R6). Na saída a conversão já acontece
     pelo `ReaisJSONResponse`, então hoje a rota é assimétrica: devolve reais e aceita cru.
   - **Armadilha:** `salvar_config` faz `cfg = {**DEFAULT_CONFIG, **limpo}` — campo que não vier no
     PUT **volta ao padrão**, não é preservado. Por isso a tela é obrigatória, não opcional:
     `frontend/src/pages/ReguaCobranca.js` (225 linhas) manda o objeto inteiro
     (`{...config, ...patch}`), então o campo precisa aparecer lá ou será zerado a cada salvamento.

4. **Campo de valor mínimo na tela** `ReguaCobranca.js`, em reais, com `data-testid`
   `regua-valor-minimo`, e texto curto explicando: "Não cobrar sobras menores que este valor
   (evita cobrar centavos de quem já pagou a parcela)".

5. **Dois marcadores novos no template**, sem mudar os textos padrão (usuário pode ter
   personalizado): `{valor_parcela}` (só a parcela) e `{encargos}` (multa + mora). Agora que
   `{valor}` inclui os acréscimos, quem quiser pode detalhar a cobrança.

### O que NÃO fazer

- **NUNCA rode `POST /api/regua/executar` contra dados reais para testar.** Ele enfileira e envia
  WhatsApp de verdade para clientes de verdade. O aceite é por teste unitário.
- Não mexa no anti-spam, no horário comercial, na fila nem na deduplicação (`regua_envios`).
- Não altere os textos padrão de `TEMPLATES_PADRAO`.
- Não resolva o N+1 deste arquivo aqui (é a tarefa 2.3, e este arquivo é o último dela).

### Critério de aceite

- **Teste unitário novo** `backend/tests/test_regua_valor_devido.py` — hoje **não existe nenhum
  teste da régua**. Cobrir, no mínimo:
  - parcela em atraso: valor cobrado = `total + multa + mora − pago` (não `total − pago`);
  - sobra de R$ 0,13 em parcela com `valor_pago > 0`: **não** entra na cobrança com o padrão de
    R$ 5,00;
  - parcela de R$ 3,00 nunca paga (`valor_pago = 0`): **entra** na cobrança;
  - `valor_minimo_centavos = 0` volta ao comportamento antigo (sem piso);
  - parcela quitada com desconto (`perdao_*` gravado, status `pago`) não entra.
- `salvar_config` com `valor_minimo` em reais grava centavos; `get_config` devolve reais.
- `python3 scripts/checar_session_em_transacao.py` → 0 problemas.
- `python3 -m flake8 --select=F routes services jobs` → nenhum achado novo.
- Suíte completa sem regressão (cole o total antes e depois).
- `yarn build` exit 0 e `diff` dos `data-testid` mostrando **só** o novo `regua-valor-minimo`.

## 2.4 `exc_info=True` quebra o log de erro

**Severidade:** alta
**Esforço:** 30 minutos
**Origem:** regressão introduzida pela própria tarefa 2.1.

### Problema

A conversão dos `print()` para `logger` trocou `print(traceback.format_exc())` por
`logger.error("Traceback do erro", exc_info=True)`. Mas o `_log` de
`services/logging_service.py:139` repassa o valor cru para `makeRecord`:

```python
exc_info = kwargs.pop("exc_info", None)
record = self.logger.makeRecord(
    self.logger.name, level, "", 0, message, (), exc_info   # <- espera tupla, recebe True
)
```

`makeRecord` espera `None` ou a tupla `(tipo, valor, traceback)`. Recebendo o booleano `True`, o
formatter estoura ao tentar formatar a exceção. Reproduzido:

```
--- Logging error ---
Traceback (most recent call last):
  File "<string>", line 6, in <module>
ZeroDivisionError: division by zero

During handling of the above exception, another exception occurred:
  File "/usr/local/lib/python3.11/logging/__init__.py", line 1110, in emit
    msg = self.format(record)
```

O `logging` do Python engole o erro do handler e imprime `--- Logging error ---` no stderr, então a
aplicação **não quebra** — mas **o traceback é perdido**. É o pior lugar possível para uma falha
silenciosa: justamente o log que diria o que deu errado.

São **6 pontos** em 5 arquivos:

```bash
cd backend && grep -rn "exc_info=True" . --include="*.py"
```

`jobs/emprestimos_abertos_job.py`, `jobs/inadimplencia_job.py`, `jobs/notificacoes_job.py`,
`jobs/relatorio_semanal.py`, `routes/assinaturas.py` (2x).

### O que fazer

Normalizar no `_log`, que resolve os 6 call sites de uma vez:

```python
def _log(self, level: int, message: str, **kwargs):
    extra_data = kwargs.pop("data", None)
    exc_info = kwargs.pop("exc_info", None)
    if exc_info is True:
        exc_info = sys.exc_info()          # makeRecord exige tupla, não booleano
    ...
```

Note que o método `exception()` da mesma classe já faz isso certo
(`kwargs["exc_info"] = sys.exc_info()`) — a correção só alinha `error(exc_info=True)` ao mesmo
comportamento.

### O que NÃO fazer

- Não troque os 6 call sites por `logger.exception(...)` sem corrigir o `_log`. Resolve os 6 de hoje
  e deixa a armadilha armada para o próximo `exc_info=True`.
- Não volte a usar `traceback.format_exc()` dentro da mensagem. O traceback pertence ao campo de
  exceção do registro, não ao texto.

### Critério de aceite

```bash
docker run --rm --env-file backend/.env -e ENVIRONMENT=development \
  -v /var/www/kredor/backend:/app:ro -w /app --entrypoint python kredor-backend -c "
import sys; sys.path.insert(0,'/app')
from services.logging_service import get_logger, setup_logging
setup_logging(); log = get_logger('teste')
try:
    1/0
except ZeroDivisionError:
    log.error('Traceback do erro', exc_info=True)
"
# Esperado: um log JSON contendo o ZeroDivisionError e o traceback.
# NÃO deve aparecer a linha "--- Logging error ---".
```

Adicionar teste em `tests/` que capture o log emitido e asserte que o traceback está no registro.

---

## 2.5 Testes de race condition falham na suíte

**Severidade:** média
**Esforço:** meio dia
**Origem:** a tarefa 1.5.3 (instalar `pytest-asyncio`) fez esses testes **rodarem** pela primeira
vez. O problema estava escondido, não foi criado agora.

### Problema

`tests/test_race_condition_parcelas.py` tem 3 testes. Rodando o arquivo inteiro:

```
test_indice_unico_bloqueia_insert_paralelo          PASSED
test_job_concorrente_nao_duplica                    PASSED
test_pagamento_e_job_concorrentes_nao_duplicam      FAILED
```

Mas rodando **o terceiro sozinho**, ele **passa**:

```bash
pytest tests/test_race_condition_parcelas.py::test_pagamento_e_job_concorrentes_nao_duplicam
# 1 passed
```

E o resultado é **determinístico** — duas execuções seguidas do arquivo dão `1 failed, 2 passed`
nas duas. Ou seja: não é concorrência instável, é **estado compartilhado** deixado no banco pelos
testes anteriores, provavelmente colidindo com o índice único parcial
`(emprestimo_id, numero_parcela)`.

Um teste que passa sozinho e falha na suíte é pior que um teste ausente: ele treina a equipe a
ignorar a saída vermelha.

### O que fazer

1. Dar isolamento a cada teste. Uma `fixture` que crie ids únicos por teste e limpe no teardown:

   ```python
   @pytest.fixture
   async def emprestimo_isolado(db_teste):
       emp_id = f"test-{uuid.uuid4()}"
       yield emp_id
       await db_teste.parcelas.delete_many({"emprestimo_id": emp_id})
       await db_teste.emprestimos.delete_many({"id": emp_id})
   ```

2. **Antes de dar o isolamento por resolvido, entenda por que falha.** Se o terceiro teste depende de
   as parcelas dos anteriores *não* existirem, isso pode indicar que a asserção dele está frouxa
   (contando documentos globais em vez dos do próprio empréstimo). Nesse caso o conserto é na
   asserção, não só na limpeza.

3. Confirmar que os 3 passam tanto isolados quanto em suíte, e em duas execuções seguidas sem limpar
   o banco entre elas.

### O que NÃO fazer

- **Não** marque com `@pytest.mark.skip` nem `xfail`. Estes são os testes de condição de corrida do
  caminho de dinheiro — desligá-los devolve o projeto ao estado que a tarefa 1.5.3 acabou de
  corrigir.
- **Não** resolva com `pytest -p no:randomly` ou forçando ordem de execução. Ordem fixa esconde o
  acoplamento em vez de removê-lo.
- **Não** limpe a coleção inteira no teardown (`delete_many({})`). Se alguém rodar a suíte apontada
  para o banco errado, apaga dados reais. Limpe só os ids que o teste criou.

### Critério de aceite

```bash
cd /var/www/kredor
for i in 1 2; do
docker run --rm --network kredor_network --env-file backend/.env \
  -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \
  -e MONGO_URL_TESTE_RS='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \
  -e DB_NAME=kredor_test \
  -v /var/www/kredor/backend:/app -w /app --entrypoint python kredor-backend \
  -m pytest tests/test_race_condition_parcelas.py -q -p no:cacheprovider 2>&1 | tail -1
done
# Esperado nas DUAS execuções: "3 passed"
```

---

## 2.6 Migração escreve valores não-inteiros em campos `_centavos`

**Severidade:** alta
**Esforço:** meio dia
**Origem:** causa raiz do `GET /api/dashboard 500`. O commit `fce9b23` tratou o sintoma; a origem
segue aberta.

### Problema

`backend/scripts/migrar_para_centavos.py` tem este fallback em `_montar_update`:

```python
convertido = _converter(doc[campo])
set_[f"{campo}_centavos"] = convertido if convertido is not None else doc[campo]
#                                                                    ^^^^^^^^^^
#                          grava o valor legado CRU num campo que deveria ser int
```

`_converter` devolve `None` para tudo que não é `int`/`float`. Nesses casos a migração grava o valor
original **verbatim** no campo `_centavos`. Medido — 5 de 7 tipos de entrada gravam algo que não é
inteiro:

| Valor legado | Gravado em `valor_principal_centavos` | |
|---|---|:--|
| `1234.56` | `123456` | OK |
| `1234` | `123400` | OK |
| `"1234.56"` | `'1234.56'` | 🔴 string |
| `""` | `''` | 🔴 string |
| `None` | `None` | 🔴 nulo |
| `True` | `True` | 🔴 booleano |
| `{"$numberDecimal": "10"}` | `{'$numberDecimal': '10'}` | 🔴 objeto |

O `historico_prorrogacoes` tem variante do mesmo defeito: quando `_converter` devolve `None`, grava
`None` no campo `_centavos` (`item[f"{campo}_centavos"] = convertido`).

### Por que isso derrubou o dashboard

`sum()` sobre uma coluna com esses valores levanta `TypeError`, virando HTTP 500. Reproduzido:

```
None     antes do fix: TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'
string   antes do fix: TypeError: unsupported operand type(s) for +: 'int' and 'str'
```

### A correção aplicada em `fce9b23` está incompleta

```
None     depois do fix: 1000                    <- resolvido pelo `or 0`
string   depois do fix: TypeError               <- AINDA quebra
```

O `or 0` cobre `None`, mas **string continua derrubando o endpoint**. E
`scripts/corrigir_centavos_float.py` só procura `{"$type": "double"}` — não toca em string, nulo,
booleano nem objeto.

Além disso, `int(round(...))` numa soma de centavos **contraria as regras R1 e R2** deste documento:
reintroduz arredondamento no caminho do dinheiro. É aceitável como cinto de segurança temporário,
não como solução.

### Segundo defeito, em `corrigir_centavos_float.py`

```python
amostra = await db[coll].find_one()
campos = [k for k in amostra.keys() if k.endswith("_centavos")]
```

A lista de campos a verificar vem de **um único documento arbitrário**. Campos `_centavos` que
existem só em parte dos documentos (`valor_incorporado_centavos`, `principal_anterior_centavos`,
`principal_apos_centavos` em `pagamentos`) passam batido se a amostra não os tiver.

### O que fazer

1. **Corrigir a migração** — nunca gravar valor não convertível. Falhe alto:

   ```python
   convertido = _converter(doc[campo])
   if convertido is None:
       # valor legado inesperado: registra e NÃO grava lixo no campo _centavos
       logger.error(
           "Valor legado não convertível em centavos",
           data={"colecao": colecao, "_id": str(doc["_id"]), "campo": campo,
                 "valor": repr(doc[campo]), "tipo": type(doc[campo]).__name__},
       )
       continue
   set_[f"{campo}_centavos"] = convertido
   ```

   Estender `_converter` para aceitar string numérica (`"1234.56"`) via `Decimal(str(...))`, e
   tratar `None`/`""` como `0` **somente se** isso for a semântica correta do campo — decida por
   campo, não por padrão.

2. **Generalizar o script de limpeza.** Trocar a amostra de um documento pela união real dos campos:

   ```python
   campos = set()
   async for doc in db[coll].find({}, {"_id": 0}):
       campos.update(k for k in doc if k.endswith("_centavos"))
   ```

   Ou usar agregação com `$objectToArray`. E procurar **todos** os tipos errados, não só `double`:

   ```python
   {campo: {"$not": {"$type": ["int", "long"]}}}
   ```

3. **Rodar a limpeza e, depois, remover o `int(round(...))`** de `routes/dashboard.py:36` e `:68`.
   O cinto de segurança sai quando os dados estiverem sãos — senão ele esconde a próxima
   contaminação.

4. **Impedir a reincidência.** Adicionar ao `main.py`, no `lifespan`, uma verificação de integridade
   que conte campos `_centavos` com tipo errado e logue `warning` se houver. Custa uma agregação no
   boot e transforma corrupção silenciosa em alerta visível.

### O que NÃO fazer

- **Não** deixe o `int(round(...))` como solução permanente. Ele viola R1/R2 e mascara dado corrompido.
- **Não** trate `None` como `0` no ponto de leitura (`or 0`) e considere resolvido. `0` e "valor
  desconhecido" são coisas diferentes num sistema de crédito: um empréstimo com principal nulo
  somando como zero silenciosamente é pior que um erro.
- **Não** rode a limpeza em produção sem `mongodump` antes.

### Critério de aceite

Nenhum campo `_centavos` com tipo diferente de inteiro, em nenhuma coleção:

```bash
docker exec kredor_mongodb mongosh kredor --quiet --eval '
const colecoes = ["parcelas","emprestimos","pagamentos","carteira_movimentos","transacoes_checkout"];
let total = 0;
colecoes.forEach(c => {
  const campos = new Set();
  db[c].find({}).forEach(d => Object.keys(d).forEach(k => { if (k.endsWith("_centavos")) campos.add(k); }));
  campos.forEach(campo => {
    const n = db[c].countDocuments({[campo]: {$not: {$type: ["int","long"]}}, [campo]: {$exists: true}});
    if (n > 0) { print(`  ${c}.${campo}: ${n} documento(s) com tipo errado`); total += n; }
  });
});
print("TOTAL de campos _centavos com tipo errado: " + total);'
# Esperado: 0
```

E, com os dados sãos, o `int(round(...))` removido:

```bash
cd backend && grep -n "int(round(" routes/dashboard.py
# Esperado: nenhuma saída
```

---

## 2.7 Autorização: `perfil="superadmin"` é um valor morto e armadilhado

**Severidade:** alta
**Esforço:** 1 dia

### Contexto — dois eixos que NÃO são a mesma coisa

O sistema tem **dois conceitos de privilégio, ortogonais entre si**. Confundi-los é o erro que esta
tarefa previne:

| Eixo | Campo | O que controla | Valores |
|---|---|---|---|
| **Hierarquia do tenant** | `owner_id` | Escopo dos dados, via `get_user_context()` | `None` = dono da conta; preenchido = funcionário desse dono |
| **Privilégio de plataforma** | `perfil` | Painel cross-tenant + bypass de limites de plano | `usuario` / `admin` / `superadmin` |

**"Dono da conta" não é "super admin".** Todo cliente pagante é dono da própria conta
(`owner_id=None`, `is_owner()` → `True`), mas recebe `perfil="usuario"` no cadastro
(`routes/auth.py:73`) e no convite de equipe (`routes/equipe.py:91`).

O painel `/api/superadmin/*` é do **operador da plataforma**, não do dono da conta. Ele consulta sem
filtro de tenant:

```python
routes/superadmin.py:75   total_usuarios = await db.usuarios.count_documents({})     # TODOS os tenants
routes/superadmin.py:182  usuarios = await db.usuarios.find(query)                   # lista TODOS
routes/superadmin.py:315  await db.usuarios.update_one(...)                          # desativa 2FA de qualquer conta
routes/superadmin.py:358  await db.usuarios.find_one({"id": usuario_id})             # deleta qualquer usuário
```

Se "super admin" fosse o dono da conta, **todo cliente veria e editaria os dados de todos os outros
clientes**. Não é o caso hoje — e não deve passar a ser.

> ✅ **Verificado em 10/09/2026: não existe vazamento entre tenants.** O cadastro público atribui
> `perfil="usuario"`, o convite de equipe atribui `perfil="usuario"`, e nenhum caminho de código
> promove um cliente a `admin` automaticamente.

### O defeito

`models/usuario.py:14` declara três perfis:

```python
perfil: Literal["superadmin", "admin", "usuario"] = "usuario"
```

Mas o valor `"superadmin"` é tratado de forma **inconsistente** entre as camadas:

| Camada | Arquivo | Aceita `superadmin`? |
|---|---|:--|
| Frontend — guarda de rota | `App.js:127` (`AdminRoute`, usada por **13 rotas**) | ✅ sim |
| Frontend — wrapper de assinatura | `AssinaturaWrapper.js:62` | ✅ sim |
| Backend — limites de plano | `permissao_service.py:22,63,81` (`PERFIS_ADMIN`) | ✅ sim |
| Backend — painel super admin | `superadmin.py:63` | ❌ **não** |
| Backend — suporte | `suporte.py` 116, 158, 183, 206, 232, 259, 285, 300 | ❌ **não** (8x) |
| Backend — notificações | `notificacoes.py` 200, 218, 230, 244, 264, 292 | ❌ **não** (6x) |
| Backend — assinaturas | `assinaturas.py` 552, 564 | ❌ **não** (2x) |
| Backend — bypass de assinatura | `assinatura_middleware.py` 34, 96 | ❌ **não** (2x) |

**19 guardas do backend testam o literal `"admin"` e rejeitam `superadmin`. 1 lugar
(`PERFIS_ADMIN`) o aceita. O frontend o aceita em 13 rotas.**

Consequência prática para um usuário com `perfil="superadmin"`:

1. O frontend mostra o menu e deixa navegar para as 13 rotas administrativas.
2. Cada requisição volta **403 "Acesso restrito a administradores"**.
3. Mas ele ganha limites ilimitados de plano (via `PermissaoService.is_admin()`).

Ou seja: o perfil de nome mais privilegiado dá **menos** acesso que `admin`, numa tela cheia de
erros. É uma armadilha para quem for criar contas administrativas amanhã.

### Causa raiz: a checagem está duplicada 19 vezes

A inconsistência existe **porque não há fonte única**. Cada rota reimplementou
`if current_user.perfil != "admin": raise HTTPException(403, ...)` na mão. Corrigir os 19 literais
sem eliminar a duplicação só reposiciona o problema — o vigésimo será escrito errado de novo.

Note que já existe uma dependency pronta e **ela é usada em apenas 1 dos 20 lugares**:

```python
routes/superadmin.py:61
async def require_super_admin(current_user: Usuario = Depends(get_current_user)):
    """Verifica se usuário é super admin"""
    if current_user.perfil != "admin":     # <- o nome diz superadmin, o teste diz admin
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return current_user
```

O nome da função contradiz o que ela faz. Quem lê conclui o oposto.

### Decisão — eliminar o perfil `superadmin`

**Remova o valor `"superadmin"` do `Literal`.** Não implemente o segundo nível de privilégio.

Justificativa:
- **Nenhum usuário tem esse perfil.** O banco de produção está vazio, o cadastro nunca o atribui, e
  não há caminho de código que promova alguém a `superadmin`. Remover não quebra nada existente.
- Não há necessidade de produto para dois níveis de operador hoje. Um nível (`admin`) resolve.
- Manter o valor obriga a sincronizar **19 guardas de backend + 13 rotas de frontend +
  `PERFIS_ADMIN`** para sempre. Já falhou uma vez.
- O nome colide com `routes/superadmin.py`, que atende `perfil="admin"`. A colisão garante confusão
  futura mesmo se o código for corrigido.

Se um dia houver necessidade real de dois níveis, o caminho certo é **permissões nomeadas**
(o modelo já tem `permissoes: List[str]`), não um segundo valor de enum.

### O que fazer

**Passo 1 — Fonte única de autorização.** Em `services/auth_utils.py` (ou um novo
`services/autorizacao.py`), criar as dependencies e **usá-las em todos os 20 lugares**:

```python
async def require_operador_plataforma(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Operador da plataforma: acesso cross-tenant ao painel administrativo.

    NÃO confundir com dono da conta (`is_owner`), que é todo cliente pagante.
    """
    if current_user.perfil != PERFIL_OPERADOR:
        raise HTTPException(status_code=403, detail="Acesso restrito ao operador da plataforma.")
    return current_user


async def require_dono_da_conta(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Dono da conta (tenant), em oposição a funcionário convidado."""
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")
    return current_user
```

Com `PERFIL_OPERADOR = "admin"` como constante única — nunca mais o literal espalhado.

**Passo 2 — Substituir as 19 checagens inline** por `Depends(require_operador_plataforma)` na
assinatura da rota. Os 8 de `suporte.py`, 6 de `notificacoes.py` e 2 de `assinaturas.py` são
substituições diretas. Os 2 de `assinatura_middleware.py` são *concessão* de bypass, não guarda —
lá troque o literal pela constante `PERFIL_OPERADOR`.

**Passo 3 — Remover `"superadmin"`**:
- `models/usuario.py:14` → `Literal["admin", "usuario"]`
- `services/permissao_service.py:22` → `PERFIS_ADMIN = [PERFIL_OPERADOR]` (ou elimine a lista e use
  a constante)
- `frontend/src/App.js:127` → `user?.perfil !== 'admin'`
- `frontend/src/components/AssinaturaWrapper.js:62` → `user?.perfil === 'admin'`

**Passo 4 — Renomear para o que a coisa é.** `require_super_admin` → `require_operador_plataforma`.
Se preferir manter a URL `/api/superadmin/*` para não quebrar o frontend, mantenha — mas corrija o
nome da função e o docstring, que hoje mentem.

**Passo 5 — Separar "plano ilimitado" de "acesso à plataforma".** Hoje `PermissaoService.is_admin()`
faz as duas coisas com o mesmo campo. Não existe forma de dar enterprise vitalício a um cliente sem
também lhe entregar o painel de todos os tenants. Introduza um campo próprio, ex.:

```python
plano_ilimitado: bool = False   # concedido manualmente; NÃO dá acesso ao painel da plataforma
```

E em `obter_limites` / `verificar_plano_ativo`, conceder o bypass de limites quando
`is_admin(usuario) or usuario.plano_ilimitado`.

### O que NÃO fazer

- **Não** "conserte" adicionando `superadmin` aos 19 literais. Isso mantém a duplicação e a próxima
  rota vai errar de novo. A correção é a fonte única.
- **Não** use `is_owner()` para guardar o painel administrativo. `is_owner()` é `True` para **todo
  cliente pagante** — usá-lo lá entregaria o painel cross-tenant para a base inteira. Este é o erro
  exato que esta tarefa existe para prevenir.
- **Não** faça o backend passar a aceitar `superadmin` só para casar com o frontend. A direção certa
  é o frontend parar de aceitar um valor que não existe mais.
- **Não** mexa em `get_user_context()` nem em `owner_id`. O escopo de dados por tenant está correto
  e auditado; não é parte desta tarefa (regra R9).
- **Não** remova o valor do `Literal` sem antes confirmar que nenhum documento no banco o usa
  (comando no critério de aceite). Se houver algum, migre para `admin` primeiro.

### Critério de aceite

1. Nenhum documento com o perfil removido, em nenhum banco:
   ```bash
   docker exec kredor_mongodb mongosh --quiet --eval '
   ["kredor","kredor_test"].forEach(nome => {
     const n = db.getSiblingDB(nome).usuarios.countDocuments({perfil: "superadmin"});
     print(nome + ": " + n + " usuario(s) com perfil superadmin");
   });'
   # Esperado: 0 em todos
   ```

2. O literal `"admin"` não aparece mais espalhado em guardas.

   > ⚠️ **Este critério estava errado na primeira versão deste documento.** O grep original só
   > cobria `perfil != "admin"` e `perfil == "admin"`, e **8 guardas no formato `not in (...)`
   > escaparam** — ver tarefa 2.8. Use o comando abrangente abaixo:

   ```bash
   cd backend && grep -rnE 'perfil *(!=|==|not in|in) *[\(\["]' routes/ services/ \
     | grep -v "PERFIL_OPERADOR"
   # Esperado: nenhuma saída (só a constante PERFIL_OPERADOR na fonte única)
   ```

3. `superadmin` não existe mais em nenhuma camada:
   ```bash
   cd /var/www/kredor && grep -rn "superadmin" backend/models/ backend/services/ frontend/src/ \
     | grep -v node_modules | grep -viE "superadminAPI|/superadmin|routes/superadmin"
   # Esperado: nenhuma saída (as URLs e o nome do módulo podem permanecer)
   ```

4. Frontend e backend concordam. Teste com um usuário `perfil="usuario"` e outro `perfil="admin"`:
   ```
   usuario  -> AdminRoute redireciona para /dashboard  E  API devolve 403
   admin    -> AdminRoute libera                       E  API devolve 200
   ```
   Adicionar teste de integração em `tests/` cobrindo os dois casos em pelo menos uma rota de cada
   arquivo afetado (`superadmin.py`, `suporte.py`, `notificacoes.py`, `assinaturas.py`).

5. O bypass de limites continua funcionando para `admin` e passa a funcionar para
   `plano_ilimitado=True` **sem** dar acesso ao painel:
   ```
   perfil=usuario, plano_ilimitado=True  -> limites ilimitados  E  403 no painel
   ```

---

## 2.8 Resíduos da tarefa 2.7 — 8 guardas escaparam e `perfil` sem validação

**Severidade:** alta
**Esforço:** 2 horas
**Origem:** falha no critério de aceite **deste documento**, não do executor.

### Por que escaparam

O critério 2 da tarefa 2.7 mandava rodar:

```bash
grep -rn 'perfil != "admin"\|perfil == "admin"' routes/ services/
```

Esse grep cobre apenas comparação direta. **Não cobre o formato `not in (...)` / `not in [...]`**,
que é como 8 guardas estavam escritas. O executor rodou o critério, ele passou, e as 8 continuaram
lá. A culpa é do critério — já corrigido na tarefa 2.7 acima.

### As 8 guardas remanescentes

Todas ainda referenciam `"superadmin"`, valor que **não existe mais** no `Literal` de
`models/usuario.py`:

```
routes/admin_carteiras.py:21   if user.perfil not in ("admin", "superadmin"):
routes/assinaturas.py:1459     if current_user.perfil not in ["admin", "superadmin"]:
routes/assinaturas.py:1474     idem
routes/assinaturas.py:1489     idem
routes/assinaturas.py:1505     idem
routes/emprestimos.py:343      if current_user.perfil not in ['admin','superadmin'] and not is_owner(current_user):
routes/emprestimos.py:836      if current_user.perfil not in ['admin','superadmin']:
routes/emprestimos.py:909      if current_user.perfil not in ['admin','superadmin'] and not is_owner(current_user):
```

`routes/admin_carteiras.py:20` chegou a criar **uma segunda função de guarda local**
(`_garantir_admin`), duplicando o que `services/autorizacao.py` já oferece.

**Não é brecha de segurança hoje:** como `perfil="superadmin"` não passa mais na validação do
modelo, a condição `not in ("admin","superadmin")` é funcionalmente equivalente a
`!= "admin"`. Mas é exatamente a duplicação que a 2.7 existia para eliminar — e a menção a um
valor morto engana quem for ler.

Atenção especial aos 3 de `emprestimos.py`: eles combinam privilégio de plataforma **com**
`is_owner()` no mesmo `if`. Ao converter, preserve a semântica composta — é "operador da plataforma
**ou** dono da conta", não uma coisa só. Não troque por `require_operador_plataforma` cegamente,
senão o dono da conta perde acesso ao próprio empréstimo.

### O campo `perfil` não é validado no painel administrativo

`routes/superadmin.py:31` e `:39`:

```python
class UsuarioCreate(BaseModel):
    perfil: str = "usuario"          # <- str livre, não o Literal

class UsuarioUpdate(BaseModel):
    perfil: Optional[str] = None     # <- idem
```

Um operador pode gravar `perfil="superadmin"`, `"operador"` ou qualquer typo. Consequência medida:

```
perfil='admin'        -> OK
perfil='usuario'      -> OK
perfil='superadmin'   -> ValidationError   <<< login impossível
perfil='operador'     -> ValidationError   <<< login impossível
perfil=''             -> ValidationError   <<< login impossível
```

E `services/auth.py:166` (`get_current_user`) captura apenas `jwt.ExpiredSignatureError` e
`jwt.InvalidTokenError` — **não** captura `ValidationError`. Então o erro sobe como **HTTP 500**, não
como 401/403.

Resultado: um typo no painel **inutiliza a conta em silêncio**, com erro 500 em toda requisição, sem
mensagem que explique a causa e sem forma de o próprio usuário recuperar.

### O que fazer

1. Converter as 8 guardas para a fonte única de `services/autorizacao.py`:
   - `admin_carteiras.py` → apagar `_garantir_admin` e usar `garantir_operador_plataforma`
   - `assinaturas.py` (4) → `garantir_operador_plataforma(current_user)`
   - `emprestimos.py` (3) → **preservar a semântica composta**:
     ```python
     if not (is_operador_plataforma(current_user) or is_owner(current_user)):
         raise HTTPException(status_code=403, detail="...")
     ```
     Considere extrair isso para `services/autorizacao.py` como
     `garantir_operador_ou_dono(user)`, já que aparece 2 vezes.

2. Tipar `perfil` com o mesmo `Literal` do modelo em `routes/superadmin.py`:
   ```python
   from typing import Literal
   PerfilValido = Literal["admin", "usuario"]

   class UsuarioCreate(BaseModel):
       perfil: PerfilValido = "usuario"

   class UsuarioUpdate(BaseModel):
       perfil: Optional[PerfilValido] = None
   ```
   Assim um valor inválido volta **422 na hora**, em vez de inutilizar a conta.

3. Tratar `ValidationError` em `get_current_user` — um documento de usuário corrompido deve dar
   **401 com mensagem clara**, nunca 500:
   ```python
   except ValidationError as e:
       logger.error("Documento de usuário inválido no banco",
                    data={"usuario_id": usuario.get("id"), "erro": str(e)})
       raise HTTPException(status_code=401, detail="Conta com dados inconsistentes. Contate o suporte.")
   ```

### O que NÃO fazer

- **Não** troque os 3 de `emprestimos.py` por `require_operador_plataforma` sem a cláusula
  `or is_owner(...)`. Isso tiraria do dono da conta o acesso aos próprios empréstimos.
- **Não** apenas remova a string `"superadmin"` das 8 listas e pare aí. A tarefa é eliminar a
  duplicação, não editar os literais.
- **Não** amplie o `Literal` do modelo para aceitar valores extras "por segurança". A validação
  estrita é o que transforma typo em 422 em vez de conta inutilizada.

### Critério de aceite

1. Nenhuma guarda de perfil fora da fonte única:
   ```bash
   cd backend && grep -rnE 'perfil *(!=|==|not in|in) *[\(\["]' routes/ services/ \
     | grep -v "PERFIL_OPERADOR"
   # Hoje: 8 linhas
   # Esperado: nenhuma saída
   ```

2. `superadmin` não aparece mais em nenhum literal de código:
   ```bash
   cd backend && grep -rn '"superadmin"\|'"'"'superadmin'"'"'' routes/ services/ models/
   # Esperado: nenhuma saída
   ```

3. Perfil inválido é rejeitado com 422 pelo painel, não aceito:
   ```
   PUT /api/superadmin/usuarios/{id}  body: {"perfil": "superadmin"}  -> 422
   PUT /api/superadmin/usuarios/{id}  body: {"perfil": "admin"}       -> 200
   ```

4. Documento de usuário com perfil inválido devolve **401**, não 500. Teste: gravar
   `perfil="invalido"` direto no banco de teste, autenticar, e conferir o status.

5. O dono da conta continua acessando os próprios empréstimos após a conversão das 3 guardas de
   `emprestimos.py`. Teste com `perfil="usuario"`, `owner_id=None` nas rotas das linhas 343, 836 e 909.

---

## 2.9 Convite de equipe grava a senha no campo errado e não passa pelo modelo

**Severidade:** alta
**Esforço:** meio dia

### Contexto — os dois caminhos de criação de usuário

Só existem dois. Ambos atribuem `perfil="usuario"`; o que os distingue é `owner_id`:

| | Cadastro público (`routes/auth.py:70`) | Convite de equipe (`routes/equipe.py:87`) |
|---|---|---|
| `perfil` | `usuario` | `usuario` |
| `owner_id` | `None` (não é passado) → **dono da conta** | id de quem convidou → **funcionário** |
| `plano` | `trial` | `equipe` (dummy; herda limites do dono) |
| `get_user_context()` | próprio `id` | `owner_id` (opera nos dados do dono) |
| Como é construído | `Usuario(...)` — passa pelo modelo | **dict cru** — não passa pelo modelo |

### Defeito 1 — nome do campo de senha divergente

```python
routes/auth.py:82      doc["senha_hash"] = hash_senha(dados.senha)   # cadastro público
routes/equipe.py:90    "senha": hashed_password,                     # convite (cadastro manual)
routes/equipe.py:129   "senha": hash_senha(dados.senha),             # aceitar convite por email
```

O login sobrevive por um fallback defensivo:

```python
routes/auth.py:179   stored_hash = usuario.get("senha_hash")
routes/auth.py:181   if not stored_hash: stored_hash = usuario.get("senha")
```

**Mas `routes/auth.py:590` (ativar/desativar 2FA) não tem o fallback:**

```python
if not verificar_senha(senha, usuario_doc.get("senha_hash", "")):
```

Para um membro de equipe, `.get("senha_hash", "")` devolve `""`. Comportamento medido de
`verificar_senha` com hash vazio:

```
hash correto -> True
hash VAZIO   -> UnknownHashError: hash could not be identified
```

Ele **levanta exceção**, não retorna `False`. Nada captura → **HTTP 500**, não "Senha incorreta".

**Impacto: nenhum membro de equipe consegue ativar ou desativar 2FA.** Recebe 500 sem explicação, e
não há caminho alternativo na interface.

Note que `routes/auth.py:623` **tem** o fallback (`usuario_doc.get("senha_hash") or usuario_doc.get("senha")`).
O mesmo arquivo trata o mesmo dado de duas formas — sinal de que o fallback foi adicionado
reativamente, onde alguém notou o bug, sem resolver a causa.

### Defeito 2 — o convite não passa pelo modelo `Usuario`

`routes/equipe.py:87` monta um dict literal. Divergência medida:

```
campos do modelo Usuario   : 32
campos gravados no convite : 15
ausentes no doc do membro  : 18
gravados fora do modelo    : ['senha']
```

Os 18 ausentes incluem `two_factor_enabled`, `two_factor_activated_at`, `plano_ilimitado`,
`data_inicio_trial`, `data_fim_trial`, `data_vencimento_assinatura`, `data_expiracao_plano`,
os 7 campos de `onboarding_*` e os 4 de gateway (`asaas_*`, `syncpay_*`).

Não quebra hoje porque o Pydantic preenche defaults na leitura (`Usuario(**usuario)`) e membros
pulam a checagem de trial (vão pelo caminho do dono em `permissao_service.verificar_plano_ativo`).
Mas:

- O documento do membro é **estruturalmente diferente** do documento do dono. Query direta no Mongo
  por `two_factor_enabled` ou `onboarding_completed` ignora todos os membros.
- Esse caminho não tem validação do `Literal` de `perfil`.
- **É a causa raiz do defeito 1.** Quem escreve dict cru não é obrigado a seguir a convenção do
  modelo, e foi assim que `senha` divergiu de `senha_hash`.

### O que fazer

1. **Padronizar o campo em `senha_hash`.** Alterar `routes/equipe.py:90` e `:129`. Escrever
   `backend/scripts/migrar_senha_para_senha_hash.py`, idempotente:
   - para cada documento com `senha` e sem `senha_hash`: `$rename` de `senha` → `senha_hash`
   - para cada documento com **os dois** campos: manter `senha_hash`, `$unset senha`, e **logar
     warning** (indica gravação dupla em algum caminho)
   - imprimir o total migrado

2. **Só depois da migração**, remover os dois fallbacks (`auth.py:181` e `:623`). Enquanto houver
   documento legado com `senha`, os fallbacks são necessários. A ordem é: padronizar a escrita →
   migrar os dados → remover os fallbacks. Nunca o contrário.

3. **Corrigir `auth.py:590`** para não estourar 500 com hash ausente:
   ```python
   stored_hash = usuario_doc.get("senha_hash") or ""
   if not stored_hash or not verificar_senha(senha, stored_hash):
       raise HTTPException(status_code=401, detail="Senha incorreta")
   ```
   E envolver `verificar_senha` num `try/except UnknownHashError` no próprio
   `services/auth.py:47`, devolvendo `False` — hash inválido é senha errada, não erro de servidor.

4. **Construir o membro pelo modelo.** Em `routes/equipe.py`, trocar o dict por:
   ```python
   membro = Usuario(
       nome=dados.nome, email=dados.email, perfil="usuario", plano="equipe",
       plano_ativo=True, owner_id=current_user.id, cargo=dados.cargo,
       permissoes=dados.permissoes,
       email_verificado=bool(dados.senha),
       convite_pendente=not dados.senha,
       email_verification_token=verification_token,
   )
   doc = membro.model_dump()
   doc["senha_hash"] = hashed_password
   ```
   Isso resolve os 18 campos ausentes e impede que a próxima divergência de nome aconteça.

### O que NÃO fazer

- **Não** remova os fallbacks de `auth.py:181` e `:623` antes de migrar os dados. Isso trancaria
  fora do sistema todo membro de equipe já cadastrado.
- **Não** "resolva" adicionando o fallback também na linha 590. Isso propaga a inconsistência para
  um terceiro lugar em vez de eliminá-la.
- **Não** grave os dois campos (`senha` e `senha_hash`) "por compatibilidade". Duas fontes de
  verdade para credencial é pior que uma errada.
- **Não** inclua `senha_hash` no modelo `Usuario`. Ele é serializado em respostas da API
  (`UsuarioPublico` existe justamente para isso, mas `Usuario` aparece em `LoginResponse`). O hash
  fica fora do modelo, adicionado ao dict só na hora de gravar.

### Critério de aceite

1. Nenhum caminho grava o campo `senha`:
   ```bash
   cd backend && grep -rn '"senha":' routes/ services/
   # Esperado: nenhuma saída
   ```

2. Nenhum documento no banco tem o campo legado:
   ```bash
   docker exec kredor_mongodb mongosh kredor --quiet --eval '
   print("com senha (legado): " + db.usuarios.countDocuments({senha: {$exists: true}}));
   print("com senha_hash    : " + db.usuarios.countDocuments({senha_hash: {$exists: true}}));'
   # Esperado: legado 0; senha_hash == total de usuários
   ```

3. `verificar_senha` com hash inválido devolve `False`, não levanta:
   ```bash
   docker run --rm --env-file backend/.env -e ENVIRONMENT=development \
     -v /var/www/kredor/backend:/app:ro -w /app --entrypoint python kredor-backend -c "
   import sys; sys.path.insert(0,'/app')
   from services.auth import verificar_senha
   print('hash vazio ->', verificar_senha('x', ''))
   print('hash lixo  ->', verificar_senha('x', 'nao-e-hash'))"
   # Esperado: False nos dois, sem exceção
   ```

4. Documento de membro criado pelo convite tem os mesmos 32 campos do modelo:
   ```bash
   docker run --rm --env-file backend/.env -e ENVIRONMENT=development \
     -v /var/www/kredor/backend:/app:ro -w /app --entrypoint python kredor-backend -c "
   import sys; sys.path.insert(0,'/app')
   from models.usuario import Usuario
   print('campos do modelo:', len(Usuario.model_fields))"
   # E conferir no banco que um membro recém-convidado tem todos eles.
   ```

5. Teste de integração novo: convidar membro com senha manual, autenticar com ela, e **ativar 2FA**
   com sucesso (hoje isso devolve 500).

---

# FASE 3 — Manutenibilidade

## 3.1 Um único gateway de pagamento

**Severidade:** baixa
**Esforço:** 1 dia

### Problema

Cinco integrações de pagamento coexistem, várias incompletas:

| Arquivo | Linhas | Marcadores TODO/mock |
|---|---|---|
| `services/asaas_service.py` | 298 | 6 |
| `services/mercadopago.py` | 523 | 1 |
| `services/mercadopago_assinatura.py` | 166 | 0 |
| `services/pagseguro.py` | 279 | 0 |
| `services/syncpay.py` | 197 | 0 |

Cada agente de IA que passou pelo projeto adicionou o seu. Ninguém removeu os anteriores.

### O que fazer

1. Decidir **qual** gateway é o oficial (decisão de negócio — pergunte ao dono do produto).
2. Apagar os outros arquivos e suas rotas.
3. Se houver necessidade real de mais de um, criar uma interface comum
   (`services/gateways/base.py`) com implementações por gateway, selecionada por configuração —
   não cinco módulos soltos com APIs diferentes.

### Critério de aceite

```bash
ls backend/services/ | grep -icE "asaas|mercadopago|pagseguro|syncpay"
# Esperado: 1 (ou o número de implementações sob a interface comum)
```

---

## 3.2 Limpeza de arquivos mortos

**Severidade:** baixa
**Esforço:** 2 horas

### Problema

Os 116 arquivos de relatório de IA (`test_reports/`, `security_reports/`) **já foram removidos** na
Fase 1. ✅

Restam exatamente **3** arquivos mortos versionados (verificado em 10/09/2026):

```
backend/routes/assinaturas.py.backup
backend/services/notificacao_service_v2.py
frontend/src/pages/Checkout.js.bak
```

Dois detalhes que valem atenção:

1. **`assinaturas.py.backup` foi *editado* pela migração para centavos** (commit `170fed7` alterou 1
   linha nele). O agente aplicou a renomeação de campos num arquivo que deveria ter sido apagado.
   É inofensivo, mas mostra que o arquivo passa por baixo do radar — motivo de mais para removê-lo.

2. **`notificacao_service_v2.py` está vivo e em uso**, importado **dentro de uma função**:
   ```
   backend/services/notificacao_service.py:97:
       from services.notificacao_service_v2 import verificar_vencimentos_usuario_v2
   ```
   Ou seja, resolver isto também abate um caso da tarefa 3.3.

### O que fazer

1. Apagar `backend/routes/assinaturas.py.backup` e `frontend/src/pages/Checkout.js.bak`.
2. Resolver `notificacao_service` contra `notificacao_service_v2`: mover
   `verificar_vencimentos_usuario_v2` (e o que mais estiver em uso) para
   `notificacao_service.py`, apagar o `_v2`, e trazer o import para o topo do arquivo.
   Se as duas versões implementam a mesma regra de formas diferentes, **decida qual é a correta** —
   não mantenha as duas.
3. Garantir que os relatórios não voltem. Confirmar no `.gitignore`:
   ```
   test_reports/
   security_reports/
   memory/test_credentials.md
   ```
   Manter `memory/PRD.md` se for documentação viva do produto.

### Critério de aceite

```bash
git ls-files | grep -cE "\.backup$|\.bak$|_v2\.py$"
# Esperado: 0
```

---

## 3.3 Quebrar ciclos de import

**Severidade:** baixa
**Esforço:** 2 dias

### Problema

**208** imports dentro de funções (medido em 10/09/2026). Isso é contorno de dependência circular,
não escolha de design. Cada um custa uma resolução de módulo por chamada e esconde o grafo real de
dependências.

Concentração:

| Arquivo | Imports em função |
|---|---:|
| `routes/emprestimos.py` | **55** |
| `routes/assinaturas.py` | 24 |
| `routes/auth.py` | 17 |
| `routes/parcelas.py` | 12 |
| `routes/whatsapp.py` | 10 |
| `routes/superadmin.py` | 8 |
| (demais) | 82 |

`routes/emprestimos.py` sozinho tem mais de um quarto do total — é onde o ciclo é mais denso e onde
começar dá o maior retorno.

```bash
cd backend && grep -rcE "^\s+(from|import) " routes/*.py services/*.py jobs/*.py \
  | grep -v ":0" | sort -t: -k2 -rn | head -10
```

### O que fazer

1. Mapear os ciclos:
   ```bash
   docker exec kredor_backend sh -c "pip install pydeps && python -m pydeps . --max-bacon=2 --show-cycles"
   ```
2. Para cada ciclo, extrair o que é compartilhado (tipos, constantes, funções puras) para um módulo
   neutro que os dois lados importam — tipicamente `models/` ou um novo `domain/`.
3. Mover os imports para o topo do arquivo.

### O que NÃO fazer

- Não faça tudo de uma vez. Um ciclo por commit, com os testes passando entre eles.
- Não crie um `utils.py` genérico como depósito. Extraia por domínio.

### Critério de aceite

```bash
cd backend && grep -rnE "^\s+(from|import) " routes/ services/ jobs/ | grep -v "^\s*#" | wc -l
# Meta: abaixo de 20 (só as exceções documentadas da regra R4)
```

---

## 3.4 Fonte única do cálculo financeiro

**Severidade:** média
**Esforço:** 1 dia

### Problema

`frontend/src/components/JurosCalculator.js:36-41` reimplementa juros compostos e PMT em JavaScript:

```javascript
const montante = P * Math.pow(1 + i, n);
const pmt = i === 0 ? P / n : (P * i) / (1 - Math.pow(1 + i, -n));
```

O backend tem as mesmas fórmulas em `services/calculos.py`. São **duas fontes de verdade para o
cálculo do dinheiro**. Quando uma mudar, a simulação na tela vai divergir do contrato gerado — e o
cliente vê um valor, assina outro.

**A Fase 1 tornou isto urgente.** O backend agora calcula em centavos inteiros com resíduo tratado; o
`JurosCalculator.js` continua em `Number` do JavaScript, que é float binário de dupla precisão — o
mesmo problema que acabamos de eliminar do backend. Hoje a tela e o contrato **já podem divergir em
centavos**, e a divergência só cresce.

### O que fazer

Boa notícia: **o endpoint já existe e está publicado.** Verificado em 10/09/2026:

```
backend/routes/emprestimos.py:28:  @router.post("/simular", response_model=SimulacaoResponse)
```

E a `SimulacaoResponse` já devolve os valores convertidos para reais pela `ReaisJSONResponse`. Então
a tarefa é só do lado do frontend:

1. `JurosCalculator.js` passa a chamar `POST /api/emprestimos/simular` (via `src/api/`, não `axios`
   direto — ver 3.5) e apenas renderizar o resultado.
2. Apagar as fórmulas do JavaScript (linhas 36 e 41).
3. Tratar o estado de carregamento: hoje o cálculo é instantâneo e local; ao virar chamada de rede,
   precisa de *debounce* nos campos e indicador de carregamento, senão o usuário digita e a tela
   pisca a cada tecla.

### O que NÃO fazer

- Não deixe "só uma continha simples" no front. Toda aritmética de dinheiro é do backend.
- Não faça o front recalcular para "validar" a resposta do backend.

### Critério de aceite

```bash
grep -rnE "Math\.pow\(1 ?\+|/ ?100 ?\* ?taxa" frontend/src/ | grep -v node_modules
# Esperado: nenhuma saída
```

---

## 3.4.1 Endpoint público de simulação sem limite de entrada (DoS)

**Severidade:** alta
**Esforço:** 30 minutos
**Origem:** introduzido pela própria tarefa 3.4.

### Contexto

Para tirar a fórmula do frontend, a 3.4 criou um endpoint **público, sem autenticação**:

```python
routes/emprestimos.py:86
@router.post("/simular-publico", response_model=SimulacaoResponse)
async def simular_emprestimo_publico(simulacao: SimulacaoRequest):
    return executar_simulacao(simulacao)
```

A decisão está **certa** e é melhor que a minha spec (que dizia usar `/simular`): a calculadora fica
na landing, onde não há login, e o endpoint delega para o **mesmo** `executar_simulacao` da rota
autenticada — fonte única de cálculo preservada, sem tocar o banco.

### O problema

`SimulacaoRequest` (`models/emprestimo.py:95-109`) **não tem limite superior** nos campos de prazo:

```python
prazo_meses: Optional[int] = None      # sem Field(le=...)
prazo_semanas: Optional[int] = None    # sem Field(le=...)
prazo_dias: Optional[int] = None       # sem Field(le=...)
```

Custo de **uma única requisição**, medido em container com `--memory=512m`:

| `prazo_dias` | tempo | pico de memória | parcelas geradas |
|---:|---:|---:|---:|
| 12 | 0,4 ms | 0 MB | 12 |
| 360 | 6 ms | 0,5 MB | 360 |
| 10.000 | 285 ms | 14 MB | 10.000 |
| **200.000** | **12.777 ms** | **284 MB** | 200.000 |

O crescimento é linear. O container do backend tem limite de **1 GB** e roda **2 workers gunicorn**
— **3 ou 4 requisições concorrentes desse tipo derrubam o worker por OOM**. E a resposta JSON de
200 mil parcelas ainda satura a banda.

O `RateLimitMiddleware` cobre a rota (só `/health`, `/`, `/docs`, `/openapi.json` e `/webhook` são
isentos), mas rate limit protege contra **volume**, não contra **uma requisição caríssima**. Mesmo
dentro da cota, um punhado dessas mata o container.

A validação da 1.5.1 (`principal < periodos → 422`) não protege: basta enviar principal alto junto
com prazo alto.

### O que fazer

Limitar os campos de prazo no schema, com teto compatível com o produto:

```python
class SimulacaoRequest(EntradaEmReais):
    valor_principal_centavos: int = Field(..., ge=1, le=1_000_000_000_00)  # até R$ 1 bi
    prazo_meses: Optional[int] = Field(None, ge=1, le=600)      # 50 anos
    prazo_semanas: Optional[int] = Field(None, ge=1, le=2_600)  # 50 anos
    prazo_dias: Optional[int] = Field(None, ge=1, le=18_250)    # 50 anos
```

Com teto de 18.250 dias o pior caso cai para ~520 ms e ~26 MB — dentro do aceitável para um
endpoint público, e ainda coberto pelo rate limit.

Aplique o mesmo limite em `EmprestimoCreate`, para a rota autenticada não ficar aberta ao mesmo
abuso por um cliente pagante.

### O que NÃO fazer

- **Não** resolva exigindo autenticação no `/simular-publico`. A calculadora da landing precisa dele
  sem login; e o mesmo abuso continuaria possível por qualquer conta trial gratuita.
- **Não** confie apenas no rate limit. Ele limita requisições por janela, não o custo de cada uma.
- **Não** adicione timeout na rota como única defesa. O custo de memória já foi pago quando o
  timeout dispara.
- **Não** invente limites sem checar o produto. Se o negócio precisa de prazo maior que 50 anos,
  ajuste o teto — mas escolha um número e documente por quê.

### Critério de aceite

1. Prazo acima do teto é rejeitado com **422**, não processado:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -X POST https://kredor.com.br/api/emprestimos/simular-publico \
     -H 'Content-Type: application/json' \
     -d '{"valor_principal":100000,"taxa_juros_diaria":0.1,"prazo_dias":200000,"metodo_calculo":"juros_simples","periodicidade":"diario"}'
   # Esperado: 422
   ```

2. Prazo válido continua funcionando:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -X POST https://kredor.com.br/api/emprestimos/simular-publico \
     -H 'Content-Type: application/json' \
     -d '{"valor_principal":10000,"taxa_juros_mensal":2,"prazo_meses":12,"metodo_calculo":"tabela_price","periodicidade":"mensal"}'
   # Esperado: 200
   ```

3. Teste de propriedade novo: para todo prazo no teto máximo de cada periodicidade, a simulação
   completa em menos de 1 segundo e abaixo de 50 MB de pico.

---

## 3.5 Frontend

**Severidade:** baixa — é o item de **menor prioridade de todo este documento**. Não arrisque
regressão em telas de dinheiro por causa dele.

Dividida em quatro subtarefas **independentes**. Faça na ordem, e trate cada uma como entrega
separada.

---

### 3.5(a) `process.env.REACT_APP_BACKEND_URL` — ✅ concluída em 10/09/2026

Eram 3 leituras em 2 arquivos, ignorando a injeção em tempo de execução do `docker-entrypoint.sh`.
As duas de `Configuracoes.js` eram as piores: montavam a **URL de webhook** que o usuário copia para
o painel do gateway; valor de build errado = webhook quebrado e pagamento não confirmado, em
silêncio.

```bash
grep -rn "process.env.REACT_APP_BACKEND_URL" frontend/src/ | wc -l
# Hoje: 0 ✅
```

---

### 3.5(b) Chamadas soltas de `axios`/`fetch` — ✅ concluída em 10/09/2026

Eram 27 chamadas diretas dentro de `src/pages/`, contornando `src/api/`. Cada uma repetia tratamento
de erro, header de auth e URL base.

```bash
grep -rn "axios\.\|fetch(" frontend/src/pages/ | wc -l
# Hoje: 0 ✅
```

---

### 3.5(c) Retorno ao usuário quando a operação falha

**Esforço:** 1 dia · **Risco:** baixo · **Estado medido em 13/09/2026:** 11 sem aviso + 37 com
aviso duplicado = **48 ocorrências em 34 arquivos**

> **Alinhamento feito em 13/09/2026, depois de uma tentativa que piorou a tela.** O critério antigo
> desta subtarefa era `grep -rn -A1 "catch" | grep -c "console.error"`, com meta zero. Essa medição
> **olha uma linha e não enxerga se o bloco já dá retorno ao usuário.** Executada ao pé da letra,
> levou a inserir um `toast` na primeira linha de 83 blocos — 33 deles já mostravam `modal.error`,
> `alert` ou erro na tela. Resultado: **mensagem dupla**, e no `Dashboard.js` um toast vermelho
> "Não foi possível carregar dashboard" em todo 403 de plano inativo, inclusive nas 10 tentativas
> de "✅ Pagamento processado! Ativando seu plano...". O defeito é da especificação, não de quem
> executou: a meta zero foi atingida e a tela ficou pior. Critério refeito abaixo, com medidor
> versionado.

**Medição (única fonte de verdade):**

```bash
cd frontend && node scripts/checar_feedback_em_catch.js src
# sem_aviso (registra, não avisa):    11   <- gate
# duplicado (dois canais na falha):   37   <- gate
# engolido  (nem avisa nem registra): 46   (informativo)
# fora do gate (utils/hooks/context/api): 44   (informativo)
```

O medidor lê o **bloco inteiro**, casando as chaves a partir da que abre depois do `catch (...)`, e
conta **canais distintos** de aviso (`toast`, `modal`/`showModal`, `alert`, erro inline via
`setError`/`setErro`/`setMensagem`). Dois `setError` em ramos de um `if/else` não são duplicidade:
só um roda.

**Por que dois contadores, e não um:** consertar um não pode criar o outro. É esse par que impede a
regressão de 11/09.

**Escopo do gate: `pages/` e `components/`.** Fora deles a função não tem como avisar ninguém — um
formatador ou um parser devolve um valor e quem chamou decide o que dizer. As ocorrências em
`utils/`, `hooks/`, `context/` e `api/` saem listadas como `fora_do_gate` e **não reprovam**.
`engolido` (nem avisa nem registra) também é informativo: a maior parte é silêncio correto, como um
parser de JWT que devolve `null`.

**Silêncio proposital é permitido e precisa ser declarado.** Quando o bloco deve ficar calado
(recurso opcional que falhou, prévia que só deixa de aparecer), escreva dentro dele
`// silencioso: <motivo>`. O medidor ignora o bloco e o motivo fica no código. Exemplo real em
`components/pagamentos/RestanteDoPagamento.js`.

**O que fazer:**

1. **Um canal por falha.** Escolha pelo contexto, não por gosto: `toast` para carregamento em
   segundo plano; `modal.error` para ação que o usuário disparou e precisa reconhecer; erro inline
   para validação de campo de formulário. Se o bloco já tem um, **não acrescente outro** — remova o
   que sobrou.
2. **A mensagem diz qual operação falhou.** "Não foi possível registrar o pagamento" serve; "Erro"
   não serve. Em tela de dinheiro o usuário precisa saber se o pagamento entrou ou não.
3. **Continue registrando o erro** (`console.error` com o `err`), sempre. O aviso é para o usuário;
   o log é para quem for investigar.
4. **Caso especial obrigatório — `pages/Dashboard.js`:** o 403 de plano inativo **não** é erro de
   carregamento. Ele já é tratado abaixo, com `setError` e a mensagem de ativação do plano; o toast
   precisa sair desse caminho (ou ficar condicionado a `err.response?.status !== 403`). Sem isso,
   quem acabou de pagar vê 10 erros vermelhos.

**O que NÃO fazer:** não trocar por toast genérico em todos; não acrescentar aviso em `utils/` ou
`hooks/`; não transformar aviso inline de formulário em modal (o usuário perde o que digitou de
vista); não mexer na estrutura do componente — esta subtarefa toca **só o bloco de erro** (a 3.5(d)
é que quebra arquivo).

**Critério de aceite:**

- `node scripts/checar_feedback_em_catch.js src` com **`sem_aviso: 0` e `duplicado: 0`** (os dois
  números são contagem decrescente: progresso parcial conta, e cada commit deve baixar ao menos um
  deles sem subir o outro).
- `yarn build` com exit 0.
- `diff` dos `data-testid` antes/depois **vazio** (o frontend não tem teste automatizado; são 516
  âncoras hoje).
- Conferência manual declarada de **3 telas de dinheiro** (Pagamentos, Empréstimos,
  EmprestimoDetalhes): provocar uma falha (backend fora do ar) e afirmar no relatório quantas
  mensagens apareceram — a resposta correta é exatamente **uma** por falha.
- Um arquivo por commit, começando por `pages/Dashboard.js` (é o que afeta cliente pagante).

Esta subtarefa é **independente da 3.5(d)** e muito menos arriscada. Faça esta primeiro.

---

### 3.5(d) Quebrar componentes grandes

**Esforço:** 1 dia **por arquivo** · **Risco:** médio a alto (telas de dinheiro)

> **Alinhamento feito em 10/09/2026, a pedido de quem executa.** O agente apontou, com razão, que:
> (1) o número neste documento estava desatualizado — dizia 4 arquivos, são **11**; (2) o critério
> era **binário** ("maior arquivo < 800"), então quebrar 3 ou 8 dava o mesmo resultado: reprovado;
> (3) fazer os 11 (≈15 mil linhas) num passe só é risco alto num app de dinheiro.
>
> **Ele está certo nos três pontos, e o defeito é da especificação, não da execução.** Critério
> binário sobre 11 arquivos independentes é má especificação: torna progresso parcial invisível e
> empurra para uma mudança grande de uma vez — exatamente o oposto do que se quer em código que
> movimenta dinheiro. Corrigido abaixo.

**Medição real (10/09/2026) — 11 arquivos, 15.361 linhas:**

| # | Arquivo | Linhas | Categoria de risco |
|---:|---|---:|---|
| 1 | `pages/AdminUsuarios.js` | 866 | 🟢 só operador da plataforma |
| 2 | `pages/AdminAssinaturas.js` | 1.438 | 🟢 só operador da plataforma |
| 3 | `pages/Simulacao.js` | 951 | 🟢 somente leitura, não persiste |
| 4 | `pages/ConfigNotificacoes.js` | 1.164 | 🟡 configuração |
| 5 | `pages/Configuracoes.js` | 2.442 | 🟡 configuração (maior ganho de linhas) |
| 6 | `pages/Clientes.js` | 1.513 | 🟡 CRUD |
| 7 | `pages/Consultas.js` | 1.621 | 🟠 consome saldo da carteira |
| 8 | `pages/Emprestimos.js` | 1.243 | 🔴 dinheiro |
| 9 | `pages/EmprestimoDetalhes.js` | 1.418 | 🔴 dinheiro |
| 10 | `pages/Pagamentos.js` | 1.585 | 🔴 dinheiro |
| 11 | `pages/CheckoutTransparenteBrick.js` | 1.120 | 🔴 captura de pagamento |

Gerar a lista atualizada (as linhas mudam a cada commit):

```bash
cd frontend && find src -name "*.js" | xargs wc -l | sort -rn \
  | awk '$1>800 && $2!="total" {n++; soma+=$1; printf "  %6d  %s\n", $1, $2} \
         END {print "arquivos > 800: " n "  soma: " soma}'
```

#### Critério corrigido — contagem decrescente, não binário

A métrica passa a ser **quantos arquivos ainda estão acima de 800 linhas**: `11 → 0`. Cada arquivo
concluído é progresso real e mensurável.

**Regras de execução — obrigatórias:**

1. **Um arquivo por commit/PR.** Nunca dois no mesmo.
2. **Siga a ordem da tabela** (1 → 11). Ela vai de menor para maior risco: as duas primeiras são
   telas que só o operador da plataforma usa, então um erro ali não atinge cliente nenhum. Isso
   estabelece o padrão de extração antes de chegar em `Pagamentos.js`.
3. **Pare quando quiser.** A tarefa é cumulativa. Entregar 4 dos 11 e parar é um resultado legítimo,
   não uma tarefa reprovada — e é bem melhor que forçar os 11 e quebrar uma tela.
4. **Extração é mecânica, não redesenho.** Mova formulário, listagem, filtros e modais para arquivos
   próprios, mantendo o estado no componente-pai e passando por props. **Não** aproveite para trocar
   biblioteca de estado, mudar a forma das chamadas de API, nem "melhorar" a UX (regra R9).

#### Gate por arquivo — o frontend não tem testes

Verifiquei: `frontend/package.json` tem o script `test` (`craco test`), mas **0 arquivos de teste**.
Em compensação existem **474 `data-testid`** em `src/pages/` — as telas foram construídas para serem
testáveis.

Então o gate de cada arquivo é:

1. **Build limpo** (não confie no exit code de um pipe):
   ```bash
   cd /var/www/kredor && docker compose build frontend > /tmp/fe.log 2>&1; echo "exit=$?"
   # Esperado: exit=0
   ```

2. **Os `data-testid` da página continuam todos presentes.** Antes de mexer, capture o inventário;
   depois, compare. Nenhum pode desaparecer — se um sumiu, algum elemento foi perdido na extração:
   ```bash
   cd frontend
   grep -rho 'data-testid="[^"]*"' src/pages/Pagamentos.js | sort > /tmp/testids_antes.txt
   # ... faça a extração (o arquivo pai + os novos subcomponentes) ...
   grep -rho 'data-testid="[^"]*"' src/pages/Pagamentos.js src/components/pagamentos/ | sort > /tmp/testids_depois.txt
   diff /tmp/testids_antes.txt /tmp/testids_depois.txt
   # Esperado: nenhuma diferença
   ```

3. **Conferência manual da página**, declarada no relatório. Liste explicitamente o que você abriu e
   confirmou: carregou a listagem, abriu cada modal, submeteu o formulário principal, o filtro
   filtrou, o estado sobreviveu à navegação de ida e volta.

4. Para os 4 arquivos 🔴, **também** o fluxo de ponta a ponta: registrar um pagamento de teste e
   conferir no banco que parcela e empréstimo foram atualizados. Use `backend/tests/e2e_centavos.sh`
   como referência.

#### O que NÃO fazer

- **Não** quebre mais de um arquivo por commit. Se algo regredir, você precisa saber qual extração
  causou.
- **Não** comece pelos 🔴. `Pagamentos.js` e `CheckoutTransparenteBrick.js` são os últimos da fila
  de propósito.
- **Não** mude comportamento durante a extração. Se encontrar um bug no caminho, anote e siga (R9) —
  corrigir junto torna impossível saber se a regressão veio da extração ou da correção.
- **Não** apague `data-testid` "que não parecem usados". Eles são a única ancoragem de teste que
  existe no frontend hoje.

#### Critério de aceite

```bash
cd frontend && find src -name "*.js" | xargs wc -l | sort -rn \
  | awk '$1>800 && $2!="total"' | wc -l
# Hoje: 11
# Meta final: 0   (progresso parcial CONTA — reporte o número a cada arquivo entregue)
```

Mais, por arquivo entregue: build com `exit=0`, `diff` dos `data-testid` vazio, e a lista do que foi
conferido manualmente colada no relatório.

---

# Checklist final

Marque somente com a saída do comando de verificação em mãos.

## Fase 1 — Bloqueadores ✅ concluída em 10/09/2026

- [x] **1.1** Credencial rotacionada e fora do git
- [x] **1.2** Segredos obrigatórios em produção (falha no import se ausentes)
- [x] **1.3** Dinheiro em centavos inteiros, zero `round()` em `calculos.py`, testes de precisão passando
- [x] **1.4** Replica set ativo, transações nos 4 blocos de dinheiro, toda operação com `session=`

## Fase 1.5 — Correções da Fase 1 ✅ concluída em 10/09/2026

- [x] **1.5.1** Zero valores negativos na grade completa (37 → 0, verificado em 2.700 casos)
- [x] **1.5.2** `transacao()` loga warning em dev e falha em produção quando não há replica set
- [x] **1.5.3** `pytest-asyncio` + `pytest.ini` instalados; os 3 testes de race condition rodando
- [x] **1.5.4** Checker de `session=` cobre chamadas de função, com allowlist explícita
- [x] **1.5.5** `frontend/Dockerfile` em `node:20-alpine` no repositório

## Fase 2 — Operabilidade

- [x] **2.1** Zero `print()` em `routes/`, `services/`, `jobs/` (296 → 0); `request_id` via contextvar
- [ ] **2.2** Datas como `Date` do BSON; migração idempotente executada (hoje: **333** `isoformat()`, **37** `utcnow()`)
- [ ] **2.3** Zero query dentro de laço não justificada (hoje: **35 em 14 arquivos**) — contagem decrescente, detector `backend/scripts/checar_query_em_laco.py`
- [x] **2.4** `exc_info=True` normalizado no `_log:144`; nenhum `--- Logging error ---`
- [x] **2.5** `test_race_condition_parcelas.py` com 3 passed em duas execuções seguidas
- [x] **2.6** Zero campos `_centavos` com tipo != inteiro; migração falha alto; `int(round(` removido; verificação de integridade no `lifespan`
- [x] **2.7** Fonte única (`services/autorizacao.py`); `perfil="superadmin"` eliminado do modelo e do frontend; `plano_ilimitado` separado do acesso à plataforma
- [x] **2.8** As 8 guardas convertidas para a fonte única; `perfil` tipado com `Literal`; `ValidationError` → 401
- [x] **2.9** `senha_hash` padronizado; script de migração criado; `verificar_senha` devolve `False`; `equipe.py` usa o modelo
- [ ] **2.10** Cobrança automática usa `saldo_devedor_parcela` (hoje ignora multa/mora) e piso configurável para não cobrar centavos de quem já pagou

## Fase 3 — Manutenibilidade

- [x] **3.1** Gateways reduzidos de 5 para 2, sob estratégia de seleção configurável
- [x] **3.2** Arquivos mortos removidos (3 → 0); `notificacao_service_v2` resolvido
- [x] **3.3** Imports em função abaixo de 20 (177 → **3**)
- [x] **3.4** Cálculo financeiro só no backend (endpoint `/simular-publico` + debounce no `JurosCalculator`)
- [x] **3.4.1** Teto de prazo aplicado; prazo acima do teto devolve **422**, válido devolve 200
- [x] **3.5(a)** `process.env.REACT_APP_BACKEND_URL` eliminado (3 → 0)
- [x] **3.5(b)** Chamadas soltas de `axios`/`fetch` em `pages/` (27 → 0)
- [x] **3.5(c)** Um aviso (e só um) por falha em `pages/`+`components/` — `sem_aviso 0`, `duplicado 0`, `canal_morto 0` pelo medidor `frontend/scripts/checar_feedback_em_catch.js` (rodada `4561019` + correção `ff32630` do toast de `sonner`, que não era exibido)
- [ ] **3.5(d)** Arquivos > 800 linhas: **12 → 0**, um por commit, na ordem de risco da tabela — progresso parcial conta
- [x] **R11** Criação de entidade pelo modelo Pydantic (3 → 0)

## Verificação de regressão (rodar ao fim de cada fase)

```bash
cd /var/www/kredor
docker compose build && docker compose up -d
sleep 15
docker compose ps                                    # 4 containers healthy
docker exec kredor_backend python -m pytest tests/ -q  # suíte passando
curl -s -o /dev/null -w "%{http_code}\n" https://kredor.com.br/       # 200
curl -s -o /dev/null -w "%{http_code}\n" https://kredor.com.br/api/   # 200
docker compose logs backend --since 2m | grep -iE "error|traceback"   # vazio
```

---

## Observações finais

**O que já está bom e não deve ser mexido:**

- Desenho dos índices em `main.py` (compostos na ordem certa, TTL nas coleções de log, índice único
  parcial contra parcela duplicada).
- Isolamento multi-tenant por `usuario_id` — consistente, sem vazamento encontrado.
- Autenticação: bcrypt, 2FA, Turnstile, proteção brute-force por conta e por IP, rate limit
  distribuído via Mongo.
- Os scripts de reparo em `backend/scripts/` — continuam úteis para dados legados.

**O que a Fase 1 acertou e merece registro** (auditado em 10/09/2026):

- `backend/utils/dinheiro.py` — a conversão na fronteira via `EntradaEmReais` (um `model_validator`
  do Pydantic) mais `ReaisJSONResponse` como `default_response_class` é **melhor que a solução
  especificada neste documento**: o frontend não precisou de uma única linha de mudança.
- `backend/scripts/checar_session_em_transacao.py` — checker AST que entende até a cadeia
  `db.x.find(...).to_list()`. Bem superior ao `grep` que este documento sugeria. (Ver 1.5.4 para o
  ponto cego que sobrou.)
- A separação entre operação transacional e efeito derivado em `routes/pagamentos.py` está correta:
  `registrar_auditoria` e `recalcular_status_emprestimo` rodam **depois** do commit, com comentário
  documentando a intenção. Verifiquei a indentação linha por linha.
- A invariante `soma das amortizações == principal` fecha **exata** em 2.700 de 2.700 combinações
  testadas de principal × taxa × prazo, em Price, SAC e parcelas fixas.

**Ordem recomendada:**

1. **Fase 1** — ✅ concluída (1.1 → 1.2 → 1.4 → 1.3)
2. **Fase 1.5** — começar por **1.5.5** (5 minutos, desbloqueia build limpo), depois **1.5.1**
   (o único que envolve dinheiro), depois 1.5.3 → 1.5.2 → 1.5.4
3. **Fase 2** — 2.2 (datas) antes de 2.3 (N+1), porque parte dos laços some ao trocar as somas em
   Python por agregação, e agregação por período depende de `Date` do BSON
4. **Fase 3** — qualquer ordem; 3.2 é o mais rápido

**Ferramentas de verificação disponíveis no repositório:**

| Script | O que checa |
|---|---|
| `backend/scripts/checar_query_em_laco.py` | N+1 (tarefa 2.3) |
| `backend/scripts/checar_session_em_transacao.py` | `session=` em transação (1.4, 1.5.4) |
| `backend/scripts/migrar_para_centavos.py` | Migração de dados legados (1.3) |
| `backend/tests/test_dinheiro.py` | Precisão monetária (1.3, 1.5.1) |
| `backend/tests/test_transacao_pagamento.py` | Rollback real (1.4) — exige `MONGO_URL_TESTE_RS` |

**Como rodar a suíte** (o `.dockerignore` do backend exclui `tests/`, então não está na imagem):

```bash
cd /var/www/kredor
docker run --rm --network kredor_network --env-file backend/.env \
  -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \
  -e MONGO_URL_TESTE_RS='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \
  -e DB_NAME=kredor_test \
  -v /var/www/kredor/backend:/app -w /app --entrypoint python kredor-backend \
  -m pytest tests/test_dinheiro.py tests/test_transacao_pagamento.py -q -p no:cacheprovider
```

Sem `MONGO_URL_TESTE_RS` os 3 testes de atomicidade ficam **skipped** em silêncio — sempre passe a
variável. Os testes de integração que fazem login falham nesta VPS porque o Turnstile aqui usa chave
real (o ambiente de preview usa a chave de teste que sempre passa) e o banco de produção está vazio;
isso é diferença de ambiente, não regressão.
