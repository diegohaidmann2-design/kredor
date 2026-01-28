"""
Job de Notificações Automáticas - Sistema Gestor Cred
Executa verificações periódicas e cria notificações automaticamente
"""
from datetime import datetime, timezone
from config import db
from services.notificacao_service import (
    verificar_vencimentos_usuario,
    verificar_assinaturas_expirando,
    criar_resumo_diario_admin
)


async def job_verificar_vencimentos_todos():
    """
    Job para verificar vencimentos de TODOS os usuários
    Executa a cada hora durante horário comercial
    """
    print("=" * 60)
    print(f"🔔 [Notificações] Verificando vencimentos - {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        # Buscar todos os usuários ativos
        usuarios = await db.usuarios.find({
            "plano_ativo": True,
            "ativo": True
        }).to_list(10000)
        
        total_notificacoes = 0
        usuarios_processados = 0
        
        for usuario in usuarios:
            usuario_id = usuario.get("id")
            if not usuario_id:
                continue
            
            try:
                resultado = await verificar_vencimentos_usuario(usuario_id)
                total_notificacoes += resultado.get("notificacoes_criadas", 0)
                usuarios_processados += 1
            except Exception as e:
                print(f"   ⚠️ Erro ao processar {usuario.get('email')}: {e}")
        
        print(f"✅ [Notificações] {usuarios_processados} usuários processados")
        print(f"✅ [Notificações] {total_notificacoes} notificações criadas")
        print("=" * 60)
        
        # Log de execução
        await db.jobs_execucoes.insert_one({
            "job": "verificar_vencimentos",
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "usuarios_processados": usuarios_processados,
            "notificacoes_criadas": total_notificacoes,
            "status": "sucesso"
        })
        
        return {
            "success": True,
            "usuarios_processados": usuarios_processados,
            "notificacoes_criadas": total_notificacoes
        }
        
    except Exception as e:
        print(f"❌ [Notificações] Erro: {e}")
        import traceback
        traceback.print_exc()
        
        await db.jobs_execucoes.insert_one({
            "job": "verificar_vencimentos",
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "status": "erro",
            "erro": str(e)
        })
        
        return {"success": False, "error": str(e)}


async def job_verificar_assinaturas():
    """
    Job para verificar assinaturas expirando
    Executa diariamente às 09:00
    """
    print("=" * 60)
    print(f"⏰ [Notificações] Verificando assinaturas - {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        resultado = await verificar_assinaturas_expirando()
        
        print(f"✅ [Notificações] {resultado.get('notificacoes_criadas', 0)} notificações de assinatura criadas")
        print("=" * 60)
        
        await db.jobs_execucoes.insert_one({
            "job": "verificar_assinaturas",
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "notificacoes_criadas": resultado.get("notificacoes_criadas", 0),
            "status": "sucesso"
        })
        
        return resultado
        
    except Exception as e:
        print(f"❌ [Notificações] Erro: {e}")
        
        await db.jobs_execucoes.insert_one({
            "job": "verificar_assinaturas",
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "status": "erro",
            "erro": str(e)
        })
        
        return {"success": False, "error": str(e)}


async def job_resumo_diario_admin():
    """
    Job para criar resumo diário para administradores
    Executa diariamente às 08:00
    """
    print("=" * 60)
    print(f"📊 [Notificações] Gerando resumo diário - {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        resultado = await criar_resumo_diario_admin()
        
        print(f"✅ [Notificações] Resumo diário criado:")
        print(f"   - Novos usuários: {resultado.get('novos_usuarios', 0)}")
        print(f"   - Novos clientes: {resultado.get('novos_clientes', 0)}")
        print(f"   - Pagamentos: {resultado.get('pagamentos_hoje', 0)}")
        print(f"   - Parcelas em atraso: {resultado.get('parcelas_atraso', 0)}")
        print("=" * 60)
        
        await db.jobs_execucoes.insert_one({
            "job": "resumo_diario_admin",
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "dados": resultado,
            "status": "sucesso"
        })
        
        return resultado
        
    except Exception as e:
        print(f"❌ [Notificações] Erro: {e}")
        
        await db.jobs_execucoes.insert_one({
            "job": "resumo_diario_admin",
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "status": "erro",
            "erro": str(e)
        })
        
        return {"success": False, "error": str(e)}
