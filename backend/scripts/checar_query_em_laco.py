"""Detecta consultas ao banco executadas dentro de laços (padrão N+1).

Uso:
    python3 scripts/checar_query_em_laco.py routes/dashboard.py [outro.py ...]

Sai com código 1 se encontrar alguma ocorrência não justificada, para poder ser usado em CI.

Há laço em que buscar em lote não agrega: o que ele percorre é uma lista fixa escrita no código
(seed de templates padrão, tabela de preços), então N é constante e pequeno — trocar por
`bulk_write` só adiciona complexidade. Nesses casos escreva

    # lote-nao-se-aplica: <motivo>

na linha do laço, na linha da query ou na linha imediatamente acima dela. A ocorrência sai da
contagem que reprova e entra em "justificada(s)", com o motivo visível no código. Não use a
justificativa em laço que percorre coleção do banco: aí o N cresce com o uso e é N+1 de verdade.
"""
import sys

ABERTURAS_DE_LACO = ("for ", "while ", "async for ")
JUSTIFICATIVA = "# lote-nao-se-aplica:"


def checar(caminho: str) -> tuple[list[tuple[int, int, str]], list[tuple[int, str]]]:
    """Retorna (achados, justificadas).

    achados     = [(linha_da_query, linha_do_laco, trecho)]
    justificadas = [(linha_da_query, motivo)]
    """
    achados: list[tuple[int, int, str]] = []
    justificadas: list[tuple[int, str]] = []
    lacos_abertos: list[tuple[int, int, bool]] = []  # (indentação, linha, justificado)
    comentario_anterior: str | None = None

    with open(caminho, encoding="utf-8") as arquivo:
        for numero, linha in enumerate(arquivo, 1):
            conteudo = linha.strip()
            if not conteudo:
                continue
            if conteudo.startswith("#"):
                # Só o comentário de justificativa vale para a linha seguinte.
                comentario_anterior = conteudo if JUSTIFICATIVA in conteudo else None
                continue

            indentacao = len(linha) - len(linha.lstrip())
            while lacos_abertos and indentacao <= lacos_abertos[-1][0]:
                lacos_abertos.pop()

            justificativa_aqui = None
            for origem in (conteudo, comentario_anterior):
                if origem and JUSTIFICATIVA in origem:
                    justificativa_aqui = origem.split(JUSTIFICATIVA, 1)[1].strip()
                    break

            if conteudo.startswith(ABERTURAS_DE_LACO):
                lacos_abertos.append((indentacao, numero, justificativa_aqui is not None))
            elif lacos_abertos and "await db." in conteudo:
                motivo = justificativa_aqui
                if motivo is None and lacos_abertos[-1][2]:
                    motivo = "justificado no laço"
                if motivo:
                    justificadas.append((numero, motivo))
                else:
                    achados.append((numero, lacos_abertos[-1][1], conteudo[:70]))

            comentario_anterior = None

    return achados, justificadas


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: checar_query_em_laco.py <arquivo.py> [outro.py ...]")
        return 2

    total = total_justificado = 0
    for caminho in sys.argv[1:]:
        achados, justificadas = checar(caminho)
        total += len(achados)
        total_justificado += len(justificadas)
        sufixo = f", {len(justificadas)} justificada(s)" if justificadas else ""
        print(f"{caminho}: {len(achados)} query(s) dentro de laço{sufixo}")
        for numero, laco, trecho in achados:
            print(f"  linha {numero} (laço aberto na linha {laco}): {trecho}")
        for numero, motivo in justificadas:
            print(f"  linha {numero} justificada: {motivo}")

    print(f"TOTAL: {total} não justificada(s), {total_justificado} justificada(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
