"""
Serviço de envio de emails via SMTP
Suporta: Gmail, Hostinger, Umbler e outros servidores SMTP
Configurações podem vir do banco de dados ou variáveis de ambiente
"""
import os
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
from typing import Optional
from datetime import datetime

# Configurações padrão do SMTP (fallback para variáveis de ambiente)
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', 'noreply@gestorcred.com.br')
SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'Gestor Cred')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
APP_URL = os.environ.get('APP_URL', 'http://localhost:3000')

# Cache para configurações do banco
_config_cache = None
_config_cache_time = None


async def get_smtp_config():
    """
    Obtém configurações SMTP do banco de dados.
    Se não existir, retorna None e o sistema usará as variáveis de ambiente.
    """
    global _config_cache, _config_cache_time
    from config import db
    
    # Cache de 5 minutos
    if _config_cache_time and (datetime.now() - _config_cache_time).seconds < 300:
        return _config_cache
    
    try:
        config = await db.configuracoes_sistema.find_one({"tipo": "email"})
        if config and config.get("smtp_host") and config.get("smtp_user"):
            _config_cache = config
            _config_cache_time = datetime.now()
            return config
    except:
        pass
    
    return None


# Cache síncrono para configurações
_sync_config_cache = None


def _get_sync_smtp_config():
    """
    Obtém configurações SMTP do banco de forma síncrona.
    Usa pymongo síncrono para não bloquear event loop.
    """
    global _sync_config_cache
    
    # Retornar cache se existir
    if _sync_config_cache:
        return _sync_config_cache
    
    try:
        import os
        from pymongo import MongoClient
        
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'sgej')
        
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        db = client[db_name]
        config = db.configuracoes_sistema.find_one({"tipo": "email"})
        client.close()
        
        if config and config.get("smtp_host") and config.get("smtp_user") and config.get("smtp_password"):
            _sync_config_cache = config
            return config
    except Exception as e:
        print(f"⚠️ Não foi possível carregar config SMTP do banco: {e}")
    
    return None


