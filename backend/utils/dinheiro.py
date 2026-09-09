"""Dinheiro: centavos inteiros por dentro, reais só na fronteira da API.

Convenção: todo campo monetário interno termina em `_centavos` e é `int`.
Na entrada da API o frontend envia reais (ex.: 100.50) e na saída recebe reais
sob o nome sem sufixo (ex.: `valor_total`). A conversão acontece exclusivamente
aqui: `EntradaEmReais` (request) e `ReaisJSONResponse` (response).
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator

SUFIXO = "_centavos"
_CENTAVO = Decimal("0.01")


def reais_para_centavos(valor: float | str | Decimal | int) -> int:
    """Converte reais em centavos inteiros passando por Decimal (100.50 -> 10050, nunca 10049)."""
    return int(Decimal(str(valor)).quantize(_CENTAVO, rounding=ROUND_HALF_UP) * 100)


def centavos_para_reais(centavos: int) -> float:
    """Converte centavos inteiros em reais para a resposta da API."""
    return centavos / 100


def arredondar_centavos(valor: float | Decimal | int) -> int:
    """Único ponto de arredondamento: resultado de (centavos x taxa) para centavos inteiros."""
    return int(Decimal(str(valor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def dividir_centavos(total: int, partes: int) -> list[int]:
    """Divide um total em N partes inteiras; o resto vai na última, então sum(resultado) == total."""
    if partes <= 0:
        raise ValueError("partes deve ser maior que zero")
    base = total // partes
    resultado = [base] * partes
    resultado[-1] += total - (base * partes)
    return resultado


def formatar_reais(centavos: int | None) -> str:
    """Formata centavos no padrão brasileiro: 123456 -> '1.234,56'."""
    texto = f"{(centavos or 0) / 100:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def para_api(obj: Any) -> Any:
    """Converte recursivamente `chave_centavos: int` em `chave: reais` para o frontend."""
    if isinstance(obj, dict):
        saida = {}
        for chave, valor in obj.items():
            if isinstance(chave, str) and chave.endswith(SUFIXO) and not isinstance(valor, bool):
                base = chave[: -len(SUFIXO)]
                if valor is None:
                    saida[base] = None
                elif isinstance(valor, (int, float)):
                    saida[base] = centavos_para_reais(valor)
                else:
                    saida[chave] = para_api(valor)
            else:
                saida[chave] = para_api(valor)
        return saida
    if isinstance(obj, list):
        return [para_api(item) for item in obj]
    return obj


class EntradaEmReais(BaseModel):
    """Request model cujos campos `x_centavos` aceitam `x` em reais vindo do frontend."""

    @model_validator(mode="before")
    @classmethod
    def _converter_reais(cls, dados: Any) -> Any:
        if not isinstance(dados, dict):
            return dados
        dados = dict(dados)
        for campo in cls.model_fields:
            if not campo.endswith(SUFIXO):
                continue
            base = campo[: -len(SUFIXO)]
            if base in dados and campo not in dados:
                valor = dados.pop(base)
                dados[campo] = reais_para_centavos(valor) if valor is not None else None
        return dados


class ReaisJSONResponse(JSONResponse):
    """Fronteira de saída: tudo que a API devolve passa por `para_api`."""

    def render(self, content: Any) -> bytes:
        return super().render(para_api(content))
