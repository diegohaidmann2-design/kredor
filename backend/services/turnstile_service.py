"""
Serviço de verificação do Cloudflare Turnstile (proteção anti-bot).
A validação DEVE ser feita no backend: um token gerado no browser, sozinho,
não é garantia de segurança. Tokens são de uso único e expiram em 300s.
"""
import os
import httpx

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def turnstile_habilitado() -> bool:
    return bool(os.environ.get("TURNSTILE_SECRET_KEY", "").strip())


async def verificar_turnstile(token: str, remote_ip: str | None = None) -> tuple[bool, list]:
    """
    Verifica o token do Turnstile junto à Cloudflare.
    Retorna (sucesso, error_codes). Fail-closed: se a Cloudflare estiver
    inacessível, retorna (False, ["network-error"]).
    """
    secret = os.environ.get("TURNSTILE_SECRET_KEY", "").strip()
    if not secret:
        # Proteção desabilitada (sem secret configurado)
        return True, []

    if not token:
        return False, ["missing-input-response"]

    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("success")), data.get("error-codes", [])
    except (httpx.HTTPError, ValueError):
        return False, ["network-error"]
