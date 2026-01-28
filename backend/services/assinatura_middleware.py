"""
Middleware para verificar assinatura e trial dos usuários
"""
from fastapi import HTTPException, status
from datetime import datetime, timezone
from models.usuario import Usuario


class AssinaturaException(HTTPException):
    """Exceção personalizada para problemas de assinatura"""
    def __init__(self, tipo: str, mensagem: str):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "tipo": tipo,
                "mensagem": mensagem
            }
        )


def verificar_email_confirmado(usuario: Usuario):
    """Verifica se o email foi confirmado"""
    if not usuario.email_verificado:
        raise AssinaturaException(
            tipo="email_nao_verificado",
            mensagem="Por favor, confirme seu email antes de continuar. Verifique sua caixa de entrada."
        )


def verificar_assinatura_ativa(usuario: Usuario):
    """Verifica se a assinatura do usuário está ativa"""
    
    # ADMIN TEM ACESSO TOTAL - bypass de todas as verificações
    if usuario.perfil == "admin":
        return  # Admin sempre tem acesso
    
    # Email precisa estar verificado
    if not usuario.email_verificado:
        raise AssinaturaException(
            tipo="email_nao_verificado",
            mensagem="Por favor, confirme seu email antes de continuar."
        )
    
    agora = datetime.now(timezone.utc)
    
    # Verificar trial
    if usuario.plano == "trial":
        if agora > usuario.data_fim_trial:
            raise AssinaturaException(
                tipo="trial_expirado",
                mensagem=f"Seu período de testes expirou em {usuario.data_fim_trial.strftime('%d/%m/%Y')}. Assine um plano para continuar."
            )
        return  # Trial ainda válido
    
    # Verificar assinatura paga
    if usuario.data_vencimento_assinatura:
        if agora > usuario.data_vencimento_assinatura:
            raise AssinaturaException(
                tipo="assinatura_vencida",
                mensagem=f"Sua assinatura venceu em {usuario.data_vencimento_assinatura.strftime('%d/%m/%Y')}. Renove para continuar."
            )
    
    # Se não tem data de vencimento mas não é trial, considerar vencido
    if usuario.plano != "trial" and not usuario.data_vencimento_assinatura:
        raise AssinaturaException(
            tipo="assinatura_vencida",
            mensagem="Sua assinatura está inativa. Por favor, assine um plano."
        )


def dias_restantes_trial(usuario: Usuario) -> int:
    """Retorna quantos dias faltam para o trial expirar"""
    if usuario.plano != "trial":
        return 0
    
    agora = datetime.now(timezone.utc)
    delta = usuario.data_fim_trial - agora
    return max(0, delta.days)


def dias_restantes_assinatura(usuario: Usuario) -> int:
    """Retorna quantos dias faltam para a assinatura vencer"""
    if usuario.plano == "trial" or not usuario.data_vencimento_assinatura:
        return 0
    
    agora = datetime.now(timezone.utc)
    delta = usuario.data_vencimento_assinatura - agora
    return max(0, delta.days)


def status_assinatura(usuario: Usuario) -> dict:
    """Retorna informações completas sobre o status da assinatura"""
    agora = datetime.now(timezone.utc)
    
    # ADMIN TEM ACESSO ILIMITADO
    if usuario.perfil == "admin":
        return {
            "email_verificado": True,
            "plano": "admin",
            "plano_nome": "ADMINISTRADOR",
            "plano_ativo": True,
            "status": "ativo",
            "tipo": "admin",
            "acesso_ilimitado": True,
            "mensagem": "Acesso administrativo total"
        }
    
    resultado = {
        "email_verificado": usuario.email_verificado,
        "plano": usuario.plano,
        "plano_ativo": usuario.plano_ativo,
        "status": "ativo"
    }
    
    # Trial
    if usuario.plano == "trial":
        dias_restantes = dias_restantes_trial(usuario)
        resultado.update({
            "tipo": "trial",
            "data_fim": usuario.data_fim_trial.isoformat(),
            "dias_restantes": dias_restantes,
            "expirando": dias_restantes <= 3,
            "expirado": agora > usuario.data_fim_trial
        })
        
        if agora > usuario.data_fim_trial:
            resultado["status"] = "expirado"
    
    # Assinatura paga
    else:
        if usuario.data_vencimento_assinatura:
            dias_restantes = dias_restantes_assinatura(usuario)
            resultado.update({
                "tipo": "assinatura",
                "data_vencimento": usuario.data_vencimento_assinatura.isoformat(),
                "dias_restantes": dias_restantes,
                "vencendo": dias_restantes <= 7,
                "vencido": agora > usuario.data_vencimento_assinatura
            })
            
            if agora > usuario.data_vencimento_assinatura:
                resultado["status"] = "vencido"
        else:
            resultado["status"] = "inativo"
    
    return resultado
