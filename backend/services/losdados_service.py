"""
Serviço de integração com a API LosDados (consultas de crédito/dados).
A chave da API fica SOMENTE no backend (variável de ambiente) e nunca é
retornada ao frontend. Campos internos (signature/issuer) também são removidos.
"""
import os
import re
import httpx

LOSDADOS_API_URL = os.environ.get("LOSDADOS_API_URL", "https://app.losdados.com.br/api/v1")
LOSDADOS_API_KEY = os.environ.get("LOSDADOS_API_KEY", "")

TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class LosDadosError(Exception):
    """Erro de negócio da consulta (mensagem segura para o usuário)."""
    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def validar_cpf(cpf: str) -> str:
    """Valida e normaliza um CPF (retorna somente dígitos). Lança LosDadosError se inválido."""
    digits = re.sub(r"\D", "", cpf or "")
    if len(digits) != 11 or digits == digits[0] * 11:
        raise LosDadosError("CPF inválido. Informe 11 dígitos.", status_code=400)

    def _dv(base: str) -> int:
        s = sum(int(d) * f for d, f in zip(base, range(len(base) + 1, 1, -1)))
        r = (s * 10) % 11
        return 0 if r == 10 else r

    if _dv(digits[:9]) != int(digits[9]) or _dv(digits[:10]) != int(digits[10]):
        raise LosDadosError("CPF inválido (dígitos verificadores não conferem).", status_code=400)
    return digits


def _sanitize(payload: dict) -> dict:
    """Remove campos internos que não devem ir para o cliente."""
    if not isinstance(payload, dict):
        return {"data": payload}
    payload.pop("signature", None)
    payload.pop("issuer", None)
    return payload


async def consultar_cpf(cpf: str) -> dict:
    """Consulta um CPF na LosDados. Retorna o payload sanitizado (sem a chave)."""
    if not LOSDADOS_API_KEY:
        raise LosDadosError("Serviço de consultas não configurado.", status_code=503)

    cpf_digits = validar_cpf(cpf)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                f"{LOSDADOS_API_URL}/consulta/cpf",
                params={"cpf": cpf_digits},
                headers={"X-API-Key": LOSDADOS_API_KEY},
            )
    except httpx.RequestError:
        raise LosDadosError("Não foi possível conectar ao serviço de consultas. Tente novamente.", status_code=504)

    if resp.status_code == 401:
        raise LosDadosError("Falha de autenticação no serviço de consultas.", status_code=502)
    if resp.status_code == 429:
        raise LosDadosError("Limite de consultas atingido. Tente novamente mais tarde.", status_code=429)
    if resp.status_code >= 400:
        raise LosDadosError("O serviço de consultas retornou um erro. Tente novamente.", status_code=502)

    try:
        payload = resp.json()
    except ValueError:
        raise LosDadosError("Resposta inválida do serviço de consultas.", status_code=502)

    return _sanitize(payload)
