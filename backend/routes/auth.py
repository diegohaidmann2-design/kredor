"""
Rotas de Autenticação
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.auth")

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel
from datetime import datetime, timezone

from config import db
from models.usuario import (
    Usuario, LoginRequest, LoginResponse, UsuarioCreate, UsuarioPublico,
    EmailNormalizado, normalizar_email,
)
from services.auth import (
    hash_senha, verificar_senha, criar_tokens, get_current_user,
    refresh_access_token, revogar_token,
    encerrar_sessao, jti_do_token, registrar_sessao,
    validar_forca_senha,
)
from services.auditoria import registrar_auditoria
from services.turnstile_service import verificar_turnstile, turnstile_habilitado
import secrets
from services.brute_force_service import (
        verificar_bloqueio, registrar_tentativa_falha, registrar_sucesso,
        verificar_bloqueio_ip, registrar_tentativa_falha_ip, registrar_sucesso_ip,
        extrair_ip,
    )
from services.permissao_service import permissao_service
from models.two_factor import TwoFactorVerifyRequest
from services.two_factor_service import validar_codigo_2fa
from services.two_factor_service import criar_codigo_2fa, enviar_codigo_2fa_email, verificar_rate_limit_2fa
from services.two_factor_service import alternar_2fa_usuario
from services.notificacao_service import notificar_novo_usuario
from services.email_service import enviar_email_async, email_verificacao
from fastapi.responses import HTMLResponse

router = APIRouter()


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/registro", response_model=Usuario)
async def registrar(dados: UsuarioCreate, background_tasks: BackgroundTasks, request: Request):
    """Registra um novo usuário com plano trial e envia email de verificação"""

    # 🛡️ Proteção anti-bot (Cloudflare Turnstile) — validada no backend
    if turnstile_habilitado():
        ip = extrair_ip(request)
        ok, erros = await verificar_turnstile(dados.turnstile_token or "", ip)
        if not ok:
            logger.error(f"⚠️ [Turnstile] Registro bloqueado: {erros}")
            raise HTTPException(
                status_code=400,
                detail="Verificação de segurança falhou. Refaça o desafio e tente novamente."
            )

    # Fix #1: Rate limit no registro (reutiliza o mesmo mecanismo do login)
    bloqueado, segundos = await verificar_bloqueio(f"registro:{dados.email}")
    if bloqueado:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas de registro. Tente novamente em {segundos // 60 + 1} minuto(s)."
        )

    # Política única do sistema (services/auth.validar_forca_senha): mesma régua do convite de
    # membro, do aceite de convite e da troca de senha.
    validar_forca_senha(dados.senha, dados.email)

    # Verificar se email já existe
    existing = await db.usuarios.find_one({"email": dados.email})
    if existing:
        await registrar_tentativa_falha(f"registro:{dados.email}")
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Gerar token de verificação
    verification_token = secrets.token_urlsafe(32)
    
    # Criar usuário com perfil 'usuario' e plano 'trial' por padrão
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        perfil="usuario",
        plano="trial",  # Plano trial gratuito
        plano_ativo=True,  # Trial começa ativo
        email_verificado=False,
        email_verification_token=verification_token,
        email_verification_sent_at=datetime.now(timezone.utc)
    )
    
    doc = usuario.model_dump()
    doc["senha_hash"] = hash_senha(dados.senha)
    if "senha" in doc:
        del doc["senha"]
        
    doc["created_at"] = doc["created_at"].isoformat()
    doc["data_inicio_trial"] = doc["data_inicio_trial"].isoformat()
    doc["data_fim_trial"] = doc["data_fim_trial"].isoformat()
    if doc.get("email_verification_sent_at"):
        doc["email_verification_sent_at"] = doc["email_verification_sent_at"].isoformat()
    
    await db.usuarios.insert_one(doc)
    
    # Criar notificações (boas-vindas + alerta para admins)
    try:
        await notificar_novo_usuario(usuario.id, usuario.nome, usuario.email)
    except Exception as e:
        logger.error(f"Erro ao criar notificações: {e}")
    
    # Enviar email de verificação
    try:
        html, texto = email_verificacao(usuario.nome, usuario.email, verification_token)
        background_tasks.add_task(enviar_email_async, usuario.email, "Confirme seu email - Kredor", html, texto)
    except Exception as e:
        logger.error(f"Erro ao enviar email de verificação: {e}")
    
    return usuario


@router.post("/login")
async def login(dados: LoginRequest, request: Request):
    """
    Realiza login do usuário e retorna access + refresh tokens
    Se 2FA estiver ativo, envia código por email e retorna requires_2fa=true
    
    Returns:
        {
            "requires_2fa": true,  # Se 2FA estiver ativo
            "email": "user@example.com"
        }
        
        OU (se 2FA desativado):
        
        {
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "bearer",
            "usuario": {...}
        }
    """

    ip = extrair_ip(request)

    # 🛡️ Proteção anti-bot (Cloudflare Turnstile) — validada no backend
    if turnstile_habilitado():
        ok_ts, erros_ts = await verificar_turnstile(dados.turnstile_token or "", ip)
        if not ok_ts:
            logger.error(f"⚠️ [Turnstile] Login bloqueado: {erros_ts}")
            raise HTTPException(
                status_code=400,
                detail="Verificação de segurança falhou. Refaça o desafio e tente novamente."
            )

    # 1) Proteção por IP (anti credential-stuffing / automação)
    ip_bloqueado, ip_segundos = await verificar_bloqueio_ip(ip)
    if ip_bloqueado:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas a partir do seu IP. Tente novamente em {ip_segundos // 60 + 1} minuto(s)."
        )

    # 2) Proteção por conta (brute force direcionado)
    bloqueado, segundos = await verificar_bloqueio(dados.email)
    if bloqueado:
        minutos = segundos // 60
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas falhas. Conta bloqueada por {minutos} minuto(s). Tente novamente mais tarde."
        )
    
    logger.info(f"🔍 Tentativa de login: {dados.email}")
    usuario = await db.usuarios.find_one({"email": dados.email}, {"_id": 0})
    
    if not usuario:
        logger.error(f"❌ Usuário não encontrado: {dados.email}")
        await registrar_tentativa_falha(dados.email, ip)
        await registrar_tentativa_falha_ip(ip)
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    stored_hash = usuario.get("senha_hash") or ""

    # Se ainda não encontrou hash valido, falhar
    if not stored_hash or not verificar_senha(dados.senha, stored_hash):
        logger.error(f"❌ Senha inválida para: {dados.email}")
        await registrar_tentativa_falha(dados.email, ip)
        await registrar_tentativa_falha_ip(ip)
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if not usuario.get("ativo", True):
        raise HTTPException(status_code=401, detail="Usuário inativo")
    
    # TRIAL pode fazer login mesmo sem verificar (será redirecionado no frontend)
    
    # Bloquear apenas planos PAGOS com pagamento pendente
    if (usuario.get("payment_status") == "pending" and 
        not usuario.get("plano_ativo", False) and 
        usuario.get("plano") != "trial"):
        raise HTTPException(
            status_code=402,  # Payment Required
            detail="Pagamento pendente. Complete o pagamento para acessar sua conta."
        )
    
    # Login bem-sucedido - limpar tentativas
    await registrar_sucesso(dados.email)
    await registrar_sucesso_ip(ip)
    
    # Verificar se 2FA está ativo
    if usuario.get("two_factor_enabled", False):
        
        # Verificar rate limiting
        pode_enviar, segundos_restantes = await verificar_rate_limit_2fa(usuario["id"])
        if not pode_enviar:
            raise HTTPException(
                status_code=429,
                detail=f"Por favor, aguarde {segundos_restantes} segundos antes de solicitar um novo código"
            )
        
        # Criar e enviar código 2FA
        codigo = await criar_codigo_2fa(usuario["id"])
        enviado = await enviar_codigo_2fa_email(usuario["email"], usuario["nome"], codigo)
        
        if not enviado:
            raise HTTPException(
                status_code=500,
                detail="Erro ao enviar código de verificação. Tente novamente."
            )
        
        return {
            "requires_2fa": True,
            "email": usuario["email"],
            "message": "Código de verificação enviado para seu email"
        }
    
    # 2FA desativado - login normal
    # Criar access token e refresh token
    access_token, refresh_token = criar_tokens(usuario["id"])

    # Uma conta, um acesso por vez: este login passa a ser a única sessão válida e derruba a
    # anterior. Para duas pessoas ao mesmo tempo, o dono cadastra um membro em Minha Equipe.
    await registrar_sessao(
        usuario["id"], jti_do_token(access_token),
        ip=extrair_ip(request), dispositivo=request.headers.get("user-agent"),
    )
    
    usuario["created_at"] = datetime.fromisoformat(usuario["created_at"])
    usuario_obj = Usuario(**{k: v for k, v in usuario.items() if k != "senha"})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "usuario": usuario_obj,
        # Mantém compatibilidade com frontend antigo
        "token": access_token
    }


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh(request: RefreshTokenRequest):
    """
    Gera novo access token usando refresh token
    
    Body:
        {
            "refresh_token": "..."
        }
    
    Returns:
        {
            "access_token": "...",
            "token_type": "bearer"
        }
    """
    new_access_token = await refresh_access_token(request.refresh_token)
    return RefreshTokenResponse(access_token=new_access_token)


@router.post("/logout")
async def logout(current_user: Usuario = Depends(get_current_user)):
    """
    Faz logout revogando os tokens do usuário
    
    Nota: Requer que o frontend envie o JTI do token no header
    ou armazene localmente para revogar
    """
    # Encerra a sessão da conta: o token que ficou no navegador deixa de ser aceito, e não só
    # é apagado do lado do cliente.
    await encerrar_sessao(current_user.id)

    return {"message": "Logout realizado com sucesso"}


@router.get("/me", response_model=UsuarioPublico)
async def me(current_user: Usuario = Depends(get_current_user)):
    """Retorna dados do usuário atual (sem campos sensíveis)"""
    return UsuarioPublico(**current_user.model_dump())


class AtualizarPerfilRequest(BaseModel):
    """Campos que o próprio usuário pode alterar no seu perfil.

    O email não entra: é a identidade de login (índice único, usado para recuperar senha e
    para o 2FA). Trocá-lo exige reverificação e liberaria tomar a conta de alguém digitando o
    email dele — é fluxo próprio, não um campo de formulário.

    O cargo também não: quem define a função de um membro é o dono, em Minha Equipe. Se o
    membro pudesse editar o próprio cargo, o campo deixaria de significar algo.
    """
    nome: str


@router.put("/me", response_model=UsuarioPublico)
async def atualizar_meu_perfil(
    dados: AtualizarPerfilRequest,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
):
    """Atualiza o perfil do usuário logado.

    A tela de perfil tinha "Editar Perfil" e "Salvar" desde sempre, com o handler vazio e sem
    rota nenhuma por trás: o nome digitado sumia na frente do usuário, sem erro.
    """
    nome = (dados.nome or "").strip()
    if len(nome) < 2:
        raise HTTPException(status_code=422, detail="O nome deve ter pelo menos 2 caracteres.")
    if len(nome) > 120:
        raise HTTPException(status_code=422, detail="O nome deve ter no máximo 120 caracteres.")

    nome_anterior = current_user.nome
    if nome == nome_anterior:
        return UsuarioPublico(**current_user.model_dump())

    await db.usuarios.update_one(
        {"id": current_user.id},
        {"$set": {"nome": nome, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )

    # O nome aparece no convite de equipe, nos contratos e nos recibos: a troca é relevante
    # para quem audita a conta depois.
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="atualizar",
        entidade="perfil",
        entidade_id=current_user.id,
        detalhes=f"Alterou o nome de \"{nome_anterior}\" para \"{nome}\"",
        dados_anteriores={"nome": nome_anterior},
        dados_novos={"nome": nome},
        ip=extrair_ip(request),
    )

    atualizado = await db.usuarios.find_one({"id": current_user.id}, {"_id": 0})
    atualizado["created_at"] = datetime.fromisoformat(atualizado["created_at"])
    return UsuarioPublico(**atualizado)


@router.post("/verificar-email/{token}")
async def verificar_email(token: str):
    """Verifica email do usuário via token (API)"""
    logger.info(f"DEBUG: Tentando verificar token: {token}")
    usuario_doc = await db.usuarios.find_one({"email_verification_token": token})
    
    if not usuario_doc:
        logger.info(f"DEBUG: Token nao encontrado no banco: {token}")
        # Tentar buscar qualquer usuario para ver se o token existe em outro campo ou formato (debug apenas)
        count = await db.usuarios.count_documents({})
        logger.info(f"DEBUG: Total usuarios no banco: {count}")
        raise HTTPException(status_code=404, detail="Token inválido ou expirado")
    
    logger.info(f"DEBUG: Token valido encontrado para usuario: {usuario_doc.get('email')}")
    
    # Atualizar usuário
    await db.usuarios.update_one(
        {"_id": usuario_doc["_id"]},
        {"$set": {
            "email_verificado": True,
            "email_verification_token": None
        }}
    )
    
    return {"message": "Email verificado com sucesso!"}


@router.get("/verificar-email/{token}")
async def verificar_email_get(token: str):
    """Verifica email do usuário via token (Link direto do Email)"""
    try:
        # Reutilizar lógica ou chamar função interna
        usuario_doc = await db.usuarios.find_one({"email_verification_token": token})
        
        if not usuario_doc:
             return HTMLResponse(content="""
                <html>
                    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                        <h1 style="color: #ef4444;">Link Inválido ou Expirado</h1>
                        <p>O link de verificação não é válido ou já foi utilizado.</p>
                        <a href="/">Voltar para Home</a>
                    </body>
                </html>
             """, status_code=404)
        
        # Atualizar usuário
        await db.usuarios.update_one(
            {"_id": usuario_doc["_id"]},
            {"$set": {
                "email_verificado": True,
                "email_verification_token": None
            }}
        )
        
        # Retornar página de sucesso HTML
        return HTMLResponse(content="""
            <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #10b981;">Email Verificado com Sucesso! 🎉</h1>
                    <p>Sua conta foi ativada.</p>
                    <p>Você já pode fechar esta janela ou clicar abaixo para entrar.</p>
                    <a href="/login" style="background-color: #10b981; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ir para Login</a>
                </body>
            </html>
        """)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verificar-status-email")
async def verificar_status_email(
    email: str,
    current_user: Usuario = Depends(get_current_user)  # Fix #2: requer autenticação
):
    """Verifica se o email de um usuário já foi verificado (requer auth)"""
    email = normalizar_email(email)
    usuario = await db.usuarios.find_one({"email": email}, {"_id": 0, "email_verificado": 1, "email": 1})
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return {
        "email": usuario["email"],
        "verificado": usuario.get("email_verificado", False)
    }


class ReenviarVerificacaoRequest(BaseModel):
    email: EmailNormalizado


@router.post("/reenviar-verificacao")
async def reenviar_verificacao(dados: ReenviarVerificacaoRequest, background_tasks: BackgroundTasks):
    """
    Reenvia email de verificação (Endpoint público)
    Requer email no corpo da requisição
    """
    # Buscar usuário
    usuario = await db.usuarios.find_one({"email": dados.email})
    
    # Por segurança, sempre retornar sucesso mesmo se não achar usuário (evitar enumeração)
    # Mas se usuário já verificado, podemos avisar
    if not usuario:
        # Retorna sucesso fake para não expor e-mails não cadastrados
        return {"message": "Se o email estiver cadastrado, um novo link será enviado."}
    
    if usuario.get("email_verificado", False):
        return {"message": "Email já verificado. Faça login na sua conta."}
    
    # Gerar novo token
    verification_token = secrets.token_urlsafe(32)
    
    # Fix #5: remover debug print com token sensível
    await db.usuarios.update_one(
        {"_id": usuario["_id"]},
        {"$set": {
            "email_verification_token": verification_token,
            "email_verification_sent_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Enviar email
    try:
        html, texto = email_verificacao(usuario["nome"], usuario["email"], verification_token)
        background_tasks.add_task(enviar_email_async, usuario["email"], "Confirme seu email - Kredor", html, texto)
        
        return {"message": "Processamento de reenvio de e-mail iniciado. Confira sua caixa de entrada em instantes."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao reenviar email para {dados.email}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar reenvio de e-mail")


@router.get("/permissoes")
async def obter_permissoes(current_user: Usuario = Depends(get_current_user)):
    """
    Retorna as permissões e limites do usuário atual.
    Admin tem acesso total a tudo.
    """
    return await permissao_service.obter_resumo_permissoes(current_user)



# ============================================================
# ENDPOINTS DE AUTENTICAÇÃO DE DOIS FATORES (2FA)
# ============================================================

@router.post("/verify-2fa")
async def verify_2fa(dados: dict):
    """
    Verifica o código 2FA fornecido após o login
    
    Body:
        {
            "email": "user@example.com",
            "codigo": "123456"
        }
    
    Returns:
        {
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "bearer",
            "usuario": {...}
        }
    """
    
    email = dados.get("email")
    codigo = dados.get("codigo")
    email = normalizar_email(email)
    
    if not email or not codigo:
        raise HTTPException(status_code=400, detail="Email e código são obrigatórios")
    
    # Buscar usuário
    usuario = await db.usuarios.find_one({"email": email}, {"_id": 0})
    
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    
    # Validar código
    sucesso, mensagem = await validar_codigo_2fa(usuario["id"], codigo)
    
    if not sucesso:
        raise HTTPException(status_code=401, detail=mensagem)
    
    # Código válido - criar tokens
    access_token, refresh_token = criar_tokens(usuario["id"])
    await registrar_sessao(usuario["id"], jti_do_token(access_token))
    
    usuario["created_at"] = datetime.fromisoformat(usuario["created_at"])
    usuario_obj = Usuario(**{k: v for k, v in usuario.items() if k != "senha"})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "usuario": usuario_obj,
        "token": access_token
    }


@router.post("/resend-2fa")
async def resend_2fa(dados: dict):
    """
    Reenvia código 2FA por email
    
    Body:
        {
            "email": "user@example.com"
        }
    
    Returns:
        {
            "message": "Código reenviado com sucesso"
        }
    """
    
    email = dados.get("email")
    
    email = normalizar_email(email)
    if not email:
        raise HTTPException(status_code=400, detail="Email é obrigatório")
    
    # Fix #4: resend-2fa não deve revelar se usuário existe
    # Buscar usuário
    usuario = await db.usuarios.find_one({"email": email}, {"_id": 0})
    
    if not usuario or not usuario.get("two_factor_enabled", False):
        # Resposta genérica — não revela se o email existe ou se 2FA está ativo
        raise HTTPException(
            status_code=400,
            detail="Não foi possível reenviar o código. Verifique o email e tente novamente."
        )
    
    # Verificar rate limiting
    pode_enviar, segundos_restantes = await verificar_rate_limit_2fa(usuario["id"])
    if not pode_enviar:
        raise HTTPException(
            status_code=429,
            detail=f"Por favor, aguarde {segundos_restantes} segundos antes de solicitar um novo código"
        )
    
    # Criar e enviar código
    codigo = await criar_codigo_2fa(usuario["id"])
    enviado = await enviar_codigo_2fa_email(usuario["email"], usuario["nome"], codigo)
    
    if not enviado:
        raise HTTPException(
            status_code=500,
            detail="Erro ao enviar código. Tente novamente."
        )
    
    return {
        "message": "Código reenviado com sucesso",
        "email": email
    }


@router.post("/toggle-2fa")
async def toggle_2fa(dados: dict, current_user: Usuario = Depends(get_current_user)):
    """
    Ativa ou desativa 2FA para o usuário atual
    Requer confirmação de senha (campos: enabled bool e a senha atual do usuário)
    
    Returns:
        {
            "message": "2FA ativado com sucesso",
            "two_factor_enabled": true
        }
    """
    
    enabled = dados.get("enabled")
    senha = dados.get("senha")
    
    if enabled is None or not senha:
        raise HTTPException(status_code=400, detail="'enabled' e 'senha' são obrigatórios")
    
    # Buscar usuário completo (com senha)
    usuario_doc = await db.usuarios.find_one({"id": current_user.id}, {"_id": 0})
    
    if not usuario_doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Verificar senha
    stored_hash = usuario_doc.get("senha_hash") or ""
    if not stored_hash or not verificar_senha(senha, stored_hash):
        raise HTTPException(status_code=401, detail="Senha incorreta")
    
    # Alternar 2FA
    sucesso = await alternar_2fa_usuario(current_user.id, enabled)
    
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao alterar configuração de 2FA")
    
    acao = "ativado" if enabled else "desativado"
    
    return {
        "message": f"2FA {acao} com sucesso",
        "two_factor_enabled": enabled
    }


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str


@router.post("/alterar-senha")
async def alterar_senha(dados: AlterarSenhaRequest, current_user: Usuario = Depends(get_current_user)):
    """
    Altera a senha do usuário atual
    """
    # Buscar usuário completo para obter o hash da senha
    usuario_doc = await db.usuarios.find_one({"id": current_user.id})
    if not usuario_doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Verificar senha atual
    stored_hash = usuario_doc.get("senha_hash") or ""
    if not stored_hash or not verificar_senha(dados.senha_atual, stored_hash):
        raise HTTPException(status_code=401, detail="Senha atual incorreta")
    
    validar_forca_senha(dados.nova_senha, current_user.email, campo="nova senha")

    if verificar_senha(dados.nova_senha, stored_hash):
        raise HTTPException(status_code=422, detail="A nova senha deve ser diferente da atual.")

    # Atualizar para a nova senha
    nova_senha_hash = hash_senha(dados.nova_senha)
    await db.usuarios.update_one(
        {"id": current_user.id},
        {"$set": {"senha_hash": nova_senha_hash}}
    )
    
    return {"message": "Senha alterada com sucesso"}


@router.get("/2fa-status")
async def get_2fa_status(current_user: Usuario = Depends(get_current_user)):
    """
    Retorna o status atual do 2FA do usuário
    
    Returns:
        {
            "two_factor_enabled": true,
            "two_factor_activated_at": "2026-01-22T10:30:00Z"
        }
    """
    usuario_doc = await db.usuarios.find_one(
        {"id": current_user.id},
        {"_id": 0, "two_factor_enabled": 1, "two_factor_activated_at": 1}
    )
    
    if not usuario_doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return {
        "two_factor_enabled": usuario_doc.get("two_factor_enabled", False),
        "two_factor_activated_at": usuario_doc.get("two_factor_activated_at")
    }
