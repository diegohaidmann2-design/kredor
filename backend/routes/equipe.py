"""
Rotas para Gerenciamento de Equipe (membros da conta do dono).

Um membro é um usuário próprio (id, senha e sessão próprios) vinculado ao dono por
`owner_id`. Ele vê os dados do dono, mas só alcança o que o dono marcou — o que cada
permissão abre está em `services/permissoes_equipe.py`, aplicado centralmente pelo
guardião registrado em `routes/__init__.py`.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from config import db
from models.usuario import EmailNormalizado, Usuario, UsuarioPublico
from services.auditoria import registrar_auditoria
from services.auth import get_current_user, hash_senha, validar_forca_senha
from services.auth_utils import get_user_context, is_owner
from services.brute_force_service import (
    extrair_ip,
    registrar_sucesso,
    registrar_tentativa_falha,
    verificar_bloqueio,
)
from services.email_service import enviar_email_convite
from services.logging_service import get_logger
from services.permissao_service import permissao_service
from services.permissoes_equipe import (
    GERIR_EQUIPE,
    NAO_DELEGAVEIS,
    PERMISSOES_VALIDAS,
    ROTULOS,
    validar_permissoes,
)

logger = get_logger("gestorcred.equipe")

router = APIRouter()

# Validade do convite. Um link que nunca expira é uma credencial permanente circulando por
# email: quem tiver acesso à caixa do convidado abre a conta meses depois. Expirado, o dono
# reenvia (POST /{id}/reenviar-convite) e o token anterior deixa de valer.
CONVITE_VALIDADE_DIAS = 7


# --- Models ---

class ConviteEquipe(BaseModel):
    email: EmailNormalizado
    nome: str
    cargo: str = "Colaborador"
    permissoes: List[str] = []
    senha: Optional[str] = None  # preenchida no cadastro manual; vazia manda convite por email


class AceitarConvite(BaseModel):
    token: str
    senha: str
    nome: Optional[str] = None  # permite confirmar/corrigir o nome


class PermissoesUpdate(BaseModel):
    permissoes: List[str]


# --- Helpers ---

def _pode_gerir_equipe(usuario: Usuario) -> bool:
    """Dono sempre; membro só com a permissão explícita."""
    return is_owner(usuario) or GERIR_EQUIPE in (usuario.permissoes or [])


def _exigir_gestao(usuario: Usuario) -> None:
    if not _pode_gerir_equipe(usuario):
        raise HTTPException(
            status_code=403,
            detail="Você não tem a permissão \"Gerir a equipe\". Peça ao dono da conta.",
        )


def _conferir_delegacao(usuario: Usuario, permissoes: List[str]) -> None:
    """Impede escalação: um membro não concede o que ele mesmo não tem, nem o indelegável.

    Sem isto, quem recebe "Gerir a equipe" cria um colega com acesso total — ou promove a si
    mesmo criando uma conta nova — e a permissão vira um atalho para ser dono.
    """
    if is_owner(usuario):
        return

    proibidas = [p for p in permissoes if p in NAO_DELEGAVEIS]
    if proibidas:
        raise HTTPException(
            status_code=403,
            detail="Somente o dono da conta pode conceder a permissão \"Gerir a equipe\".",
        )

    minhas = set(usuario.permissoes or [])
    excedentes = [p for p in permissoes if p not in minhas]
    if excedentes:
        rotulos = ", ".join(ROTULOS.get(p, p) for p in excedentes)
        raise HTTPException(
            status_code=403,
            detail=f"Você não pode conceder permissão que você não tem: {rotulos}.",
        )


async def _membro_do_dono(membro_id: str, context_id: str) -> dict:
    """Busca o membro dentro da conta de quem pediu. Fora dela, 404 (não 403: não vaza id)."""
    membro = await db.usuarios.find_one({"id": membro_id, "owner_id": context_id})
    if not membro:
        raise HTTPException(status_code=404, detail="Membro não encontrado.")
    return membro


async def _contar_membros(context_id: str) -> int:
    """Conta quem ocupa vaga: ativo ou com convite pendente.

    Desativado não conta — ele não acessa nada, e cobrar vaga por membro desligado deixava a
    conta travada sem nenhuma forma de liberar (não havia como excluir de vez).
    """
    return await db.usuarios.count_documents({
        "owner_id": context_id,
        "$or": [{"ativo": True}, {"convite_pendente": True}],
    })


async def _limite_de_membros(dono: Usuario) -> int:
    """-1 = ilimitado, 0 = o plano não inclui equipe."""
    if permissao_service.tem_acesso_ilimitado(dono):
        return -1
    limites = await permissao_service.obter_limites(dono)
    return getattr(limites, "max_membros", 0)


def _expiracao_convite() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=CONVITE_VALIDADE_DIAS)).isoformat()


def _convite_expirado(usuario: dict) -> bool:
    prazo = usuario.get("convite_expira_em")
    if not prazo:
        # Convites criados antes deste campo: trata pela data de criação, sem brecha aberta.
        prazo = usuario.get("created_at")
    if not prazo:
        return True
    try:
        limite = datetime.fromisoformat(prazo)
    except (TypeError, ValueError):
        return True
    if limite.tzinfo is None:
        limite = limite.replace(tzinfo=timezone.utc)
    if not usuario.get("convite_expira_em"):
        limite = limite + timedelta(days=CONVITE_VALIDADE_DIAS)
    return datetime.now(timezone.utc) > limite


def _membro_publico(doc: dict) -> dict:
    """Resposta do membro sem campo sensível.

    A projeção antiga era `{"_id": 0}`, que devolvia `senha_hash`, o token do convite e o
    `sessao_jti` para o navegador do dono. `UsuarioPublico` já existe exatamente para isto.
    """
    base = UsuarioPublico(**{
        **doc,
        "created_at": doc.get("created_at"),
    }).model_dump()
    base.update({
        "convite_pendente": bool(doc.get("convite_pendente")),
        "convite_expirado": bool(doc.get("convite_pendente")) and _convite_expirado(doc),
    })
    return base


# --- Rotas ---

@router.post("/convidar")
async def convidar_membro(
    dados: ConviteEquipe,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
):
    """Cria um membro: com senha definida na hora, ou por convite no email."""
    _exigir_gestao(current_user)
    context_id = get_user_context(current_user)

    dono = current_user
    if not is_owner(current_user):
        dono_doc = await db.usuarios.find_one({"id": context_id})
        if not dono_doc:
            raise HTTPException(status_code=404, detail="Conta do proprietário não encontrada.")
        dono = Usuario(**{**dono_doc, "created_at": dono_doc["created_at"]})

    pode, msg = await permissao_service.verificar_recurso(dono, "multi_usuarios")
    if not pode:
        raise HTTPException(status_code=403, detail=msg)

    limite = await _limite_de_membros(dono)
    if limite == 0:
        raise HTTPException(status_code=403, detail="Seu plano não inclui membros de equipe.")
    if limite > 0:
        usados = await _contar_membros(context_id)
        if usados >= limite:
            raise HTTPException(
                status_code=403,
                detail=f"Seu plano permite {limite} membro(s). Desative um membro para incluir outro.",
            )

    permissoes = validar_permissoes(dados.permissoes)
    _conferir_delegacao(current_user, permissoes)

    if dados.senha:
        validar_forca_senha(dados.senha, dados.email, campo="senha do membro")

    existing = await db.usuarios.find_one({"email": dados.email}, {"_id": 0, "id": 1})
    if existing:
        raise HTTPException(status_code=400, detail="Este email já está cadastrado no sistema.")

    verification_token = None if dados.senha else str(uuid.uuid4())

    membro = Usuario(
        nome=dados.nome,
        email=dados.email,
        perfil="usuario",
        plano="equipe",  # Plano dummy: o membro herda os limites do dono
        plano_ativo=True,
        ativo=True,
        owner_id=context_id,
        cargo=dados.cargo,
        permissoes=permissoes,
        email_verificado=bool(dados.senha),
        convite_pendente=not dados.senha,
        email_verification_token=verification_token,
    )
    doc = membro.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["data_inicio_trial"] = doc["data_inicio_trial"].isoformat()
    if doc.get("data_fim_trial"):
        doc["data_fim_trial"] = doc["data_fim_trial"].isoformat()
    if dados.senha:
        # credencial fica fora do modelo, por design
        doc["senha_hash"] = hash_senha(dados.senha)
    else:
        doc["convite_expira_em"] = _expiracao_convite()
    doc["criado_por"] = current_user.id

    try:
        await db.usuarios.insert_one(doc)
    except DuplicateKeyError:
        # O índice único de email é a única defesa contra duas requisições simultâneas com o
        # mesmo endereço; sem este tratamento a corrida devolvia 500.
        raise HTTPException(status_code=400, detail="Este email já está cadastrado no sistema.")

    convite_enviado = None
    if not dados.senha:
        convite_enviado = await enviar_email_convite(dados.email, dono.nome, verification_token)
        if not convite_enviado:
            # enviar_email_convite devolve False em vez de levantar: sem esta checagem a tela
            # dizia "Convite enviado" para um email que nunca saiu.
            logger.error("Falha ao enviar convite de equipe", data={"membro_id": membro.id})

    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="criar",
        entidade="membro_equipe",
        entidade_id=membro.id,
        detalhes=(
            f"Adicionou membro {dados.nome} <{dados.email}> como {dados.cargo} "
            f"(permissões: {', '.join(permissoes) or 'nenhuma'}; "
            f"{'senha definida' if dados.senha else 'convite por email'})"
        ),
        dados_novos={"email": dados.email, "cargo": dados.cargo, "permissoes": permissoes},
        ip=extrair_ip(request),
    )

    if dados.senha:
        mensagem = "Membro adicionado com sucesso."
    elif convite_enviado:
        mensagem = f"Convite enviado para {dados.email}."
    else:
        mensagem = (
            f"Membro criado, mas o convite não pôde ser enviado para {dados.email}. "
            "Use “Reenviar convite” ou defina uma senha manualmente."
        )

    return {
        "message": mensagem,
        "id": membro.id,
        "convite_enviado": convite_enviado,
    }


@router.post("/{membro_id}/reenviar-convite")
async def reenviar_convite(
    membro_id: str,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
):
    """Gera um token novo e reenvia o email. Invalida o token anterior."""
    _exigir_gestao(current_user)
    context_id = get_user_context(current_user)
    membro = await _membro_do_dono(membro_id, context_id)

    if not membro.get("convite_pendente"):
        raise HTTPException(status_code=400, detail="Este membro já concluiu o cadastro.")

    token = str(uuid.uuid4())
    await db.usuarios.update_one(
        {"id": membro_id, "owner_id": context_id},
        {"$set": {
            "email_verification_token": token,
            "convite_expira_em": _expiracao_convite(),
        }},
    )

    dono_nome = current_user.nome
    if not is_owner(current_user):
        dono_doc = await db.usuarios.find_one({"id": context_id}, {"_id": 0, "nome": 1})
        dono_nome = (dono_doc or {}).get("nome") or dono_nome

    enviado = await enviar_email_convite(membro["email"], dono_nome, token)

    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="atualizar",
        entidade="membro_equipe",
        entidade_id=membro_id,
        detalhes=f"Reenviou convite para {membro['email']} (enviado: {enviado})",
        ip=extrair_ip(request),
    )

    if not enviado:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível enviar o email agora. Tente novamente em alguns minutos.",
        )
    return {"message": f"Convite reenviado para {membro['email']}."}


@router.post("/aceitar-convite")
async def aceitar_convite(dados: AceitarConvite, request: Request):
    """Finaliza o cadastro do membro convidado: define a senha e ativa a conta."""
    ip = extrair_ip(request)
    chave = f"convite:{ip}"
    bloqueado, segundos = await verificar_bloqueio(chave)
    if bloqueado:
        raise HTTPException(
            status_code=429,
            detail=f"Muitas tentativas. Tente novamente em {segundos // 60 + 1} minuto(s).",
        )

    user = await db.usuarios.find_one({
        "email_verification_token": dados.token,
        "convite_pendente": True,
    })

    if not user:
        await registrar_tentativa_falha(chave)
        raise HTTPException(status_code=400, detail="Convite inválido ou já utilizado.")

    if _convite_expirado(user):
        await registrar_tentativa_falha(chave)
        raise HTTPException(
            status_code=400,
            detail="Este convite expirou. Peça ao dono da conta para reenviar.",
        )

    validar_forca_senha(dados.senha, user.get("email"))

    await db.usuarios.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "senha_hash": hash_senha(dados.senha),
            "email_verificado": True,
            "convite_pendente": False,
            "email_verification_token": None,
            "convite_expira_em": None,
            "convite_aceito_em": datetime.now(timezone.utc).isoformat(),
            "ativo": True,
            "nome": dados.nome or user.get("nome"),
        }},
    )
    await registrar_sucesso(chave)

    await registrar_auditoria(
        usuario_id=user["id"],
        usuario_email=user.get("email", ""),
        acao="atualizar",
        entidade="membro_equipe",
        entidade_id=user["id"],
        detalhes="Aceitou o convite e definiu a senha de acesso",
        ip=ip,
    )

    return {"message": "Cadastro concluído com sucesso! Você já pode fazer login."}


@router.get("")
async def listar_equipe(current_user: Usuario = Depends(get_current_user)):
    """Lista os membros da conta, sem campo sensível, com o limite real do plano."""
    _exigir_gestao(current_user)
    context_id = get_user_context(current_user)

    membros = await db.usuarios.find({"owner_id": context_id}).to_list(500)

    dono = current_user
    if not is_owner(current_user):
        dono_doc = await db.usuarios.find_one({"id": context_id})
        if dono_doc:
            dono = Usuario(**dono_doc)

    limite = await _limite_de_membros(dono)
    usados = await _contar_membros(context_id)

    return {
        "membros": [_membro_publico(m) for m in membros],
        "limites": {
            "usado": usados,
            "total": limite,               # -1 = ilimitado, 0 = plano sem equipe
            "ilimitado": limite == -1,
        },
        "permissoes_disponiveis": [
            {"id": p, "label": ROTULOS[p], "delegavel": is_owner(current_user) or (
                p not in NAO_DELEGAVEIS and p in (current_user.permissoes or [])
            )}
            for p in sorted(PERMISSOES_VALIDAS, key=lambda x: ROTULOS[x])
        ],
    }


@router.delete("/{membro_id}")
async def remover_membro(
    membro_id: str,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
):
    """Desativa um membro (ou cancela o convite ainda pendente).

    `ativo: False` corta o acesso na requisição seguinte — `get_current_user` confere o campo
    em toda chamada — então não é preciso invalidar o token à mão. Ainda assim o `sessao_jti`
    é limpo, para o registro não sugerir uma sessão viva.
    """
    _exigir_gestao(current_user)
    context_id = get_user_context(current_user)

    if membro_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode remover o seu próprio acesso.")

    membro = await _membro_do_dono(membro_id, context_id)

    if membro.get("convite_pendente"):
        await db.usuarios.delete_one({"id": membro_id, "owner_id": context_id})
        acao, detalhes = "excluir", f"Cancelou o convite de {membro.get('email')}"
        mensagem = "Convite cancelado e usuário removido."
    else:
        await db.usuarios.update_one(
            {"id": membro_id, "owner_id": context_id},
            {"$set": {"ativo": False, "sessao_jti": None, "desativado_em":
                      datetime.now(timezone.utc).isoformat()}},
        )
        acao, detalhes = "atualizar", f"Desativou o membro {membro.get('email')}"
        mensagem = "Membro desativado com sucesso."

    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao=acao,
        entidade="membro_equipe",
        entidade_id=membro_id,
        detalhes=detalhes,
        dados_anteriores={"email": membro.get("email"), "ativo": membro.get("ativo")},
        ip=extrair_ip(request),
    )

    return {"message": mensagem}


@router.post("/{membro_id}/reativar")
async def reativar_membro(
    membro_id: str,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
):
    """Devolve o acesso a um membro desativado.

    Antes, desativar era irreversível pela interface: o membro ficava na tabela como
    "Inativo" para sempre, sem rota que o trouxesse de volta.
    """
    _exigir_gestao(current_user)
    context_id = get_user_context(current_user)
    membro = await _membro_do_dono(membro_id, context_id)

    if membro.get("ativo"):
        return {"message": "Este membro já está ativo."}

    dono = current_user
    if not is_owner(current_user):
        dono_doc = await db.usuarios.find_one({"id": context_id})
        if dono_doc:
            dono = Usuario(**dono_doc)

    limite = await _limite_de_membros(dono)
    if limite > 0 and await _contar_membros(context_id) >= limite:
        raise HTTPException(
            status_code=403,
            detail=f"Seu plano permite {limite} membro(s) ativo(s).",
        )

    await db.usuarios.update_one(
        {"id": membro_id, "owner_id": context_id},
        {"$set": {"ativo": True}, "$unset": {"desativado_em": ""}},
    )

    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="atualizar",
        entidade="membro_equipe",
        entidade_id=membro_id,
        detalhes=f"Reativou o membro {membro.get('email')}",
        ip=extrair_ip(request),
    )

    return {"message": "Membro reativado com sucesso."}


@router.put("/{membro_id}/permissoes")
async def atualizar_permissoes(
    membro_id: str,
    dados: PermissoesUpdate,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
):
    """Substitui as permissões de um membro."""
    _exigir_gestao(current_user)
    context_id = get_user_context(current_user)

    if membro_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Você não pode alterar as suas próprias permissões.",
        )

    membro = await _membro_do_dono(membro_id, context_id)

    permissoes = validar_permissoes(dados.permissoes)
    _conferir_delegacao(current_user, permissoes)

    await db.usuarios.update_one(
        {"id": membro_id, "owner_id": context_id},
        {"$set": {"permissoes": permissoes}},
    )

    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="atualizar",
        entidade="membro_equipe",
        entidade_id=membro_id,
        detalhes=(
            f"Alterou permissões de {membro.get('email')}: "
            f"{', '.join(membro.get('permissoes') or []) or 'nenhuma'} → "
            f"{', '.join(permissoes) or 'nenhuma'}"
        ),
        dados_anteriores={"permissoes": membro.get("permissoes") or []},
        dados_novos={"permissoes": permissoes},
        ip=extrair_ip(request),
    )

    return {"message": "Permissões atualizadas.", "permissoes": permissoes}
