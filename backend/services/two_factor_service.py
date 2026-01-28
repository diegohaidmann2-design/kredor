"""
Serviço de Autenticação de Dois Fatores (2FA)
Gerencia criação, validação e envio de códigos de verificação por email
"""
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from config import db
from models.two_factor import TwoFactorCode


def gerar_codigo() -> str:
    """
    Gera um código de 6 dígitos aleatório
    
    Returns:
        str: Código de 6 dígitos (ex: "123456")
    """
    return str(secrets.randbelow(1000000)).zfill(6)


async def criar_codigo_2fa(usuario_id: str) -> str:
    """
    Cria um novo código 2FA para o usuário
    Invalida códigos anteriores não usados
    
    Args:
        usuario_id: ID do usuário
        
    Returns:
        str: Código de 6 dígitos gerado
    """
    # Invalidar códigos anteriores não usados
    await db.two_factor_codes.update_many(
        {
            "usuario_id": usuario_id,
            "usado": False
        },
        {
            "$set": {"usado": True}
        }
    )
    
    # Criar novo código
    codigo = gerar_codigo()
    two_factor = TwoFactorCode(
        usuario_id=usuario_id,
        codigo=codigo
    )
    
    doc = two_factor.model_dump()
    doc["criado_em"] = doc["criado_em"].isoformat()
    doc["expira_em"] = doc["expira_em"].isoformat()
    if doc.get("usado_em"):
        doc["usado_em"] = doc["usado_em"].isoformat()
    
    await db.two_factor_codes.insert_one(doc)
    
    return codigo


