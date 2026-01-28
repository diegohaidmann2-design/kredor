from datetime import datetime
import uuid
from config import db
from services.notificacao_service import criar_notificacao

class SuporteService:
    
    @staticmethod
    async def gerar_numero_ticket():
        """Gera número único do ticket"""
        ano = datetime.now().year
        
        # Buscar último ticket do ano
        ultimo = await db.tickets_suporte.find_one(
            {"numero_ticket": {"$regex": f"^TK-{ano}-"}},
            sort=[("numero_ticket", -1)]
        )
        
        if ultimo:
            ultimo_num = int(ultimo["numero_ticket"].split("-")[-1])
            proximo = ultimo_num + 1
        else:
            proximo = 1
            
        return f"TK-{ano}-{proximo:04d}"
    
    @staticmethod
    async def criar_ticket(usuario_id: str, usuario_nome: str, 
                          usuario_email: str, dados: dict):
        """Cria um novo ticket"""
        
        numero_ticket = await SuporteService.gerar_numero_ticket()
        
        # Primeira mensagem
        mensagem = {
            "id": str(uuid.uuid4()),
            "remetente_id": usuario_id,
            "remetente_nome": usuario_nome,
            "remetente_tipo": "usuario",
            "conteudo": dados["mensagem"],
            "tipo": "texto",
            "arquivo_url": None,
            "enviado_em": datetime.now(),
            "lida": False
        }
        
        ticket = {
            "numero_ticket": numero_ticket,
            "usuario_id": usuario_id,
            "usuario_nome": usuario_nome,
            "usuario_email": usuario_email,
            "assunto": dados["assunto"],
            "categoria": dados["categoria"],
            "status": "aberto",
            "prioridade": dados.get("prioridade", "media"),
            "mensagens": [mensagem],
            "criado_em": datetime.now(),
            "atualizado_em": datetime.now(),
            "atribuido_a": None,
            "atribuido_nome": None,
            "total_mensagens": 1,
            "mensagens_nao_lidas_usuario": 0,
            "mensagens_nao_lidas_admin": 1,
            "tags": []
        }
        
        await db.tickets_suporte.insert_one(ticket)
        
        # NOTIFICAR ADMINS sobre novo ticket
        await SuporteService.notificar_admins_novo_ticket(ticket)
        
        return ticket
    
    @staticmethod
    async def adicionar_mensagem(numero_ticket: str, remetente_id: str,
                                 remetente_nome: str, remetente_tipo: str,
                                 conteudo: str, tipo: str = "texto", 
                                 arquivo_url: str = None):
        """Adiciona mensagem ao ticket e cria notificações"""
        
        ticket = await db.tickets_suporte.find_one({"numero_ticket": numero_ticket})
        if not ticket:
            raise ValueError("Ticket não encontrado")
        
        mensagem = {
            "id": str(uuid.uuid4()),
            "remetente_id": remetente_id,
            "remetente_nome": remetente_nome,
            "remetente_tipo": remetente_tipo,
            "conteudo": conteudo,
            "tipo": tipo,
            "arquivo_url": arquivo_url,
            "enviado_em": datetime.now(),
            "lida": False
        }
        
        # Atualizar contadores
        update = {
            "$push": {"mensagens": mensagem},
            "$set": {"atualizado_em": datetime.now()},
            "$inc": {"total_mensagens": 1}
        }
        
        if remetente_tipo == "admin":
            # Admin respondeu - incrementar contador do usuário
            update["$inc"]["mensagens_nao_lidas_usuario"] = 1
            # Status vira "em_atendimento" se estava "aberto"
            if ticket["status"] == "aberto":
                update["$set"]["status"] = "em_atendimento"
        else:
            # Usuário respondeu - incrementar contador do admin
            update["$inc"]["mensagens_nao_lidas_admin"] = 1
        
        await db.tickets_suporte.update_one(
            {"numero_ticket": numero_ticket},
            update
        )
        
        # CRIAR NOTIFICAÇÃO
        if remetente_tipo == "admin":
            # Notificar o usuário que o admin respondeu
            await criar_notificacao(
                usuario_id=ticket["usuario_id"],
                tipo="suporte_resposta",
                titulo=f"Nova resposta no ticket {numero_ticket}",
                mensagem=f"{remetente_nome} respondeu: {conteudo[:50]}...",
                link=f"/suporte/{numero_ticket}"
            )
        else:
            # Notificar admins que usuário respondeu
            if ticket.get("atribuido_a"):
                # Notificar apenas o admin atribuído
                await criar_notificacao(
                    usuario_id=ticket["atribuido_a"],
                    tipo="suporte_resposta",
                    titulo=f"Nova mensagem no ticket {numero_ticket}",
                    mensagem=f"{remetente_nome}: {conteudo[:50]}...",
                    link=f"/admin/suporte/{numero_ticket}"
                )
            else:
                # Notificar todos os admins
                await SuporteService.notificar_admins_mensagem(ticket, mensagem)
        
        return mensagem
    
    @staticmethod
    async def marcar_mensagens_lidas(numero_ticket: str, tipo_usuario: str):
        """Marca mensagens como lidas"""
        
        if tipo_usuario == "usuario":
            # Usuário lendo - marcar mensagens do admin como lidas
            await db.tickets_suporte.update_one(
                {"numero_ticket": numero_ticket},
                {
                    "$set": {
                        "mensagens.$[elem].lida": True,
                        "mensagens_nao_lidas_usuario": 0
                    }
                },
                array_filters=[{"elem.remetente_tipo": "admin", "elem.lida": False}]
            )
        else:
            # Admin lendo - marcar mensagens do usuário como lidas
            await db.tickets_suporte.update_one(
                {"numero_ticket": numero_ticket},
                {
                    "$set": {
                        "mensagens.$[elem].lida": True,
                        "mensagens_nao_lidas_admin": 0
                    }
                },
                array_filters=[{"elem.remetente_tipo": "usuario", "elem.lida": False}]
            )
    
    @staticmethod
    async def notificar_admins_novo_ticket(ticket: dict):
        """Notifica todos os admins sobre novo ticket"""
        
        # Buscar todos os admins
        admins = await db.usuarios.find({"perfil": "admin"}).to_list(100)
        
        for admin in admins:
            # Usar campo 'id' (UUID) ao invés de '_id' (ObjectId do MongoDB)
            admin_id = admin.get("id") or str(admin.get("_id"))
            await criar_notificacao(
                usuario_id=admin_id,
                tipo="suporte_novo",
                titulo=f"Novo ticket de suporte: {ticket['numero_ticket']}",
                mensagem=f"{ticket['usuario_nome']}: {ticket['assunto']}",
                link=f"/admin/suporte/{ticket['numero_ticket']}"
            )
    
    @staticmethod
    async def notificar_admins_mensagem(ticket: dict, mensagem: dict):
        """Notifica admins sobre nova mensagem"""
        
        admins = await db.usuarios.find({"perfil": "admin"}).to_list(100)
        
        for admin in admins:
            # Usar campo 'id' (UUID) ao invés de '_id' (ObjectId do MongoDB)
            admin_id = admin.get("id") or str(admin.get("_id"))
            await criar_notificacao(
                usuario_id=admin_id,
                tipo="suporte_mensagem",
                titulo=f"Mensagem no ticket {ticket['numero_ticket']}",
                mensagem=f"{mensagem['remetente_nome']}: {mensagem['conteudo'][:50]}...",
                link=f"/admin/suporte/{ticket['numero_ticket']}"
            )
            
    @staticmethod
    async def deletar_ticket(numero_ticket: str):
        """Remove permanentemente um ticket (Admin only)"""
        result = await db.tickets_suporte.delete_one({"numero_ticket": numero_ticket})
        return result.deleted_count > 0
