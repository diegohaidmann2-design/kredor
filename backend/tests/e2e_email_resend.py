"""E2E: envio real pela API do Resend.

Pedido de 15/09/2026. Usa `delivered@resend.dev`, o endereço de teste do próprio Resend:
a API aceita e simula a entrega, sem mandar email para nenhuma caixa de verdade.

NÃO exercita a reserva no SMTP de propósito — ela mandaria email real pelo servidor antigo.
Essa parte é coberta por tests/test_email_resend.py, com os transportes substituídos.

Não é coletado pelo pytest (não começa com test_). Rodar da raiz do repositório:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \\
      -e DB_NAME=kredor_test -e PYTHONPATH=/app \\
      --tmpfs /app/static:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend tests/e2e_email_resend.py

Precisa da RESEND_API_KEY do .env. Sai com código 1 se qualquer verificação falhar.
"""
import asyncio
import sys

from config import EMAIL_PROVIDER, RESEND_API_KEY, RESEND_FROM
from services import email_service

DESTINO_TESTE = "delivered@resend.dev"

FALHAS = []


def conferir(condicao, mensagem):
    print(("  OK    " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        FALHAS.append(mensagem)


async def main():
    print("=== configuração ===")
    conferir(bool(RESEND_API_KEY), "RESEND_API_KEY presente no ambiente")
    conferir(EMAIL_PROVIDER == "resend", f"EMAIL_PROVIDER = {EMAIL_PROVIDER!r} (esperado 'resend')")
    conferir("kredor.com.br" in RESEND_FROM,
             f"remetente é do domínio da marca: {RESEND_FROM!r}")
    if not RESEND_API_KEY:
        print("\nsem chave: nada a testar contra a API")
        sys.exit(1)

    print("\n=== envio pela API (endereço de teste do Resend) ===")
    ok = await email_service._enviar_via_resend(
        DESTINO_TESTE,
        "Kredor — verificação de integração",
        "<p>Envio de teste da integração com o Resend.</p>",
        corpo_texto="Envio de teste da integração com o Resend.",
    )
    conferir(ok is True, "o Resend aceitou o envio (domínio verificado e chave válida)")

    print("\n=== chave inválida é recusada sem derrubar o processo ===")
    original = email_service.RESEND_API_KEY
    email_service.RESEND_API_KEY = "re_chave_invalida_de_teste"
    try:
        ruim = await email_service._enviar_via_resend(
            DESTINO_TESTE, "Não deve sair", "<p>x</p>")
        conferir(ruim is False, "chave inválida devolve False em vez de levantar")
    finally:
        email_service.RESEND_API_KEY = original

    print("\n=== remetente de domínio não verificado é recusado ===")
    # Prova que a verificação de domínio do Resend está de fato ativa nesta conta.
    payload_ruim = email_service.montar_payload_resend(
        DESTINO_TESTE, "Não deve sair", "<p>x</p>",
        remetente="Kredor <teste@dominio-que-nao-existe-kredor.com>")
    import httpx
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(email_service.RESEND_ENDPOINT,
                         headers=email_service._cabecalhos_resend(), json=payload_ruim)
    conferir(r.status_code >= 400,
             f"domínio não verificado recusado (status {r.status_code})")

    print("\n" + ("=" * 70))
    if FALHAS:
        print(f"{len(FALHAS)} FALHA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print("TUDO OK")


if __name__ == "__main__":
    asyncio.run(main())
