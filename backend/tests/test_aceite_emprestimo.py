"""
Tests para o fluxo público de Aceite de Empréstimo.
Endpoints públicos:
 - GET  /api/aceite-emprestimo/info/{token}
 - POST /api/aceite-emprestimo/confirmar/{token} (multipart)
"""
import io
import os
import subprocess

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cred-sistema-preview.preview.emergentagent.com").rstrip("/")
TOKEN = "demoaceite999"


def _rearm_token():
    """Rearma o token para status 'aguardando' via mongosh."""
    cmd = (
        'db.emprestimos.updateOne({"aceite.token":"' + TOKEN + '"},'
        '{$set:{"aceite.status":"aguardando"},$unset:{"aceite.assinado_em":"","aceite.assinatura_path":""}})'
    )
    subprocess.run(["mongosh", "--quiet", "gestorcred", "--eval", cmd], capture_output=True, check=False)


def _png_bytes():
    img = Image.new("RGB", (200, 60), color=(255, 255, 255))
    # Draw a "signature" line
    for x in range(10, 190):
        img.putpixel((x, 30 + (x % 5)), (0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module", autouse=True)
def rearm_before_all():
    _rearm_token()
    yield
    _rearm_token()


class TestAceiteInfo:
    def test_info_ok(self):
        r = requests.get(f"{BASE_URL}/api/aceite-emprestimo/info/{TOKEN}", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "empresa" in data
        assert "cliente" in data and "nome" in data["cliente"]
        assert "emprestimo" in data and "valor_principal" in data["emprestimo"]
        assert "parcelas" in data and isinstance(data["parcelas"], list)
        assert data["aceite"]["status"] == "aguardando"

    def test_info_token_invalido(self):
        r = requests.get(f"{BASE_URL}/api/aceite-emprestimo/info/token-que-nao-existe-xyz", timeout=30)
        assert r.status_code == 404


class TestAceiteConfirmarValidacoes:
    def setup_method(self):
        _rearm_token()

    def _post(self, files=None, data=None):
        return requests.post(
            f"{BASE_URL}/api/aceite-emprestimo/confirmar/{TOKEN}",
            files=files or {},
            data=data or {},
            timeout=30,
        )

    def test_sem_turnstile(self):
        png = _png_bytes()
        r = self._post(
            files={"assinatura": ("assinatura.png", png, "image/png")},
            data={"confirmou_dados": "true", "consentimento": "true"},
        )
        assert r.status_code == 400
        assert "anti-rob" in r.text.lower() or "turnstile" in r.text.lower()

    def test_sem_confirmou_dados(self):
        png = _png_bytes()
        r = self._post(
            files={"assinatura": ("assinatura.png", png, "image/png")},
            data={"consentimento": "true", "turnstile_token": "dummy"},
        )
        assert r.status_code == 400
        assert "revisou" in r.text.lower() or "concorda" in r.text.lower()

    def test_sem_consentimento(self):
        png = _png_bytes()
        r = self._post(
            files={"assinatura": ("assinatura.png", png, "image/png")},
            data={"confirmou_dados": "true", "turnstile_token": "dummy"},
        )
        assert r.status_code == 400
        assert "autorizar" in r.text.lower() or "assinatura" in r.text.lower()

    def test_sem_assinatura(self):
        r = self._post(
            data={"confirmou_dados": "true", "consentimento": "true", "turnstile_token": "dummy"},
        )
        assert r.status_code == 400
        assert "assin" in r.text.lower()


class TestAceiteConfirmarSucesso:
    def test_aceite_sucesso_e_reenvio_bloqueado(self):
        _rearm_token()
        png = _png_bytes()
        r = requests.post(
            f"{BASE_URL}/api/aceite-emprestimo/confirmar/{TOKEN}",
            files={"assinatura": ("assinatura.png", png, "image/png")},
            data={"confirmou_dados": "true", "consentimento": "true", "turnstile_token": "dummy-token"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("status") == "aceito"

        # Verifica persistência via GET /info
        r2 = requests.get(f"{BASE_URL}/api/aceite-emprestimo/info/{TOKEN}", timeout=30)
        assert r2.status_code == 200
        assert r2.json()["aceite"]["status"] == "aceito"
        assert r2.json()["aceite"]["assinado_em"] is not None

        # Reenvio deve dar 400
        r3 = requests.post(
            f"{BASE_URL}/api/aceite-emprestimo/confirmar/{TOKEN}",
            files={"assinatura": ("assinatura.png", png, "image/png")},
            data={"confirmou_dados": "true", "consentimento": "true", "turnstile_token": "dummy-token"},
            timeout=30,
        )
        assert r3.status_code == 400
        assert "aceit" in r3.text.lower()
