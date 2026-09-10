"""
Tarefa 2.7 — autorização: operador da plataforma vs dono da conta.
Critérios 4 (frontend/backend concordam) e 5 (plano_ilimitado sem painel).
"""
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.usuario import Usuario
from services.auth_utils import is_operador_plataforma, is_owner, PERFIL_OPERADOR
from services.autorizacao import garantir_operador_plataforma, require_operador_plataforma
from services.permissao_service import PermissaoService


def _u(**kw) -> Usuario:
    base = dict(nome="X", email="x@x.com")
    base.update(kw)
    return Usuario(**base)


def test_perfil_literal_sem_superadmin():
    # superadmin não é mais um valor válido
    with pytest.raises(Exception):
        _u(perfil="superadmin")


def test_operador_vs_dono():
    admin = _u(perfil="admin")
    usuario = _u(perfil="usuario")
    dono_pagante = _u(perfil="usuario", owner_id=None)

    assert is_operador_plataforma(admin) is True
    assert is_operador_plataforma(usuario) is False
    # dono da conta é todo cliente (owner_id None), mas NÃO é operador
    assert is_owner(dono_pagante) is True
    assert is_operador_plataforma(dono_pagante) is False


def test_garantir_operador_plataforma_bloqueia_usuario():
    garantir_operador_plataforma(_u(perfil="admin"))  # não levanta
    with pytest.raises(HTTPException) as exc:
        garantir_operador_plataforma(_u(perfil="usuario"))
    assert exc.value.status_code == 403


@pytest.mark.asyncio(loop_scope="module")
async def test_require_operador_plataforma_dependency():
    admin = _u(perfil="admin")
    assert await require_operador_plataforma(admin) is admin
    with pytest.raises(HTTPException) as exc:
        await require_operador_plataforma(_u(perfil="usuario"))
    assert exc.value.status_code == 403


# ---- Critério 5: plano_ilimitado dá limites, não dá painel ----

@pytest.mark.asyncio(loop_scope="module")
async def test_plano_ilimitado_tem_limites_mas_nao_painel():
    svc = PermissaoService()
    ilimitado = _u(perfil="usuario", plano_ilimitado=True)

    # limites ilimitados
    assert svc.tem_acesso_ilimitado(ilimitado) is True
    limites = await svc.obter_limites(ilimitado)
    assert limites.max_clientes == -1
    assert limites.max_emprestimos == -1

    # NÃO é operador -> painel bloqueado (403)
    assert svc.is_admin(ilimitado) is False
    with pytest.raises(HTTPException) as exc:
        garantir_operador_plataforma(ilimitado)
    assert exc.value.status_code == 403


def test_perfil_operador_constante():
    assert PERFIL_OPERADOR == "admin"
