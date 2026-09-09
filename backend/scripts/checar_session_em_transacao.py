"""Verifica que TODA operação `await db.*` dentro de `async with transacao()` recebe `session=`.

Uso: python scripts/checar_session_em_transacao.py routes/*.py services/*.py
Sai com código 1 se encontrar operação sem session (serve para CI).
"""
import ast
import sys


def _e_transacao(item: ast.withitem) -> bool:
    expr = item.context_expr
    return isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "transacao"


def _comeca_com_db(node: ast.AST) -> bool:
    while isinstance(node, ast.Attribute):
        node = node.value
    return isinstance(node, ast.Name) and node.id == "db"


def _operacoes_sem_session(bloco: list[ast.stmt]) -> list[int]:
    faltando = []
    for stmt in bloco:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
                call = node.value
                # cursor: await db.x.find(...).to_list(...) -> a sessão vai no find()
                alvo = call
                while isinstance(alvo.func, ast.Attribute) and isinstance(alvo.func.value, ast.Call):
                    alvo = alvo.func.value
                if isinstance(alvo.func, ast.Attribute) and _comeca_com_db(alvo.func.value):
                    if not any(k.arg == "session" for k in alvo.keywords):
                        faltando.append(node.lineno)
    return faltando


def checar(caminho: str) -> list[int]:
    arvore = ast.parse(open(caminho, encoding="utf-8").read())
    faltando = []
    blocos = 0
    for node in ast.walk(arvore):
        if isinstance(node, ast.AsyncWith) and any(_e_transacao(i) for i in node.items):
            blocos += 1
            faltando += _operacoes_sem_session(node.body)
    print(f"{caminho}: {blocos} bloco(s) transacional(is), {len(faltando)} operação(ões) sem session")
    return faltando


if __name__ == "__main__":
    total = sum(len(checar(c)) for c in sys.argv[1:])
    sys.exit(1 if total else 0)
