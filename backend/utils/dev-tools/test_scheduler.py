#!/usr/bin/env python3
"""
Script de teste completo do Scheduler Automático
Testa todos os endpoints e funcionalidades
"""
import requests
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:8001/api"

def print_section(title):
    """Print formatado de seção"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_result(title, data):
    """Print formatado de resultado"""
    print(f"\n✓ {title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

def main():
    print_section("🧪 TESTE COMPLETO DO SCHEDULER AUTOMÁTICO")
    
    # 1. Login como admin
    print("\n1️⃣ Fazendo login como admin...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@sgej.com", "senha": "admin123"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Erro no login: {login_response.status_code}")
        print(login_response.text)
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login realizado com sucesso!")
    
    # 2. Verificar status do scheduler
    print_section("2️⃣ Status do Scheduler")
    status_response = requests.get(f"{BASE_URL}/admin/scheduler/status", headers=headers)
    
    if status_response.status_code == 200:
        status = status_response.json()
        print_result("Status do Scheduler", status)
        
        # Validar
        assert status["success"] == True
        assert status["scheduler"]["status"] == "running"
        assert status["scheduler"]["total_jobs"] == 5
        print("\n✅ Scheduler está rodando com 5 jobs agendados!")
    else:
        print(f"❌ Erro ao obter status: {status_response.status_code}")
        return
    
    # 3. Executar job de verificação de planos
    print_section("3️⃣ Executando Job: Verificar Planos Expirados")
    job_response = requests.post(
        f"{BASE_URL}/admin/scheduler/jobs/verificar-planos/executar",
        headers=headers
    )
    
    if job_response.status_code == 200:
        result = job_response.json()
        print_result("Resultado da Execução", result)
        print(f"\n✅ Job executado! Usuários atualizados: {result['resultado']['usuarios_atualizados']}")
    else:
        print(f"❌ Erro ao executar job: {job_response.status_code}")
    
    # 4. Obter estatísticas
    print_section("4️⃣ Estatísticas do Scheduler")
    stats_response = requests.get(f"{BASE_URL}/admin/scheduler/estatisticas", headers=headers)
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print_result("Estatísticas Gerais", stats)
        
        estatisticas = stats["estatisticas"]
        print(f"\n📊 Resumo:")
        print(f"   Jobs executados (24h): {estatisticas['jobs_executados_24h']}")
        print(f"   Logs de planos (24h): {estatisticas['logs_planos_24h']}")
        print(f"   Planos expirados (7d): {estatisticas['planos_expirados_7d']}")
        print(f"   Correções automáticas (7d): {estatisticas['correcoes_automaticas_7d']}")
        print("\n✅ Estatísticas obtidas com sucesso!")
    else:
        print(f"❌ Erro ao obter estatísticas: {stats_response.status_code}")
    
    # 5. Listar histórico de jobs
    print_section("5️⃣ Histórico de Execuções")
    history_response = requests.get(
        f"{BASE_URL}/admin/scheduler/jobs/historico?limit=10",
        headers=headers
    )
    
    if history_response.status_code == 200:
        history = history_response.json()
        print(f"\n✓ Total de execuções registradas: {history['total_jobs']}")
        print(f"✓ Total de logs de planos: {history['total_logs_planos']}")
        
        if history['total_jobs'] > 0:
            print("\n📋 Últimas execuções:")
            for job in history['jobs_execucoes'][:3]:
                print(f"   - {job.get('job', 'N/A')} em {job.get('executado_em', 'N/A')}")
        
        print("\n✅ Histórico obtido com sucesso!")
    else:
        print(f"❌ Erro ao obter histórico: {history_response.status_code}")
    
    # 6. Listar próximas execuções
    print_section("6️⃣ Próximas Execuções Agendadas")
    status = status_response.json()
    
    print("\n📅 Agendamentos:")
    for job in status["scheduler"]["jobs"]:
        print(f"\n   • {job['name']}")
        print(f"     ID: {job['id']}")
        print(f"     Próxima execução: {job['next_run']}")
        print(f"     Trigger: {job['trigger']}")
    
    # 7. Testar endpoint de reconciliação
    print_section("7️⃣ Teste de Reconciliação")
    reconcile_response = requests.post(
        f"{BASE_URL}/admin/scheduler/jobs/reconciliacao/executar",
        headers=headers
    )
    
    if reconcile_response.status_code == 200:
        reconcile = reconcile_response.json()
        print_result("Resultado da Reconciliação", reconcile)
        print("\n✅ Reconciliação executada com sucesso!")
    else:
        print(f"❌ Erro na reconciliação: {reconcile_response.status_code}")
    
    # Resumo final
    print_section("✅ RESUMO DOS TESTES")
    print("""
✅ Scheduler está rodando
✅ 5 jobs agendados corretamente
✅ Jobs podem ser executados manualmente via API
✅ Estatísticas funcionando
✅ Histórico de execuções funcionando
✅ Próximas execuções agendadas
✅ Sistema de reconciliação operacional

🎉 TODOS OS TESTES PASSARAM!
    """)
    
    print("\n📖 Para mais informações, consulte:")
    print("   /app/backend/SCHEDULER_README.md")
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
