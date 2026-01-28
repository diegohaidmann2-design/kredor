
import asyncio
import httpx
from datetime import datetime

# Configuração
API_URL = "http://localhost:8001/api"
ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_PASSWORD = "muda2025"  # Senha padrão do seed
USUARIO_ID_TESTE = "user-id-placeholder" # Será obtido dinamicamente

async def get_admin_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            print(f"Erro no login: {response.text}")
            return None
        return response.json()["token"]

async def create_ticket(token):
    headers = {"Authorization": f"Bearer {token}"}
    # Primeiro pegar um ID de usuário válido
    async with httpx.AsyncClient() as client:
        users_res = await client.get(f"{API_URL}/superadmin/usuarios", headers=headers)
        if users_res.status_code != 200:
             print("Erro ao listar usuários")
             return None
        
        users = users_res.json()
        if not users or not users.get("usuarios"):
            print("Nenhum usuário encontrado")
            return None
        
        user_id = users["usuarios"][0]["id"]
        
        ticket_data = {
            "usuario_id": user_id,
            "assunto": f"Ticket para Deletar {datetime.now().timestamp()}",
            "categoria": "outro",
            "mensagem": "Esta é uma mensagem de teste para deleção.",
            "prioridade": "baixa"
        }
        
        response = await client.post(f"{API_URL}/suporte/admin/tickets", json=ticket_data, headers=headers)
        if response.status_code == 200:
            print(f"Ticket criado: {response.json()['ticket']}")
            return response.json()['ticket']
        else:
            print(f"Erro ao criar ticket: {response.text}")
            return None

async def delete_ticket(token, ticket_number):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_URL}/suporte/admin/tickets/{ticket_number}", headers=headers)
        if response.status_code == 200:
            print(f"Ticket {ticket_number} deletado com sucesso!")
            return True
        else:
            print(f"Erro ao deletar ticket: {response.text}")
            return False

async def verify_ticket_gone(token, ticket_number):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/suporte/admin/tickets/{ticket_number}", headers=headers)
        if response.status_code == 404:
            print(f"Verificação OK: Ticket {ticket_number} realmente não existe mais.")
            return True
        else:
            print(f"Verificação FALHOU: Ticket {ticket_number} ainda existe ou erro desconhecido ({response.status_code}).")
            return False

async def clear_audit_logs(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_URL}/auditoria/limpar", headers=headers)
        if response.status_code == 200:
            print("Logs de auditoria limpos com sucesso!")
            return True
        else:
            print(f"Erro ao limpar logs: {response.text}")
            return False

async def verify_audit_empty(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/auditoria", headers=headers)
        if response.status_code == 200:
            logs = response.json()
            if len(logs) == 0:
                 print("Verificação OK: Lista de auditoria está vazia.")
                 return True
            else:
                 print(f"Verificação FALHOU: Ainda existem {len(logs)} logs.")
                 return False
        else:
            print(f"Erro ao listar auditoria: {response.text}")
            return False

async def main():
    print("--- Iniciando Verificação de Deleção ---")
    token = await get_admin_token()
    if not token:
        return

    # 1. Testar Deleção de Ticket
    print("\n1. Testando Deleção de Ticket...")
    ticket_num = await create_ticket(token)
    if ticket_num:
        deleted = await delete_ticket(token, ticket_num)
        if deleted:
            await verify_ticket_gone(token, ticket_num)
    
    # 2. Testar Limpeza de Auditoria
    print("\n2. Testando Limpeza de Auditoria...")
    cleared = await clear_audit_logs(token)
    if cleared:
        await verify_audit_empty(token)

if __name__ == "__main__":
    asyncio.run(main())
