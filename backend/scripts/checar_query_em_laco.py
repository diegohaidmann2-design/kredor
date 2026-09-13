"""Detecta consultas ao banco executadas dentro de laços (padrão N+1).

Uso:
    python3 scripts/checar_query_em_laco.py routes/dashboard.py

Sai com código 1 se encontrar alguma ocorrência, para poder ser usado em CI.
"""
import sys

ABERTURAS_DE_LACO = ("for ", "while ", "async for ")


def checar(caminho: str) -> list[tuple[int, int, str]]:
    """Retorna [(linha_da_query, linha_do_laco, trecho)] das queries dentro de laço."""
    achados: list[tuple[int, int, str]] = []
    lacos_abertos: list[tuple[int, int]] = []  # (indentação, linha)

    with open(caminho, encoding="utf-8") as arquivo:
        for numero, linha in enumerate(arquivo, 1):
            conteudo = linha.strip()
            if not conteudo or conteudo.startswith("#"):
                continue

            indentacao = len(linha) - len(linha.lstrip())
            while lacos_abertos and indentacao <= lacos_abertos[-1][0]:
                lacos_abertos.pop()

            if conteudo.startswith(ABERTURAS_DE_LACO):
                lacos_abertos.append((indentacao, numero))
            elif lacos_abertos and "await db." in conteudo:
                achados.append((numero, lacos_abertos[-1][1], conteudo[:70]))

    return achados


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: checar_query_em_laco.py <arquivo.py> [outro.py ...]")
        return 2

    total = 0
    for caminho in sys.argv[1:]:
        achados = checar(caminho)
        total += len(achados)
        print(f"{caminho}: {len(achados)} query(s) dentro de laço")
        for numero, laco, trecho in achados:
            print(f"  linha {numero} (laço aberto na linha {laco}): {trecho}")

    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