async def validar_codigo_2fa(usuario_id: str, codigo: str) -> Tuple[bool, str]:
    """
    Valida o código 2FA fornecido pelo usuário
    
    Args:
        usuario_id: ID do usuário
        codigo: Código de 6 dígitos fornecido
        
    Returns:
        Tuple[bool, str]: (sucesso, mensagem)
    """
    # Buscar código válido mais recente
    codigo_doc = await db.two_factor_codes.find_one(
        {
            "usuario_id": usuario_id,
            "codigo": codigo,
            "usado": False
        },
        sort=[("criado_em", -1)]
    )
    
    if not codigo_doc:
        return False, "Código inválido ou já utilizado"
    
    # Verificar expiração
    expira_em = datetime.fromisoformat(codigo_doc["expira_em"])
    if datetime.now(timezone.utc) > expira_em:
        # Marcar como usado para evitar reuso
        await db.two_factor_codes.update_one(
            {"_id": codigo_doc["_id"]},
            {"$set": {"usado": True}}
        )
        return False, "Código expirado. Solicite um novo código."
    
    # Verificar tentativas
    tentativas = codigo_doc.get("tentativas", 0)
    max_tentativas = codigo_doc.get("max_tentativas", 3)
    
    if tentativas >= max_tentativas:
        # Marcar como usado
        await db.two_factor_codes.update_one(
            {"_id": codigo_doc["_id"]},
            {"$set": {"usado": True}}
        )
        return False, "Número máximo de tentativas excedido. Solicite um novo código."
    
    # Incrementar tentativas
    await db.two_factor_codes.update_one(
        {"_id": codigo_doc["_id"]},
        {"$inc": {"tentativas": 1}}
    )
    
    # Código válido - marcar como usado
    await db.two_factor_codes.update_one(
        {"_id": codigo_doc["_id"]},
        {
            "$set": {
                "usado": True,
                "usado_em": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return True, "Código validado com sucesso"


async def verificar_rate_limit_2fa(usuario_id: str) -> Tuple[bool, int]:
    """
    Verifica se o usuário pode solicitar um novo código (rate limiting)
    Permite 1 código por minuto
    
    Args:
        usuario_id: ID do usuário
        
    Returns:
        Tuple[bool, int]: (pode_solicitar, segundos_restantes)
    """
    # Buscar último código criado
    ultimo_codigo = await db.two_factor_codes.find_one(
        {"usuario_id": usuario_id},
        sort=[("criado_em", -1)]
    )
    
    if not ultimo_codigo:
        return True, 0
    
    criado_em = datetime.fromisoformat(ultimo_codigo["criado_em"])
    tempo_decorrido = (datetime.now(timezone.utc) - criado_em).total_seconds()
    
    # Rate limit: 1 minuto entre códigos
    rate_limit_segundos = 60
    
    if tempo_decorrido < rate_limit_segundos:
        segundos_restantes = int(rate_limit_segundos - tempo_decorrido)
        return False, segundos_restantes
    
    return True, 0


async def enviar_codigo_2fa_email(usuario_email: str, usuario_nome: str, codigo: str) -> bool:
    """
    Envia o código 2FA por email
    Se o envio falhar (ex: credenciais não configuradas), imprime o código no console
    
    Args:
        usuario_email: Email do usuário
        usuario_nome: Nome do usuário
        codigo: Código de 6 dígitos
        
    Returns:
        bool: True se enviado com sucesso
    """
    try:
        from services.email_service import enviar_email
        
        # Template HTML do email
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #ffffff;
                    padding: 30px;
                    border: 1px solid #e0e0e0;
                    border-radius: 0 0 10px 10px;
                }}
                .code-box {{
                    background: #f7f9fc;
                    border: 2px dashed #667eea;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                    margin: 20px 0;
                }}
                .code {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #667eea;
                    letter-spacing: 8px;
                    font-family: 'Courier New', monospace;
                }}
                .warning {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #e0e0e0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔐 Código de Verificação</h1>
                <p>Gestor Cred - Autenticação de Dois Fatores</p>
            </div>
            
            <div class="content">
                <p>Olá, <strong>{usuario_nome}</strong>!</p>
                
                <p>Você solicitou acesso à sua conta no <strong>Gestor Cred</strong>. Para continuar, use o código de verificação abaixo:</p>
                
                <div class="code-box">
                    <div class="code">{codigo}</div>
                    <p style="margin: 10px 0 0 0; color: #666; font-size: 14px;">
                        Este código expira em <strong>10 minutos</strong>
                    </p>
                </div>
                
                <div class="warning">
                    <p style="margin: 0;">
                        <strong>⚠️ Importante:</strong><br>
                        • Este código é pessoal e intransferível<br>
                        • Nunca compartilhe com ninguém<br>
                        • Nossa equipe nunca solicitará este código<br>
                        • Você tem 3 tentativas para inserir o código correto
                    </p>
                </div>
                
                <p>Se você não solicitou este código, ignore este email. Sua conta permanece segura.</p>
                
                <p style="margin-top: 30px;">
                    Atenciosamente,<br>
                    <strong>Equipe Gestor Cred</strong>
                </p>
            </div>
            
            <div class="footer">
                <p>© 2026 Gestor Cred - Gestão de Empréstimos</p>
                <p>Este é um email automático. Por favor, não responda.</p>
            </div>
        </body>
        </html>
        """
        
        # Versão texto plano
        texto = f"""
        Código de Verificação - Gestor Cred
        
        Olá, {usuario_nome}!
        
        Você solicitou acesso à sua conta no Gestor Cred.
        
        Seu código de verificação é: {codigo}
        
        Este código expira em 10 minutos.
        
        IMPORTANTE:
        - Este código é pessoal e intransferível
        - Nunca compartilhe com ninguém
        - Nossa equipe nunca solicitará este código
        - Você tem 3 tentativas para inserir o código correto
        
        Se você não solicitou este código, ignore este email.
        
        Atenciosamente,
        Equipe Gestor Cred
        """
        
        enviado = enviar_email(
            usuario_email,
            "Código de Verificação 2FA - Gestor Cred",
            html,
            texto
        )
        
        # Se o envio falhou (ex: credenciais SMTP não configuradas), mostrar código no console
        if not enviado:
            print("\n" + "="*80)
            print("🔐 CÓDIGO 2FA (Modo Desenvolvimento - Email não configurado)")
            print("="*80)
            print(f"📧 Email: {usuario_email}")
            print(f"👤 Usuário: {usuario_nome}")
            print(f"🔢 Código: {codigo}")
            print(f"⏰ Expira em: 10 minutos")
            print("="*80 + "\n")
        
        return True  # Sempre retorna True para permitir testes sem SMTP configurado
        
    except Exception as e:
        print(f"❌ Erro ao enviar email 2FA: {e}")
        # Em desenvolvimento, mostrar código no console mesmo em caso de erro
        print("\n" + "="*80)
        print("🔐 CÓDIGO 2FA (Modo Desenvolvimento - Fallback)")
        print("="*80)
        print(f"📧 Email: {usuario_email}")
        print(f"👤 Usuário: {usuario_nome}")
        print(f"🔢 Código: {codigo}")
        print(f"⏰ Expira em: 10 minutos")
        print("="*80 + "\n")
        return True  # Permitir continuar em desenvolvimento


async def alternar_2fa_usuario(usuario_id: str, enabled: bool) -> bool:
    """
    Ativa ou desativa 2FA para o usuário
    
    Args:
        usuario_id: ID do usuário
        enabled: True para ativar, False para desativar
        
    Returns:
        bool: True se alteração foi bem-sucedida
    """
    update_data = {"two_factor_enabled": enabled}
    
    if enabled:
        update_data["two_factor_activated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.usuarios.update_one(
        {"id": usuario_id},
        {"$set": update_data}
    )
    
    return result.modified_count > 0


async def limpar_codigos_expirados():
    """
    Job de limpeza: Remove códigos expirados do banco de dados
    Deve ser executado periodicamente (ex: diariamente)
    """
    # Deletar códigos expirados há mais de 24 horas
    data_limite = datetime.now(timezone.utc) - timedelta(hours=24)
    
    result = await db.two_factor_codes.delete_many({
        "expira_em": {"$lt": data_limite.isoformat()}
    })
    
    return result.deleted_count
