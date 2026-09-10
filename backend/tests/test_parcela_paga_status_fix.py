"""
Regression + fix test for the "parcela paga com status 'atrasado'" bug
(GestorCred /pagamentos screen).

Coverage:
  * Endpoints regressão: /api/emprestimos, /api/parcelas/pendentes,
    /api/pagamentos, /api/dashboard, /api/emprestimos/abertos/resumo → 200
  * Empréstimo específico e8238621-...: parcelas 1..4 = 'pago', 5 = 'pendente'
  * Global data invariant: nenhuma parcela ativa com vp>=vt>0 e
    status != 'pago'/'paga'
  * Serviço juros_mora_service.atualizar_todas_parcelas_atrasadas
    auto-cura parcelas quitadas e não recalcula mora nelas
  * services.juros_mora_service._calcular_valores: parcela quitada
    retorna dias_atraso=0 mesmo quando data_vencimento < hoje
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import requests

sys.path.insert(0, "/app/backend")

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as fh:
            for line in fh:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except OSError:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

EMAIL_ADILSON = "diego.haidmann@gmail.com"  # empréstimo e8238621 é do Diego, não Adilson (task description imprecisa)
SENHA = "Teste@2026"
EMPRESTIMO_ID = "e8238621-f48b-4275-a1bd-540583ee3268"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def token_adilson():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": EMAIL_ADILSON, "senha": SENHA, "turnstile_token": "dummy"},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no token in response: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def auth_headers(token_adilson):
    return {"Authorization": f"Bearer {token_adilson}", "Content-Type": "application/json"}


# --------------------------------------------------------------------------- #
# Regressão de endpoints
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "path",
    [
        "/emprestimos",
        "/parcelas/pendentes",
        "/pagamentos",
        "/dashboard",
        "/emprestimos/abertos/resumo",
    ],
)
def test_endpoint_returns_200(auth_headers, path):
    r = requests.get(f"{API}{path}", headers=auth_headers, timeout=60)
    assert r.status_code == 200, f"{path} → {r.status_code}: {r.text[:200]}"


# --------------------------------------------------------------------------- #
# Empréstimo específico
# --------------------------------------------------------------------------- #
def test_emprestimo_adilson_parcelas_status(auth_headers):
    r = requests.get(f"{API}/emprestimos/{EMPRESTIMO_ID}/parcelas", headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text
    parcelas = r.json() or []
    assert len(parcelas) >= 5, f"expected >=5 parcelas, got {len(parcelas)}"
    parcelas_sorted = sorted(parcelas, key=lambda p: p.get("numero_parcela", 0))
    for p in parcelas_sorted[:4]:
        assert p["status"] in ("pago", "paga"), (
            f"parcela {p.get('numero_parcela')} status={p.get('status')} (esperado pago)"
        )
    assert parcelas_sorted[4]["status"] == "pendente", (
        f"parcela 5 status={parcelas_sorted[4].get('status')} (esperado pendente)"
    )


def test_parcela_4_nao_aparece_como_atrasada_em_pendentes(auth_headers):
    """Parcela 4 do empréstimo Adilson NÃO deve aparecer no /parcelas/pendentes."""
    r = requests.get(f"{API}/parcelas/pendentes", headers=auth_headers, timeout=60)
    assert r.status_code == 200
    for p in r.json():
        if p.get("emprestimo_id") == EMPRESTIMO_ID and p.get("numero_parcela") == 4:
            pytest.fail(
                f"Parcela 4 apareceu em pendentes com status={p.get('status')} "
                f"vp={p.get('valor_pago_centavos')} vt={p.get('valor_total_centavos')}"
            )


# --------------------------------------------------------------------------- #
# Invariante global no banco
# --------------------------------------------------------------------------- #
def test_no_inconsistent_paid_parcelas_in_db():
    """
    Nenhuma parcela ativa deve ter valor_pago_centavos >= valor_total_centavos > 0
    e status diferente de 'pago'/'paga'.
    """
    from config import db  # noqa: WPS433

    async def _run():
        return await db.parcelas.count_documents({
            "deleted": {"$ne": True},
            "valor_total_centavos": {"$gt": 0},
            "$expr": {"$gte": ["$valor_pago_centavos", "$valor_total_centavos"]},
            "status": {"$nin": ["pago", "paga"]},
        })

    count = asyncio.get_event_loop().run_until_complete(_run())
    assert count == 0, f"{count} parcelas quitadas ainda com status errado"


# --------------------------------------------------------------------------- #
# _calcular_valores: guard de parcela quitada
# --------------------------------------------------------------------------- #
def test_calcular_valores_guard_para_parcela_quitada():
    from services.juros_mora_service import _calcular_valores  # noqa: WPS433

    ontem = datetime.now(timezone.utc) - timedelta(days=60)
    parcela = {
        "status": "atrasado",  # status inconsistente
        "valor_total_centavos": 10000,
        "valor_pago_centavos": 10000,
        "data_vencimento": ontem.isoformat(),
    }
    emprestimo = {"taxa_multa_atraso": 2.0, "taxa_juros_mora_diario": 0.033}
    res = _calcular_valores(parcela, emprestimo, datetime.now(timezone.utc))
    assert res["dias_atraso"] == 0
    assert res["valor_multa_centavos"] == 0
    assert res["valor_juros_mora_centavos"] == 0


# --------------------------------------------------------------------------- #
# atualizar_todas_parcelas_atrasadas: auto-heal
# --------------------------------------------------------------------------- #
def test_atualizar_todas_parcelas_atrasadas_auto_heal():
    """Insere uma parcela órfã com vp>=vt e status='atrasado' e verifica auto-heal."""
    from config import db  # noqa: WPS433
    from services.juros_mora_service import atualizar_todas_parcelas_atrasadas  # noqa: WPS433

    parcela_id = "TEST_HEAL_PARCELA_001"
    usuario_id = "TEST_HEAL_USER_001"
    emprestimo_id = "TEST_HEAL_EMP_001"

    async def _run():
        # cleanup
        await db.parcelas.delete_many({"id": parcela_id})
        await db.emprestimos.delete_many({"id": emprestimo_id})

        await db.emprestimos.insert_one({
            "id": emprestimo_id,
            "usuario_id": usuario_id,
            "taxa_multa_atraso": 2.0,
            "taxa_juros_mora_diario": 0.033,
        })
        vencido = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        await db.parcelas.insert_one({
            "id": parcela_id,
            "usuario_id": usuario_id,
            "emprestimo_id": emprestimo_id,
            "valor_total_centavos": 50000,
            "valor_pago_centavos": 50000,
            "valor_multa_centavos": 0,
            "valor_juros_mora_centavos": 0,
            "status": "atrasado",
            "data_vencimento": vencido,
            "deleted": False,
        })

        try:
            stats = await atualizar_todas_parcelas_atrasadas(usuario_id=usuario_id)
            assert stats["total_processadas"] >= 1
            p = await db.parcelas.find_one({"id": parcela_id})
            assert p["status"] == "pago"
            assert p["valor_multa_centavos"] == 0
            assert p["valor_juros_mora_centavos"] == 0
            assert p["dias_atraso"] == 0
        finally:
            await db.parcelas.delete_many({"id": parcela_id})
            await db.emprestimos.delete_many({"id": emprestimo_id})

    asyncio.get_event_loop().run_until_complete(_run())
