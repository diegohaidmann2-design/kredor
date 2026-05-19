"""
Rotas da aplicação
"""
from fastapi import APIRouter

from .auth import router as auth_router
from .clientes import router as clientes_router
from .emprestimos import router as emprestimos_router
from .pagamentos import router as pagamentos_router
from .dashboard import router as dashboard_router
from .configuracoes import router as configuracoes_router
from .relatorios import router as relatorios_router
from .contratos import router as contratos_router
from .notificacoes import router as notificacoes_router
from .assistente import router as assistente_router
from .auditoria import router as auditoria_router
from .parcelas import router as parcelas_router
from .assinaturas import router as assinaturas_router
from .exportacao import router as exportacao_router
from .superadmin import router as superadmin_router
from .admin_jobs import router as admin_jobs_router
from .analise import router as analise_router
from .admin_transacoes import router as admin_transacoes_router
from .onboarding import router as onboarding_router
from .scheduler_admin import router as scheduler_admin_router
from .portal import router as portal_router
from .suporte import router as suporte_router
from .upload import router as upload_router
from .equipe import router as equipe_router
from .whatsapp import router as whatsapp_router
from .whatsapp_anti_spam import router as whatsapp_anti_spam_router
from .whatsapp_templates import router as whatsapp_templates_router
from .asaas import router as asaas_router
from .backup import router as backup_router


# Router principal que agrupa todas as rotas
api_router = APIRouter()

# Inclui todas as rotas com seus prefixos
api_router.include_router(auth_router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(clientes_router, prefix="/clientes", tags=["Clientes"])
api_router.include_router(emprestimos_router, prefix="/emprestimos", tags=["Empréstimos"])
api_router.include_router(pagamentos_router, prefix="/pagamentos", tags=["Pagamentos"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(configuracoes_router, prefix="/configuracoes", tags=["Configurações"])
api_router.include_router(relatorios_router, prefix="/relatorios", tags=["Relatórios"])
api_router.include_router(contratos_router, prefix="/contratos", tags=["Contratos"])
api_router.include_router(notificacoes_router, prefix="/notificacoes", tags=["Notificações"])
api_router.include_router(assistente_router, prefix="/assistente", tags=["Assistente IA"])
api_router.include_router(auditoria_router, prefix="/auditoria", tags=["Auditoria"])
api_router.include_router(parcelas_router, prefix="/parcelas", tags=["Parcelas"])
api_router.include_router(assinaturas_router, prefix="/assinaturas", tags=["Assinaturas"])
api_router.include_router(exportacao_router, prefix="/exportacao", tags=["Exportação"])
api_router.include_router(superadmin_router, prefix="/superadmin", tags=["Super Admin"])
api_router.include_router(admin_jobs_router, prefix="/admin/jobs", tags=["Admin Jobs"])
api_router.include_router(analise_router, prefix="/analise", tags=["Análise e Score"])
api_router.include_router(admin_transacoes_router, tags=["Admin - Transações"])
api_router.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
api_router.include_router(scheduler_admin_router, prefix="/admin", tags=["Admin - Scheduler"])
api_router.include_router(portal_router)  # Já tem o prefix no router
api_router.include_router(suporte_router, prefix="/suporte", tags=["Suporte"])
api_router.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])
api_router.include_router(whatsapp_anti_spam_router, prefix="/whatsapp", tags=["WhatsApp Anti-Spam"])
api_router.include_router(whatsapp_templates_router, prefix="/whatsapp", tags=["WhatsApp Templates"])
api_router.include_router(asaas_router, prefix="/asaas", tags=["Asaas - Pagamentos"])

api_router.include_router(upload_router, prefix="/upload", tags=["Upload"])
api_router.include_router(equipe_router, prefix="/equipe", tags=["Equipe"])
api_router.include_router(backup_router, prefix="/backup", tags=["Backup & Restore"])


@api_router.get("/")
async def root():
    return {"message": "Gestor Cred API v2.0 - Refatorado", "status": "online"}
