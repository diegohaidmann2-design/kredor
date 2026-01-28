"""
Modelos Multi-Tenant
"""
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime


class Tenant(BaseModel):
    id: str
    nome: str
    slug: str  # URL-friendly name
    email_admin: str
    plano: Literal["trial", "basico", "profissional", "enterprise"] = "trial"
    status: Literal["ativo", "suspenso", "cancelado"] = "ativo"
    limites: dict = {
        "max_usuarios": 1,
        "max_clientes": 50,
        "max_emprestimos": 100
    }
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    trial_ends_at: Optional[str] = None
    assinatura_id: Optional[str] = None  # ID da assinatura no gateway


class TenantCreate(BaseModel):
    nome: str
    slug: str
    email_admin: str
    plano: Literal["trial", "basico", "profissional", "enterprise"] = "trial"


class TenantUpdate(BaseModel):
    nome: Optional[str] = None
    plano: Optional[Literal["trial", "basico", "profissional", "enterprise"]] = None
    status: Optional[Literal["ativo", "suspenso", "cancelado"]] = None
    limites: Optional[dict] = None


class TenantStats(BaseModel):
    total_tenants: int
    tenants_ativos: int
    tenants_trial: int
    tenants_pagantes: int
    receita_mensal: float
    distribuicao_planos: List[dict]


class SuperAdminDashboard(BaseModel):
    stats: TenantStats
    tenants_recentes: List[dict]
    alertas: List[dict]
