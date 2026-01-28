"""
Script para gerar códigos de acesso para clientes existentes
"""
import asyncio
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
sys.path.insert(0, str(Path(__file__).parent))

from config import db
from services.portal_service import PortalService


async def gerar_codigos_clientes():
    """Gera códigos de acesso para todos os clientes que ainda não têm"""
    print("=" * 60)
    print("🔑 Gerando códigos de acesso para clientes")
    print("=" * 60)
    print()
    
    service = PortalService(db)
    
    # Buscar todos os clientes
    clientes = await db.clientes.find({}).to_list(None)
    
    if not clientes:
        print("❌ Nenhum cliente encontrado no banco de dados")
        return
    
    print(f"📊 Total de clientes: {len(clientes)}")
    print()
    
    total_criados = 0
    total_ja_existentes = 0
    
    for cliente in clientes:
        cliente_id = cliente.get("id")
        usuario_id = cliente.get("usuario_id")
        nome = cliente.get("nome", "Sem nome")
        email = cliente.get("email")
        
        if not cliente_id or not usuario_id:
            print(f"⚠️  Cliente {nome} sem ID ou usuario_id - IGNORADO")
            continue
        
        # Verificar se já tem código
        existing = await db.portal_auth.find_one({"cliente_id": cliente_id})
        
        if existing:
            codigo = existing.get("codigo_acesso", "******")
            print(f"✅ {nome[:30]:<30} | Código já existe: {codigo}")
            total_ja_existentes += 1
        else:
            # Criar código
            codigo = await service.criar_ou_atualizar_codigo(cliente_id, usuario_id)
            print(f"🆕 {nome[:30]:<30} | Novo código: {codigo}")
            total_criados += 1
            
            # Se tiver email, enviar
            if email:
                try:
                    await service.solicitar_codigo(
                        cliente.get("cpf_cnpj"), 
                        email
                    )
                    print(f"   📧 Email enviado para: {email}")
                except Exception as e:
                    print(f"   ⚠️  Erro ao enviar email: {str(e)}")
    
    print()
    print("=" * 60)
    print("✅ Processo concluído!")
    print(f"   📊 Total de códigos criados: {total_criados}")
    print(f"   ✅ Total já existentes: {total_ja_existentes}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(gerar_codigos_clientes())
