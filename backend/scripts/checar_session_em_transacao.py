"""Verifica que TODA operação de banco dentro de `async with transacao()` recebe `session=`.

Duas verificações:
  1. `await db.*` escrito diretamente no bloco -> precisa de `session=`.
  2. Qualquer OUTRA chamada `await` no bloco (ex.: um service que pode tocar o banco por
     dentro) -> precisa de `session=` OU estar na allowlist `PERMITIDAS_SEM_SESSION`.
     Isso fecha o ponto cego: adicionar uma chamada de service dentro da transação obriga
     uma decisão consciente — ou propaga a sessão, ou entra na allowlist com justificativa.

Uso: python scripts/checar_session_em_transacao.py routes/*.py services/*.py
Sai com código 1 se encontrar operação sem session (serve para CI).
"""
import ast
import sys

# Chamadas `await` que podem aparecer dentro de um bloco transacional SEM `session=`
# porque não tocam o banco (efeito derivado, rede enfileirada, utilitário puro).
# Cada entrada é o nome do callable (último atributo da cadeia). Documente o motivo ao adicionar.
PERMITIDAS_SEM_SESSION = {
    "asyncio.sleep",          # espera pura
    "asyncio.gather",         # orquestração
    "call_next",              # middleware
}


def _e_transacao(item: ast.withitem) -> bool:
    expr = item.context_expr
    return isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "transacao"


def _comeca_com_db(node: ast.AST) -> bool:
    while isinstance(node, ast.Attribute):
        node = node.value
    return isinstance(node, ast.Name) and node.id == "db"


def _nome_callable(func: ast.AST) -> str:
    """Reconstrói o nome pontilhado do callable: `services.x.f` -> 'services.x.f', `f` -> 'f'."""
    partes = []
    while isinstance(func, ast.Attribute):
        partes.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        partes.append(func.id)
    return ".".join(reversed(partes))


def _tem_session(call: ast.Call) -> bool:
    return any(k.arg == "session" for k in call.keywords)


def _problemas(bloco: list[ast.stmt]) -> list[tuple[int, str]]:
    achados = []
    for stmt in bloco:
        for node in ast.walk(stmt):
            if not (isinstance(node, ast.Await) and isinstance(node.value, ast.Call)):
                continue
            call = node.value
            # cursor: await db.x.find(...).to_list(...) -> a sessão vai no find()
            alvo = call
            while isinstance(alvo.func, ast.Attribute) and isinstance(alvo.func.value, ast.Call):
                alvo = alvo.func.value

            if isinstance(alvo.func, ast.Attribute) and _comeca_com_db(alvo.func.value):
                if not _tem_session(alvo):
                    achados.append((node.lineno, f"db sem session: {_nome_callable(alvo.func)}"))
                continue

            # Chamada await que NÃO é db.* : service/helper. Exige session= ou allowlist.
            nome = _nome_callable(alvo.func) or _nome_callable(call.func)
            base = nome.split(".")[-1]
            if _tem_session(call) or _tem_session(alvo):
                continue
            if nome in PERMITIDAS_SEM_SESSION or base in PERMITIDAS_SEM_SESSION:
                continue
            achados.append((node.lineno, f"chamada sem session (nem na allowlist): {nome}"))
    return achados


def checar(caminho: str) -> list[tuple[int, str]]:
    arvore = ast.parse(open(caminho, encoding="utf-8").read())
    achados: list[tuple[int, str]] = []
    blocos = 0
    for node in ast.walk(arvore):
        if isinstance(node, ast.AsyncWith) and any(_e_transacao(i) for i in node.items):
            blocos += 1
            achados += _problemas(node.body)
    print(f"{caminho}: {blocos} bloco(s) transacional(is), {len(achados)} problema(s)")
    for linha, msg in achados:
        print(f"    linha {linha}: {msg}")
    return achados


if __name__ == "__main__":
    total = sum(len(checar(c)) for c in sys.argv[1:])
    sys.exit(1 if total else 0)
