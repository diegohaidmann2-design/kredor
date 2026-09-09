"""
Serviço para o Portal do Cliente (Self-Service)
"""
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Dict, Any
import secrets
import string
from fastapi import HTTPException, status

from models.portal import PortalAuth, PortalClienteInfo
from utils.validators import normalize_cpf_cnpj
from services.email_service import enviar_email


class PortalService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection_auth = db["portal_auth"]
        self.collection_clientes = db["clientes"]
        self.collection_emprestimos = db["emprestimos"]
        self.collection_parcelas = db["parcelas"]
    
    def gerar_codigo_acesso(self) -> str:
        """Gera código de 6 dígitos aleatório"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    async def criar_ou_atualizar_codigo(self, cliente_id: str, usuario_id: str) -> str:
        """Cria ou atualiza código de acesso do cliente"""
        codigo = self.gerar_codigo_acesso()
        
        # Verificar se já existe auth para este cliente
        existing = await self.collection_auth.find_one({"cliente_id": cliente_id})
        
        if existing:
            # Atualizar código existente
            await self.collection_auth.update_one(
                {"cliente_id": cliente_id},
                {
                    "$set": {
                        "codigo_acesso": codigo,
                        "codigo_criado_em": datetime.now(timezone.utc),
                        "tentativas_falhas": 0,
                        "bloqueado_ate": None,
                        "ativo": True,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        else:
            # Criar novo
            auth = PortalAuth(
                cliente_id=cliente_id,
                usuario_id=usuario_id,
                codigo_acesso=codigo
            )
            await self.collection_auth.insert_one(auth.model_dump())
        
        return codigo
    
    async def validar_login(self, cpf_cnpj: str, codigo_acesso: str) -> Optional[Dict[str, Any]]:
        """Valida login do cliente no portal"""
        # Normalizar CPF/CNPJ
        cpf_cnpj_normalized = normalize_cpf_cnpj(cpf_cnpj)
        
        # Buscar cliente
        cliente = await self.collection_clientes.find_one({"cpf_cnpj": cpf_cnpj_normalized})
        if not cliente:
            return None
        
        # Buscar auth
        auth = await self.collection_auth.find_one({"cliente_id": cliente["id"]})
        if not auth:
            return None
        
        # Verificar se está bloqueado
        if auth.get("bloqueado_ate"):
            bloqueado_ate = auth["bloqueado_ate"]
            # Ensure both datetimes have timezone info
            if bloqueado_ate.tzinfo is None:
                bloqueado_ate = bloqueado_ate.replace(tzinfo=timezone.utc)
                
            if datetime.now(timezone.utc) < bloqueado_ate:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso temporariamente bloqueado. Tente novamente mais tarde."
                )
            else:
                # Desbloquear
                await self.collection_auth.update_one(
                    {"cliente_id": cliente["id"]},
                    {"$set": {"bloqueado_ate": None, "tentativas_falhas": 0}}
                )
                auth["tentativas_falhas"] = 0
        
        # Verificar código
        if auth.get("codigo_acesso") != codigo_acesso:
            # Incrementar tentativas falhas
            tentativas = auth.get("tentativas_falhas", 0) + 1
            update_data = {"tentativas_falhas": tentativas}
            
            # Bloquear após 5 tentativas
            if tentativas >= 5:
                update_data["bloqueado_ate"] = datetime.now(timezone.utc) + timedelta(hours=1)
            
            await self.collection_auth.update_one(
                {"cliente_id": cliente["id"]},
                {"$set": update_data}
            )
            
            if tentativas >= 5:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Muitas tentativas falhas. Acesso bloqueado por 1 hora."
                )
            
            return None
        
        # Login bem-sucedido - resetar tentativas e atualizar último acesso
        await self.collection_auth.update_one(
            {"cliente_id": cliente["id"]},
            {
                "$set": {
                    "tentativas_falhas": 0,
                    "ultimo_acesso": datetime.now(timezone.utc),
                    "bloqueado_ate": None
                }
            }
        )
        
        return {
            "cliente": cliente,
            "usuario_id": auth["usuario_id"]
        }
    
    async def obter_info_cliente(self, cliente_id: str) -> PortalClienteInfo:
        """Obtém informações do cliente para o portal"""
        # Buscar cliente
        cliente = await self.collection_clientes.find_one({"id": cliente_id})
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
        
        # Buscar empréstimos
        emprestimos = await self.collection_emprestimos.find(
            {"cliente_id": cliente_id}
        ).to_list(None)
        
        total_emprestimos = len(emprestimos)
        emprestimos_ativos = sum(1 for e in emprestimos if e.get("status") == "ativo")
        
        # Calcular total devido (parcelas pendentes)
        total_devido = 0
        proxima_parcela = None
        
        if emprestimos_ativos > 0:
            # Buscar parcelas pendentes
            parcelas_pendentes = await self.collection_parcelas.find(
                {
                    "emprestimo_id": {"$in": [e["id"] for e in emprestimos]},
                    "status": "pendente"
                }
            ).sort("data_vencimento", 1).to_list(None)
            
            total_devido = sum(p.get("valor_total_centavos", 0) for p in parcelas_pendentes)
            
            if parcelas_pendentes:
                proxima = parcelas_pendentes[0]
                vencimento_raw = proxima.get("data_vencimento")
                
                # Converter data de forma segura
                if vencimento_raw is None:
                    vencimento_str = None
                    dias_ate = None
                elif isinstance(vencimento_raw, str):
                    vencimento_str = vencimento_raw
                    try:
                        vencimento_dt = datetime.fromisoformat(vencimento_raw.replace("Z", "+00:00"))
                        dias_ate = (vencimento_dt - datetime.now(timezone.utc)).days
                    except Exception:
                        dias_ate = None
                elif hasattr(vencimento_raw, 'isoformat'):
                    vencimento_str = vencimento_raw.isoformat()
                    dias_ate = (vencimento_raw - datetime.now(timezone.utc)).days
                else:
                    vencimento_str = str(vencimento_raw)
                    dias_ate = None
                
                proxima_parcela = {
                    "numero": proxima.get("numero_parcela"),
                    "valor_centavos": proxima.get("valor_total_centavos"),
                    "data_vencimento": vencimento_str,
                    "dias_ate_vencimento": dias_ate
                }
        
        return PortalClienteInfo(
            id=cliente["id"],
            nome=cliente["nome"],
            cpf_cnpj=cliente["cpf_cnpj"],
            telefone=cliente["telefone"],
            email=cliente.get("email"),
            status=cliente.get("status", "ativo"),
            total_emprestimos=total_emprestimos,
            emprestimos_ativos=emprestimos_ativos,
            total_devido_centavos=total_devido,
            proxima_parcela=proxima_parcela
        )
    
    async def solicitar_codigo(self, cpf_cnpj: str, email: str) -> bool:
        """Solicita código de acesso por email"""
        # Normalizar CPF/CNPJ
        cpf_cnpj_normalized = normalize_cpf_cnpj(cpf_cnpj)
        
        # Buscar cliente
        cliente = await self.collection_clientes.find_one({"cpf_cnpj": cpf_cnpj_normalized})
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
        
        # Verificar email
        if cliente.get("email") != email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email não corresponde ao cadastro"
            )
        
        # Buscar ou criar código
        auth = await self.collection_auth.find_one({"cliente_id": cliente["id"]})
        
        if not auth:
            # Buscar usuario_id do cliente
            usuario_id = cliente.get("usuario_id")
            if not usuario_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cliente sem usuário associado"
                )
            codigo = await self.criar_ou_atualizar_codigo(cliente["id"], usuario_id)
        else:
            # Verificar rate limit (não permitir mais de 1 solicitação por hora)
            if auth.get("codigo_criado_em"):
                codigo_criado_em = auth["codigo_criado_em"]
                # Ensure both datetimes have timezone info
                if codigo_criado_em.tzinfo is None:
                    codigo_criado_em = codigo_criado_em.replace(tzinfo=timezone.utc)
                
                tempo_decorrido = datetime.now(timezone.utc) - codigo_criado_em
                if tempo_decorrido < timedelta(hours=1):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Aguarde 1 hora antes de solicitar um novo código"
                    )
            
            codigo = await self.criar_ou_atualizar_codigo(cliente["id"], auth["usuario_id"])
        
        # Enviar email
        assunto = "Seu código de acesso - Kredor"
        corpo = f"""
        <h2>Código de Acesso - Portal do Cliente</h2>
        <p>Olá, <strong>{cliente['nome']}</strong>!</p>
        <p>Seu código de acesso ao Portal do Cliente Kredor é:</p>
        <h1 style="background-color: #f0f0f0; padding: 20px; text-align: center; letter-spacing: 10px; font-family: monospace;">{codigo}</h1>
        <p>Use este código para acessar o portal e consultar seus empréstimos.</p>
        <p><strong>Importante:</strong></p>
        <ul>
            <li>Este código é pessoal e intransferível</li>
            <li>Não compartilhe com terceiros</li>
            <li>Válido até que um novo código seja solicitado</li>
        </ul>
        <p>Se você não solicitou este código, ignore este email.</p>
        <hr>
        <p style="color: #666; font-size: 12px;">Kredor - Sistema de Gestão de Empréstimos</p>
        """
        
        await enviar_email(email, assunto, corpo)
        
        return True
    
    async def alterar_codigo(self, cliente_id: str, codigo_atual: str, codigo_novo: str) -> bool:
        """Altera o código de acesso do cliente"""
        # Buscar auth
        auth = await self.collection_auth.find_one({"cliente_id": cliente_id})
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Código de acesso não encontrado"
            )
        
        # Verificar código atual
        if auth.get("codigo_acesso") != codigo_atual:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código atual incorreto"
            )
        
        # Validar novo código (6 dígitos)
        if not codigo_novo.isdigit() or len(codigo_novo) != 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Novo código deve ter 6 dígitos"
            )
        
        # Atualizar
        await self.collection_auth.update_one(
            {"cliente_id": cliente_id},
            {
                "$set": {
                    "codigo_acesso": codigo_novo,
                    "codigo_criado_em": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return True