def enviar_email(
    destinatario: str,
    assunto: str,
    corpo_html: str,
    corpo_texto: Optional[str] = None
) -> bool:
    """
    Envia email via SMTP.
    Tenta usar configurações do banco de dados primeiro, depois fallback para env vars.
    
    Args:
        destinatario: Email do destinatário
        assunto: Assunto do email
        corpo_html: Corpo do email em HTML
        corpo_texto: Corpo alternativo em texto puro (opcional)
    
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    try:
        # Tentar obter config do banco
        config = _get_sync_smtp_config()
        
        # Usar config do banco ou fallback para env vars
        smtp_host = config.get("smtp_host") if config else SMTP_HOST
        smtp_port = config.get("smtp_port", 587) if config else SMTP_PORT
        smtp_user = config.get("smtp_user") if config else SMTP_USER
        smtp_password = config.get("smtp_password") if config else SMTP_PASSWORD
        smtp_from_email = config.get("smtp_from_email") or smtp_user if config else SMTP_FROM_EMAIL
        smtp_from_name = config.get("smtp_from_name", "Gestor Cred") if config else SMTP_FROM_NAME
        smtp_use_tls = config.get("smtp_use_tls", True) if config else SMTP_USE_TLS
        
        # Verificar se temos credenciais válidas
        if not smtp_user or not smtp_password or smtp_user == "seu-email@gmail.com":
            print(f"⚠️ Credenciais SMTP não configuradas. Email para {destinatario} não enviado.")
            return False
        
        # Criar mensagem (Moderno - EmailMessage)
        msg = EmailMessage()
        
        # Headers com encoding automático
        msg['From'] = f'{smtp_from_name} <{smtp_from_email}>'
        msg['To'] = destinatario
        msg['Subject'] = assunto
        
        # Headers RFC Compliance
        domain = 'jurofacil.sistema'
        if '.' in smtp_host:
             parts = smtp_host.split('.')
             if len(parts) >= 2:
                 domain = f"{parts[-2]}.{parts[-1]}"

        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain=domain)
        
        # Corpo da mensagem
        if list(corpo_texto) if corpo_texto else []: # Check if string is not empty
             msg.set_content(corpo_texto)
             msg.add_alternative(corpo_html, subtype='html')
        else:
             msg.set_content(corpo_html, subtype='html')

        
        # Conectar e enviar
        if smtp_use_tls:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        
        print(f"✅ Email enviado para {destinatario}: {assunto}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar email para {destinatario}: {e}")
        return False


async def enviar_email_async(
    destinatario: str,
    assunto: str,
    corpo_html: str,
    corpo_texto: Optional[str] = None
) -> bool:
    """
    Envia email via SMTP (versão assíncrona que usa configurações do banco de dados)
    """
    try:
        # Tentar obter config do banco
        config = await get_smtp_config()
        
        # Usar config do banco ou fallback para env vars
        smtp_host = config.get("smtp_host") if config else SMTP_HOST
        smtp_port = config.get("smtp_port", 587) if config else SMTP_PORT
        smtp_user = config.get("smtp_user") if config else SMTP_USER
        smtp_password = config.get("smtp_password") if config else SMTP_PASSWORD
        smtp_from_email = config.get("smtp_from_email", smtp_user) if config else SMTP_FROM_EMAIL
        smtp_from_name = config.get("smtp_from_name", "Gestor Cred") if config else SMTP_FROM_NAME
        smtp_use_tls = config.get("smtp_use_tls", True) if config else SMTP_USE_TLS
        
        # Criar mensagem (Moderno - EmailMessage)
        msg = EmailMessage()
        msg['From'] = f'{smtp_from_name} <{smtp_from_email}>'
        msg['To'] = destinatario
        msg['Subject'] = assunto
        
        domain = 'jurofacil.sistema'
        if '.' in smtp_host:
             parts = smtp_host.split('.')
             if len(parts) >= 2:
                 domain = f"{parts[-2]}.{parts[-1]}"

        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain=domain)
        
        # Corpo
        if corpo_texto:
            msg.set_content(corpo_texto)
            msg.add_alternative(corpo_html, subtype='html')
        else:
            msg.set_content(corpo_html, subtype='html')
        
        # Conectar e enviar
        if smtp_use_tls:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        
        print(f"✅ Email enviado para {destinatario}: {assunto}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar email para {destinatario}: {e}")
        return False


def template_base(titulo: str, conteudo: str, botao_texto: Optional[str] = None, botao_link: Optional[str] = None) -> str:
    """Template HTML base para emails"""
    
    botao_html = ""
    if botao_texto and botao_link:
        botao_html = f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
            <tr>
                <td align="center">
                    <a href="{botao_link}" 
                       style="background-color: #10b981; color: white; padding: 14px 32px; 
                              text-decoration: none; border-radius: 8px; font-weight: bold;
                              display: inline-block;">
                        {botao_texto}
                    </a>
                </td>
            </tr>
        </table>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background-color: #f3f4f6;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 40px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 30px; text-align: center;">
                                <h1 style="margin: 0; color: white; font-size: 32px; font-weight: bold;">Gestor Cred</h1>
                                <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">Sistema de Gestão de Empréstimos</p>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                <h2 style="margin: 0 0 20px 0; color: #1f2937; font-size: 24px;">{titulo}</h2>
                                <div style="color: #4b5563; font-size: 16px; line-height: 1.6;">
                                    {conteudo}
                                </div>
                                {botao_html}
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                <p style="margin: 0 0 10px 0; color: #6b7280; font-size: 14px;">
                                    © {datetime.now().year} Gestor Cred - Sistema de Gestão de Empréstimos
                                </p>
                                <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                    Este é um email automático, por favor não responda.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    '''


# ===== TEMPLATES DE EMAIL =====

def email_verificacao(nome: str, email: str, token: str) -> tuple[str, str]:
    """Email de verificação de conta"""
    link = f"{APP_URL}/verificar-email/{token}"
    
    conteudo = f'''
    <p>Olá <strong>{nome}</strong>,</p>
    <p>Seja bem-vindo ao Gestor Cred! 🎉</p>
    <p>Para começar a usar o sistema, você precisa confirmar seu email clicando no botão abaixo:</p>
    <p style="margin-top: 30px; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
        <strong>⏰ Você ganhou 7 dias grátis para testar todas as funcionalidades!</strong>
    </p>
    <p style="margin-top: 20px; color: #6b7280; font-size: 14px;">
        Se você não criou esta conta, pode ignorar este email.
    </p>
    <p style="margin-top: 30px; font-size: 14px; color: #6b7280; word-break: break-all;">
        Se o botão não funcionar, cole o link abaixo no seu navegador:<br>
        <a href="{link}" style="color: #6b7280;">{link}</a>
    </p>
    '''
    
    html = template_base(
        titulo="Confirme seu email",
        conteudo=conteudo,
        botao_texto="Confirmar Email",
        botao_link=link
    )
    
    texto = f"""
    Olá {nome},
    
    Seja bem-vindo ao Gestor Cred!
    
    Para começar a usar o sistema, confirme seu email acessando o link:
    {link}
    
    Você ganhou 7 dias grátis para testar!
    
    Se não criou esta conta, ignore este email.
    """
    
    return html, texto


def email_trial_expirando(nome: str, dias_restantes: int) -> tuple[str, str]:
    """Email avisando que o trial está acabando"""
    link = f"{APP_URL}/assinatura"
    
    conteudo = f'''
    <p>Olá <strong>{nome}</strong>,</p>
    <p>Seu período de testes do Gestor Cred está acabando! ⏰</p>
    <p style="font-size: 18px; color: #dc2626; font-weight: bold; margin: 20px 0;">
        Restam apenas {dias_restantes} {'dia' if dias_restantes == 1 else 'dias'}!
    </p>
    <p>Para continuar usando o sistema e não perder seus dados, escolha um plano:</p>
    <ul style="margin: 20px 0; padding-left: 20px;">
        <li><strong>Plano Básico</strong> - R$ 97/mês</li>
        <li><strong>Plano Profissional</strong> - R$ 197/mês (Mais popular)</li>
        <li><strong>Plano Enterprise</strong> - R$ 497/mês</li>
    </ul>
    <p style="color: #6b7280; font-size: 14px;">
        💾 Seus dados estão seguros e serão mantidos mesmo após o trial.
    </p>
    '''
    
    html = template_base(
        titulo=f"Seu trial acaba em {dias_restantes} {'dia' if dias_restantes == 1 else 'dias'}!",
        conteudo=conteudo,
        botao_texto="Ver Planos e Assinar",
        botao_link=link
    )
    
    texto = f"""
    Olá {nome},
    
    Seu período de testes do Gestor Cred está acabando!
    Restam apenas {dias_restantes} {'dia' if dias_restantes == 1 else 'dias'}!
    
    Para continuar usando, escolha um plano:
    {link}
    
    Seus dados estão seguros!
    """
    
    return html, texto


def email_trial_expirado(nome: str) -> tuple[str, str]:
    """Email informando que o trial expirou"""
    link = f"{APP_URL}/assinatura"
    
    conteudo = f'''
    <p>Olá <strong>{nome}</strong>,</p>
    <p>Seu período de testes do Gestor Cred expirou hoje. 😔</p>
    <p style="margin: 20px 0; padding: 15px; background-color: #fee2e2; border-left: 4px solid #dc2626; border-radius: 4px;">
        <strong>⚠️ Seu acesso foi temporariamente bloqueado.</strong>
    </p>
    <p>Mas não se preocupe! Seus dados estão <strong>100% seguros</strong> e serão mantidos.</p>
    <p>Para reativar sua conta e continuar usando, escolha um plano:</p>
    <ul style="margin: 20px 0; padding-left: 20px;">
        <li><strong>Plano Básico</strong> - R$ 97/mês - Até 50 clientes</li>
        <li><strong>Plano Profissional</strong> - R$ 197/mês - Até 200 clientes</li>
        <li><strong>Plano Enterprise</strong> - R$ 497/mês - Ilimitado</li>
    </ul>
    '''
    
    html = template_base(
        titulo="Seu trial expirou",
        conteudo=conteudo,
        botao_texto="Assinar Agora",
        botao_link=link
    )
    
    texto = f"""
    Olá {nome},
    
    Seu período de testes do Gestor Cred expirou.
    Seu acesso foi bloqueado, mas seus dados estão seguros!
    
    Para reativar, assine um plano:
    {link}
    """
    
    return html, texto


def email_assinatura_vencendo(nome: str, plano: str, dias_restantes: int, data_vencimento: str) -> tuple[str, str]:
    """Email avisando que a assinatura está vencendo"""
    link = f"{APP_URL}/assinatura"
    
    conteudo = f'''
    <p>Olá <strong>{nome}</strong>,</p>
    <p>Sua assinatura do <strong>Plano {plano.title()}</strong> está vencendo! ⏰</p>
    <p style="font-size: 18px; color: #dc2626; font-weight: bold; margin: 20px 0;">
        Vence em {dias_restantes} {'dia' if dias_restantes == 1 else 'dias'} ({data_vencimento})
    </p>
    <p>Para garantir que seu acesso não seja interrompido, renove sua assinatura:</p>
    <p style="margin: 20px 0; padding: 15px; background-color: #dbeafe; border-left: 4px solid #3b82f6; border-radius: 4px;">
        💡 <strong>Dica:</strong> Configure a renovação automática e nunca mais se preocupe!
    </p>
    '''
    
    html = template_base(
        titulo="Sua assinatura está vencendo",
        conteudo=conteudo,
        botao_texto="Renovar Assinatura",
        botao_link=link
    )
    
    texto = f"""
    Olá {nome},
    
    Sua assinatura do Plano {plano.title()} está vencendo!
    Vence em {dias_restantes} {'dia' if dias_restantes == 1 else 'dias'} ({data_vencimento})
    
    Renove agora:
    {link}
    """
    
    return html, texto


def email_assinatura_vencida(nome: str, plano: str) -> tuple[str, str]:
    """Email informando que a assinatura venceu"""
    link = f"{APP_URL}/assinatura"
    
    conteudo = f'''
    <p>Olá <strong>{nome}</strong>,</p>
    <p>Sua assinatura do <strong>Plano {plano.title()}</strong> venceu hoje. 😔</p>
    <p style="margin: 20px 0; padding: 15px; background-color: #fee2e2; border-left: 4px solid #dc2626; border-radius: 4px;">
        <strong>⚠️ Seu acesso foi temporariamente bloqueado.</strong>
    </p>
    <p>Seus dados estão <strong>100% seguros</strong>, mas para continuar usando o sistema, você precisa renovar sua assinatura.</p>
    <p>Clique no botão abaixo para reativar:</p>
    '''
    
    html = template_base(
        titulo="Sua assinatura venceu",
        conteudo=conteudo,
        botao_texto="Renovar Agora",
        botao_link=link
    )
    
    texto = f"""
    Olá {nome},
    
    Sua assinatura do Plano {plano.title()} venceu.
    Seu acesso foi bloqueado, mas seus dados estão seguros!
    
    Renove agora:
    {link}
    """
    
    return html, texto


def email_pagamento_confirmado(nome: str, plano: str, valor: float, data_vencimento: str) -> tuple[str, str]:
    """Email confirmando pagamento"""
    link = f"{APP_URL}/assinatura"
    
    conteudo = f'''
    <p>Olá <strong>{nome}</strong>,</p>
    <p>Seu pagamento foi confirmado com sucesso! 🎉</p>
    <div style="margin: 30px 0; padding: 20px; background-color: #d1fae5; border: 2px solid #10b981; border-radius: 8px;">
        <p style="margin: 0 0 10px 0;"><strong>Plano:</strong> {plano.title()}</p>
        <p style="margin: 0 0 10px 0;"><strong>Valor:</strong> R$ {valor:.2f}</p>
        <p style="margin: 0;"><strong>Próximo vencimento:</strong> {data_vencimento}</p>
    </div>
    <p>Obrigado por confiar no Gestor Cred! 💚</p>
    <p style="color: #6b7280; font-size: 14px;">
        Você pode acessar o histórico de pagamentos a qualquer momento no painel de assinatura.
    </p>
    '''
    
    html = template_base(
        titulo="Pagamento confirmado!",
        conteudo=conteudo,
        botao_texto="Acessar Painel",
        botao_link=link
    )
    
    texto = f"""
    Olá {nome},
    
    Seu pagamento foi confirmado! 🎉
    
    Plano: {plano.title()}
    Valor: R$ {valor:.2f}
    Próximo vencimento: {data_vencimento}
    
    Obrigado por confiar no Gestor Cred!
    """
    
    return html, texto



# ==================== TEMPLATES DE REMARKETING ====================

def email_recuperacao_carrinho(
    nome: str,
    plano_nome: str,
    valor: float,
    cupom: Optional[str] = None,
    desconto_percentual: Optional[int] = None
) -> tuple[str, str]:
    """
    Email de recuperação de carrinho abandonado
    Enviado quando usuário não completa o checkout
    """
    link = f"{APP_URL}/checkout"
    
    # Calcular valor com desconto se houver cupom
    valor_final = valor
    economia = 0
    if cupom and desconto_percentual:
        economia = valor * (desconto_percentual / 100)
        valor_final = valor - economia
    
    cupom_html = ""
    if cupom:
        cupom_html = f'''
        <div style="margin: 30px 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 12px; text-align: center;">
            <p style="color: white; font-size: 14px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 1px;">
                🎁 Seu Cupom Exclusivo
            </p>
            <p style="color: white; font-size: 32px; font-weight: bold; margin: 0; font-family: 'Courier New', monospace; 
                       letter-spacing: 3px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2);">
                {cupom}
            </p>
            <p style="color: #e0e7ff; font-size: 18px; margin: 10px 0 0 0; font-weight: bold;">
                {desconto_percentual}% de desconto
            </p>
            <p style="color: #c7d2fe; font-size: 14px; margin: 5px 0 0 0;">
                💰 Economize R$ {economia:.2f}
            </p>
        </div>
        '''
    
    conteudo = f'''
    <p>Olá <strong>{nome}</strong>,</p>
    
    <p>Notamos que você iniciou a assinatura do <strong>Plano {plano_nome}</strong>, 
    mas não finalizou o pagamento. 😔</p>
    
    <p style="margin: 20px 0; font-size: 16px;">
        Não se preocupe! <strong>Reservamos sua vaga</strong> e preparamos uma oferta especial para você:
    </p>
    
    {cupom_html}
    
    <div style="margin: 25px 0; padding: 20px; background-color: #f0f9ff; border-radius: 8px; border-left: 4px solid #3b82f6;">
        <p style="margin: 0; font-size: 16px;"><strong>📦 Resumo do Plano:</strong></p>
        <p style="margin: 10px 0 5px 0; font-size: 15px;">
            Plano {plano_nome}
        </p>
        <p style="margin: 0; font-size: 14px; color: #64748b;">
            {f'<span style="text-decoration: line-through;">De R$ {valor:.2f}</span> por ' if cupom else ''}
            <span style="font-size: 24px; color: #10b981; font-weight: bold;">
                R$ {valor_final:.2f}/mês
            </span>
        </p>
    </div>
    
    <p style="margin: 25px 0; font-size: 15px;">
        <strong>✨ Benefícios que você vai aproveitar:</strong>
    </p>
    <ul style="margin: 10px 0 25px 20px; line-height: 1.8;">
        <li>📊 Gestão completa de empréstimos</li>
        <li>📄 Contratos profissionais em PDF</li>
        <li>💳 Controle total de pagamentos</li>
        <li>📈 Relatórios detalhados</li>
        <li>🤖 Assistente IA para dúvidas</li>
        <li>🔒 Segurança e privacidade garantidas</li>
    </ul>
    
    <p style="margin: 20px 0; padding: 15px; background-color: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
        ⏰ <strong>Atenção:</strong> Esta oferta é válida por apenas <strong>24 horas</strong>!
    </p>
    
    <p style="margin: 20px 0; color: #64748b; font-size: 14px;">
        Tem alguma dúvida? Respondemos este email em menos de 2 horas! 💬
    </p>
    '''
    
    html = template_base(
        titulo="😊 Não desista! Temos uma oferta especial para você",
        conteudo=conteudo,
        botao_texto="🚀 Finalizar Assinatura Agora",
        botao_link=link
    )
    
    texto = f"""
    Olá {nome},
    
    Notamos que você não finalizou sua assinatura do Plano {plano_nome}.
    
    {"🎁 USE O CUPOM: " + cupom + f" e ganhe {desconto_percentual}% de desconto!" if cupom else ""}
    
    Valor: R$ {valor_final:.2f}/mês {"(economize R$ " + f"{economia:.2f})" if cupom else ""}
    
    Finalize agora: {link}
    
    Oferta válida por 24 horas!
    
    Dúvidas? Responda este email.
    """
    
    return html, texto


def email_pix_expirado(
    nome: str,
    plano_nome: str,
    valor: float,
    cupom: Optional[str] = None,
    desconto_percentual: Optional[int] = None
) -> tuple[str, str]:
    """
    Email quando PIX expira sem pagamento
    Oferece nova tentativa com desconto
    """
    link = f"{APP_URL}/checkout"
    
    valor_final = valor
    if cupom and desconto_percentual:
        valor_final = valor - (valor * desconto_percentual / 100)
    
    cupom_html = ""
    if cupom:
        cupom_html = f'''
        <div style="margin: 25px 0; padding: 20px; background-color: #dcfce7; border-radius: 8px; text-align: center;">
            <p style="margin: 0 0 10px 0; font-size: 16px; color: #15803d;">
                🎁 Cupom de Desconto Exclusivo
            </p>
            <p style="margin: 0; font-size: 28px; font-weight: bold; color: #15803d; font-family: monospace;">
                {cupom}
            </p>
            <p style="margin: 10px 0 0 0; font-size: 14px; color: #166534;">
                {desconto_percentual}% OFF - Válido por 48h
            </p>
        </div>
        '''
    
    conteudo = f'''
    <p>Olá <strong>{nome}</strong>,</p>
    
    <p>Seu código PIX para o <strong>Plano {plano_nome}</strong> expirou sem ser pago. 🕐</p>
    
    <p>Mas calma! Sabemos que imprevistos acontecem. Por isso, preparamos uma nova oportunidade ainda melhor:</p>
    
    {cupom_html}
    
    <div style="margin: 20px 0; padding: 15px; background-color: #f0fdf4; border-left: 4px solid #10b981; border-radius: 4px;">
        <p style="margin: 0; font-size: 16px; color: #15803d;">
            <strong>💳 Novo valor:</strong> 
            <span style="font-size: 22px; font-weight: bold;">R$ {valor_final:.2f}/mês</span>
        </p>
    </div>
    
    <p><strong>Formas de pagamento disponíveis:</strong></p>
    <ul style="margin: 10px 0 20px 20px;">
        <li>💵 Novo PIX (gera código na hora)</li>
        <li>💳 Cartão de crédito (parcelamos em até 12x)</li>
    </ul>
    '''
    
    html = template_base(
        titulo="Seu PIX expirou - Gere um novo com desconto!",
        conteudo=conteudo,
        botao_texto="Gerar Novo Pagamento",
        botao_link=link
    )
    
    texto = f"""
    Olá {nome},
    
    Seu código PIX expirou, mas você pode gerar um novo!
    
    {"🎁 USE O CUPOM: " + cupom + f" e ganhe {desconto_percentual}% OFF!" if cupom else ""}
    
    Plano {plano_nome}: R$ {valor_final:.2f}/mês
    
    Gere novo pagamento: {link}
    """
    
    return html, texto


def email_cartao_recusado(
    nome: str,
    plano_nome: str,
    valor: float,
    motivo: str,
    cupom: Optional[str] = None,
    desconto_percentual: Optional[int] = None
) -> tuple[str, str]:
    """
    Email quando cartão é recusado
    Sugere nova tentativa ou PIX com desconto
    """
    link = f"{APP_URL}/checkout"
    
    valor_final = valor
    if cupom and desconto_percentual:
        valor_final = valor - (valor * desconto_percentual / 100)
    
    # Traduzir motivo técnico para mensagem amigável
    motivos_amigaveis = {
        "insufficient_funds": "Saldo insuficiente no cartão",
        "card_disabled": "Cartão bloqueado ou desabilitado",
        "call_issuer": "Entre em contato com seu banco",
        "invalid_card": "Dados do cartão inválidos",
        "expired_card": "Cartão vencido",
        "security_code": "Código de segurança incorreto"
    }
    motivo_amigavel = motivos_amigaveis.get(motivo, motivo)
    
    cupom_html = ""
    if cupom:
        cupom_html = f'''
        <div style="margin: 25px 0; padding: 20px; background-color: #fef3c7; border-radius: 8px; text-align: center;">
            <p style="margin: 0 0 10px 0; font-size: 16px; color: #92400e;">
                🎉 Desconto Especial para Você
            </p>
            <p style="margin: 0; font-size: 28px; font-weight: bold; color: #92400e; font-family: monospace;">
                {cupom}
            </p>
            <p style="margin: 10px 0 0 0; font-size: 14px; color: #78350f;">
                {desconto_percentual}% de desconto
            </p>
        </div>
        '''
    
    conteudo = f'''
    <p>Olá <strong>{nome}</strong>,</p>
    
    <p>Tentamos processar o pagamento do <strong>Plano {plano_nome}</strong>, 
    mas infelizmente o cartão foi recusado. 😔</p>
    
    <div style="margin: 20px 0; padding: 15px; background-color: #fef2f2; border-left: 4px solid #ef4444; border-radius: 4px;">
        <p style="margin: 0; font-size: 14px; color: #991b1b;">
            <strong>Motivo:</strong> {motivo_amigavel}
        </p>
    </div>
    
    <p>Mas não se preocupe! Você pode tentar novamente com estas opções:</p>
    
    <ul style="margin: 15px 0 20px 20px; line-height: 1.8;">
        <li><strong>💳 Outro cartão de crédito</strong> - Tente um cartão diferente</li>
        <li><strong>💵 PIX instantâneo</strong> - Pagamento aprovado na hora</li>
        <li><strong>📞 Contate seu banco</strong> - Eles podem liberar o pagamento</li>
    </ul>
    
    {cupom_html}
    '''.replace("    ", "") # Limpar indentação extra
    
    html = template_base(
        titulo="Pagamento Recusado",
        conteudo=conteudo,
        botao_texto="Tentar Novamente",
        botao_link=link
    )
    
    texto = f"""
    Olá {nome},
    
    O pagamento do Plano {plano_nome} foi recusado.
    Motivo: {motivo_amigavel}
    
    Tente novamente ou use PIX:
    {link}
    """
    
    return html, texto


async def enviar_email_convite(email: str, nome_dono: str, token: str) -> bool:
    """Envia email de convite para membro da equipe"""
    link = f"{APP_URL}/aceitar-convite/{token}"
    
    conteudo = f'''
    <p>Olá!</p>
    <p>Você foi convidado por <strong>{nome_dono}</strong> para fazer parte da equipe no <strong>Gestor Cred</strong>.</p>
    <p>Para aceitar o convite e criar sua senha de acesso, clique no botão abaixo:</p>
    <p style="margin: 20px 0; padding: 15px; background-color: #d1fae5; border-left: 4px solid #10b981; border-radius: 4px;">
        <strong>🚀 Acesso à Área de Membros</strong>
    </p>
    <p>Se você não esperava por este convite, pode ignorar este email.</p>
    '''
    
    html = template_base(
        titulo="Convite para Equipe",
        conteudo=conteudo,
        botao_texto="Aceitar Convite",
        botao_link=link
    )
    
    texto = f"""
    Olá!
    
    Você foi convidado por {nome_dono} para fazer parte da equipe no Gestor Cred.
    
    Para aceitar, acesse:
    {link}
    
    Se não esperava este convite, ignore.
    """
    
    return await enviar_email_async(
        destinatario=email,
        assunto=f"Convite de {nome_dono} - Gestor Cred",
        corpo_html=html,
        corpo_texto=texto
    )


def email_relatorio_semanal_admin(
    periodo: str,
    total_transacoes: int,
    pix_pendentes: int,
    cartoes_recusados: int,
    taxa_conversao: float,
    valor_perdido: float,
    valor_aprovado: float,
    emails_enviados: int,
    cupons_gerados: int,
    recuperacoes: int,
    valor_recuperado: float
) -> tuple[str, str]:
    """
    Relatório semanal automático para admins
    Resume desempenho do sistema de remarketing
    """
    link = f"{APP_URL}/admin/transacoes"
    
    conteudo = f'''
    <h2 style="color: #1e293b; margin-bottom: 20px;">📊 Relatório Semanal de Transações</h2>
    
    <p style="font-size: 14px; color: #64748b; margin-bottom: 30px;">
        Período: <strong>{periodo}</strong>
    </p>
    
    <div style="margin: 25px 0;">
        <h3 style="color: #334155; font-size: 18px; margin-bottom: 15px;">💰 Visão Geral Financeira</h3>
        
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr style="background-color: #dcfce7;">
                <td style="padding: 15px; border: 1px solid #bbf7d0;">
                    <div style="font-size: 14px; color: #15803d;">Valor Aprovado</div>
                    <div style="font-size: 24px; font-weight: bold; color: #15803d;">
                        R$ {valor_aprovado:,.2f}
                    </div>
                </td>
                <td style="padding: 15px; border: 1px solid #fecaca;">
                    <div style="font-size: 14px; color: #991b1b;">Valor Perdido</div>
                    <div style="font-size: 24px; font-weight: bold; color: #991b1b;">
                        R$ {valor_perdido:,.2f}
                    </div>
                </td>
            </tr>
            <tr style="background-color: #dbeafe;">
                <td style="padding: 15px; border: 1px solid #bfdbfe;">
                    <div style="font-size: 14px; color: #1e40af;">Recuperado (Remarketing)</div>
                    <div style="font-size: 24px; font-weight: bold; color: #1e40af;">
                        R$ {valor_recuperado:,.2f}
                    </div>
                </td>
                <td style="padding: 15px; border: 1px solid #e0e7ff;">
                    <div style="font-size: 14px; color: #4338ca;">Taxa de Conversão</div>
                    <div style="font-size: 24px; font-weight: bold; color: #4338ca;">
                        {taxa_conversao:.1f}%
                    </div>
                </td>
            </tr>
        </table>
    </div>
    
    <div style="margin: 25px 0;">
        <h3 style="color: #334155; font-size: 18px; margin-bottom: 15px;">📈 Métricas de Transações</h3>
        
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
            <div style="padding: 15px; background-color: #f1f5f9; border-radius: 8px; text-align: center;">
                <div style="font-size: 14px; color: #64748b;">Total</div>
                <div style="font-size: 28px; font-weight: bold; color: #1e293b;">{total_transacoes}</div>
            </div>
            <div style="padding: 15px; background-color: #fef3c7; border-radius: 8px; text-align: center;">
                <div style="font-size: 14px; color: #92400e;">PIX Pendentes</div>
                <div style="font-size: 28px; font-weight: bold; color: #92400e;">{pix_pendentes}</div>
            </div>
            <div style="padding: 15px; background-color: #fee2e2; border-radius: 8px; text-align: center;">
                <div style="font-size: 14px; color: #991b1b;">Cartões Recusados</div>
                <div style="font-size: 28px; font-weight: bold; color: #991b1b;">{cartoes_recusados}</div>
            </div>
        </div>
    </div>
    
    <div style="margin: 25px 0;">
        <h3 style="color: #334155; font-size: 18px; margin-bottom: 15px;">🎯 Performance do Remarketing</h3>
        
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background-color: #f8fafc;">
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">Emails Enviados</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: bold;">
                    {emails_enviados}
                </td>
            </tr>
            <tr style="background-color: #ffffff;">
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">Cupons Gerados</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: bold;">
                    {cupons_gerados}
                </td>
            </tr>
            <tr style="background-color: #f8fafc;">
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">Recuperações</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: bold; color: #10b981;">
                    {recuperacoes}
                </td>
            </tr>
            <tr style="background-color: #ffffff;">
                <td style="padding: 12px;">Taxa de Recuperação</td>
                <td style="padding: 12px; text-align: right; font-weight: bold; color: #10b981;">
                    {(recuperacoes / emails_enviados * 100) if emails_enviados > 0 else 0:.1f}%
                </td>
            </tr>
        </table>
    </div>
    
    <div style="margin: 30px 0; padding: 20px; background-color: #f0f9ff; border-radius: 8px; border-left: 4px solid #3b82f6;">
        <p style="margin: 0; font-size: 14px; color: #1e40af;">
            💡 <strong>Dica:</strong> Transações com PIX pendente há mais de 24h têm 80% menos chance de conversão. 
            Considere enviar emails de recuperação automaticamente após 2 horas.
        </p>
    </div>
    '''
    
    html = template_base(
        titulo="Relatório Semanal - Sistema de Transações",
        conteudo=conteudo,
        botao_texto="Ver Painel Completo",
        botao_link=link
    )
    
    texto = f"""
    RELATÓRIO SEMANAL - {periodo}
    
    VISÃO GERAL:
    - Total de Transações: {total_transacoes}
    - Taxa de Conversão: {taxa_conversao:.1f}%
    - Valor Aprovado: R$ {valor_aprovado:,.2f}
    - Valor Perdido: R$ {valor_perdido:,.2f}
    
    REMARKETING:
    - Emails Enviados: {emails_enviados}
    - Cupons Gerados: {cupons_gerados}
    - Recuperações: {recuperacoes}
    - Valor Recuperado: R$ {valor_recuperado:,.2f}
    
    Ver mais: {link}
    """
    
    return html, texto

