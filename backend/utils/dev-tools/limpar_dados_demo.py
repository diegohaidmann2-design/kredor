#!/usr/bin/env python3
"""
Script para Limpar Dados Demo do Kredor
Remove todos os dados de demonstração, mantendo apenas o admin
"""
import asyncio
from datetime import datetime
from config import db


async def limpar_dados_demo():
    """Remove todos os dados demo do banco"""
    print("=" * 70)
    print("🗑️  LIMPEZA DE DADOS DEMO - Kredor")
    print("=" * 70)
    print("\n⚠️  ATENÇÃO: Esta operação irá REMOVER todos os dados de demonstração!")
    print("Apenas o usuário admin@sgej.com será mantido.\n")
    
    # Confirmar duas vezes
    confirmacao1 = input("Tem certeza que deseja continuar? (s/n): ").lower().strip()
    if confirmacao1 != 's':
        print("\n❌ Operação cancelada.")
        return
    
    confirmacao2 = input("\n⚠️  Confirme novamente digitando 'LIMPAR': ").strip()
    if confirmacao2 != 'LIMPAR':
        print("\n❌ Operação cancelada.")
        return
    
    print("\n🔄 Iniciando limpeza...\n")
    inicio = datetime.now()
    
    # Admin que será mantido
    admin = await db.usuarios.find_one({"email": "admin@sgej.com"})
    if not admin:
        print("❌ Usuário admin não encontrado!")
        return
    
    admin_id = admin["id"]
    
    # Contar antes
    print("📊 Contagem antes da limpeza:")
    count_usuarios = await db.usuarios.count_documents({"id": {"$ne": admin_id}})
    count_clientes = await db.clientes.count_documents({})
    count_emprestimos = await db.emprestimos.count_documents({})
    count_parcelas = await db.parcelas.count_documents({})
    count_pagamentos = await db.pagamentos.count_documents({})
    count_notificacoes = await db.notificacoes.count_documents({})
    count_transacoes = await db.transacoes.count_documents({})
    
    print(f"   • Usuários (exceto admin): {count_usuarios}")
    print(f"   • Clientes:                {count_clientes}")
    print(f"   • Empréstimos:             {count_emprestimos}")
    print(f"   • Parcelas:                {count_parcelas}")
    print(f"   • Pagamentos:              {count_pagamentos}")
    print(f"   • Notificações:            {count_notificacoes}")
    print(f"   • Transações:              {count_transacoes}")
    
    print("\n🗑️  Removendo dados...\n")
    
    # Deletar dados (mantendo apenas admin)
    result_usuarios = await db.usuarios.delete_many({"id": {"$ne": admin_id}})
    print(f"   ✅ Usuários removidos: {result_usuarios.deleted_count}")
    
    result_clientes = await db.clientes.delete_many({})
    print(f"   ✅ Clientes removidos: {result_clientes.deleted_count}")
    
    result_emprestimos = await db.emprestimos.delete_many({})
    print(f"   ✅ Empréstimos removidos: {result_emprestimos.deleted_count}")
    
    result_parcelas = await db.parcelas.delete_many({})
    print(f"   ✅ Parcelas removidas: {result_parcelas.deleted_count}")
    
    result_pagamentos = await db.pagamentos.delete_many({})
    print(f"   ✅ Pagamentos removidos: {result_pagamentos.deleted_count}")
    
    result_notificacoes = await db.notificacoes.delete_many({})
    print(f"   ✅ Notificações removidas: {result_notificacoes.deleted_count}")
    
    result_transacoes = await db.transacoes.delete_many({})
    print(f"   ✅ Transações removidas: {result_transacoes.deleted_count}")
    
    # Limpar collections de logs (opcional)
    result_logs_planos = await db.logs_planos.delete_many({})
    print(f"   ✅ Logs de planos removidos: {result_logs_planos.deleted_count}")
    
    result_jobs = await db.jobs_execucoes.delete_many({})
    print(f"   ✅ Logs de jobs removidos: {result_jobs.deleted_count}")
    
    result_auditoria = await db.auditoria.delete_many({})
    print(f"   ✅ Logs de auditoria removidos: {result_auditoria.deleted_count}")
    
    # Tempo de execução
    fim = datetime.now()
    duracao = (fim - inicio).total_seconds()
    
    # Verificar após limpeza
    print("\n📊 Verificação após limpeza:")
    count_usuarios_final = await db.usuarios.count_documents({})
    count_clientes_final = await db.clientes.count_documents({})
    count_emprestimos_final = await db.emprestimos.count_documents({})
    
    print(f"   • Usuários restantes:  {count_usuarios_final} (deve ser 1 - admin)")
    print(f"   • Clientes restantes:  {count_clientes_final} (deve ser 0)")
    print(f"   • Empréstimos restantes: {count_emprestimos_final} (deve ser 0)")
    
    print("\n" + "=" * 70)
    print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
    print("=" * 70)
    print(f"\n⏱️  Tempo de execução: {duracao:.2f} segundos")
    print(f"\n✅ O usuário admin@sgej.com foi preservado.")
    print("✅ Todas as configurações do sistema foram mantidas.")
    print("\n💡 O sistema está pronto para novos dados ou para executar")
    print("   o script criar_dados_demo.py novamente.")
    print("\n" + "=" * 70)


async def main():
    try:
        await limpar_dados_demo()
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n\n❌ Erro durante a limpeza: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
