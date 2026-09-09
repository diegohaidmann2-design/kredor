"""
Testa as 3 melhorias de PRORROGAÇÃO:
  (1) POST /api/emprestimos/{id}/prorrogar/preview
  (2) Histórico persistido em emprestimo.historico_prorrogacoes
  (3) GET  /api/emprestimos/{id}/recibo-prorrogacao/{prorrogacaoId} => PDF
      POST /api/emprestimos/{id}/recibo-prorrogacao/{prorrogacaoId}/whatsapp
"""
import os
import requests
import pytest
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cred-system-staging.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_SENHA = "Teste@2026"
TURNSTILE = "test-token"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={
        "email": ADMIN_EMAIL, "senha": ADMIN_SENHA, "turnstile_token": TURNSTILE
    }, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def cliente_id(headers):
    # pega qualquer cliente existente do admin
    r = requests.get(f"{API}/clientes", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    lst = body.get("items") if isinstance(body, dict) else body
    assert lst and len(lst) > 0, "Nenhum cliente disponível"
    return lst[0]["id"]


@pytest.fixture(scope="module")
def emprestimo_teste(headers, cliente_id):
    """Cria empréstimo NOVO (juros_simples 1000@10%/3m) e devolve o id."""
    payload = {
        "cliente_id": cliente_id,
        "valor_principal": 1000.0,
        "taxa_juros_mensal": 10.0,
        "prazo_meses": 3,
        "metodo_calculo": "juros_simples",
        "periodicidade": "mensal",
        "data_emprestimo": datetime.now(timezone.utc).date().isoformat(),
        "descricao": "TEST_prorrogacao_melhorias",
    }
    r = requests.post(f"{API}/emprestimos", headers=headers, json=payload, timeout=30)
    assert r.status_code in (200, 201), r.text
    emp = r.json()
    emp_id = emp.get("id") or emp.get("_id")
    assert emp_id
    yield emp_id
    # cleanup
    try:
        requests.delete(f"{API}/emprestimos/{emp_id}", headers=headers, timeout=30)
    except Exception:
        pass


def test_preview_prorrogacao(headers, emprestimo_teste):
    r = requests.post(f"{API}/emprestimos/{emprestimo_teste}/prorrogar/preview",
                      headers=headers, json={"periodos": 2}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tipo"] == "prazo_fixo"
    assert data["novo_total_parcelas"] == 5
    assert abs(data["valor_parcela"] - 300.0) < 0.02, data["valor_parcela"]
    assert abs(data["novo_valor_total_com_juros"] - 1500.0) < 0.02
    assert isinstance(data["parcelas_preview"], list) and len(data["parcelas_preview"]) == 5
    p1 = data["parcelas_preview"][0]
    for k in ("numero_parcela", "data_vencimento", "valor_total"):
        assert k in p1


def test_prorrogar_e_historico(headers, emprestimo_teste):
    # executa a prorrogação
    r = requests.post(f"{API}/emprestimos/{emprestimo_teste}/prorrogar",
                      headers=headers, json={"periodos": 2}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    # esperado: id retornado
    prorrogacao_id = body.get("prorrogacao_id") or body.get("prorrogacaoId")
    assert prorrogacao_id, f"prorrogacao_id ausente na resposta: {body}"

    # confirma que histórico persistiu (lê diretamente do DB — o endpoint GET
    # /api/emprestimos/{id} usa response_model=Emprestimo que NÃO inclui
    # historico_prorrogacoes; a validação via API está no test_get_retorna_historico)
    import asyncio
    from dotenv import load_dotenv
    load_dotenv('/app/backend/.env')
    from motor.motor_asyncio import AsyncIOMotorClient
    async def _fetch():
        c = AsyncIOMotorClient(os.environ['MONGO_URL'])
        d = await c[os.environ['DB_NAME']].emprestimos.find_one(
            {"id": emprestimo_teste}, {"_id": 0, "historico_prorrogacoes": 1})
        c.close()
        return d
    emp = asyncio.get_event_loop().run_until_complete(_fetch()) if False else asyncio.run(_fetch())
    hist = (emp or {}).get("historico_prorrogacoes") or []
    assert len(hist) >= 1, f"Histórico não foi persistido: {emp}"
    item = next((h for h in hist if h.get("id") == prorrogacao_id), hist[-1])
    assert item.get("periodos") == 2
    assert "data" in item or "criado_em" in item
    assert item.get("parcelas_antes") == 3
    assert item.get("parcelas_depois") == 5
    pytest.prorrogacao_id = prorrogacao_id  # share


def test_get_endpoint_retorna_historico_prorrogacoes(headers, emprestimo_teste):
    """Regressão: o endpoint GET /api/emprestimos/{id} DEVE devolver
    historico_prorrogacoes para o frontend renderizar a seção 'Histórico de Prorrogações'.
    """
    r = requests.get(f"{API}/emprestimos/{emprestimo_teste}", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    hist = body.get("historico_prorrogacoes")
    assert hist is not None and len(hist) >= 1, (
        f"Bug: GET /api/emprestimos/{{id}} não retorna historico_prorrogacoes. "
        f"Keys retornadas: {list(body.keys())}"
    )


def test_recibo_pdf(headers, emprestimo_teste):
    pid = getattr(pytest, "prorrogacao_id", None)
    assert pid, "prorrogacao_id não capturado no teste anterior"
    r = requests.get(f"{API}/emprestimos/{emprestimo_teste}/recibo-prorrogacao/{pid}",
                     headers=headers, timeout=60)
    assert r.status_code == 200, r.text[:400]
    ctype = r.headers.get("content-type", "")
    assert "application/pdf" in ctype, ctype
    assert r.content[:4] == b"%PDF", "Conteúdo não é PDF"
    assert len(r.content) > 500


def test_recibo_whatsapp_mensagem_amigavel(headers, emprestimo_teste):
    pid = getattr(pytest, "prorrogacao_id", None)
    assert pid
    r = requests.post(f"{API}/emprestimos/{emprestimo_teste}/recibo-prorrogacao/{pid}/whatsapp",
                      headers=headers, timeout=60)
    # WhatsApp NÃO configurado no ambiente -> esperar 400 com msg amigável
    assert r.status_code in (200, 400), r.text
    if r.status_code == 400:
        detail = ""
        try:
            detail = (r.json().get("detail") or "").lower()
        except Exception:
            detail = r.text.lower()
        assert ("whatsapp" in detail or "integra" in detail), f"Mensagem não amigável: {detail}"
