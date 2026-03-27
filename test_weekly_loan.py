#!/usr/bin/env python3
"""
Quick test for weekly loan functionality after bug fix
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://projeto-em-progresso.preview.emergentagent.com"

def test_weekly_loan():
    # Login first
    login_data = {
        "email": "admin@gestorcerd.com",
        "senha": "admin123"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # Get client ID
    response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to get clients: {response.status_code}")
        return False
    
    clients = response.json().get('items', response.json())
    cliente_id = clients[0]['id']
    print(f"✅ Using client: {clients[0].get('nome', 'N/A')} - {cliente_id}")
    
    # Test weekly loan simulation
    print("\n🔍 Testing Weekly Loan Simulation...")
    weekly_sim_data = {
        "valor_principal": 5000.0,
        "taxa_juros_semanal": 1.0,
        "prazo_semanas": 24,
        "metodo_calculo": "tabela_price",
        "periodo_carencia_meses": 0,
        "periodicidade": "semanal"
    }
    
    response = requests.post(f"{BASE_URL}/api/emprestimos/simular", json=weekly_sim_data, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Weekly simulation works!")
        sim_result = response.json()
        print(f"   📊 Total with interest: R$ {sim_result.get('valor_total_com_juros', 0):,.2f}")
        print(f"   📅 Installments: {len(sim_result.get('parcelas', []))}")
    else:
        print(f"   ❌ Weekly simulation failed: {response.text}")
        return False
    
    # Test weekly loan creation
    print("\n🔍 Testing Weekly Loan Creation...")
    weekly_loan_data = {
        "cliente_id": cliente_id,
        "valor_principal": 5000.0,
        "taxa_juros_semanal": 1.0,
        "prazo_semanas": 24,
        "metodo_calculo": "tabela_price",
        "periodo_carencia_meses": 0,
        "taxa_multa_atraso": 2.0,
        "taxa_juros_mora_diario": 0.033,
        "periodicidade": "semanal",
        "data_inicio": datetime.now().isoformat(),
        "dia_vencimento": None
    }
    
    response = requests.post(f"{BASE_URL}/api/emprestimos", json=weekly_loan_data, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Weekly loan creation works!")
        loan_result = response.json()
        loan_id = loan_result.get('id')
        print(f"   💰 Loan ID: {loan_id}")
        print(f"   📊 Total with interest: R$ {loan_result.get('valor_total_com_juros', 0):,.2f}")
        
        # Test getting installments
        print("\n🔍 Testing Weekly Loan Installments...")
        response = requests.get(f"{BASE_URL}/api/emprestimos/{loan_id}/parcelas", headers=headers)
        if response.status_code == 200:
            parcelas = response.json()
            print(f"   ✅ Found {len(parcelas)} installments")
            if parcelas:
                print(f"   📅 First installment due: {parcelas[0].get('data_vencimento', 'N/A')}")
                print(f"   📅 Last installment due: {parcelas[-1].get('data_vencimento', 'N/A')}")
        else:
            print(f"   ❌ Failed to get installments: {response.status_code}")
        
        return True
    else:
        print(f"   ❌ Weekly loan creation failed: {response.text}")
        return False

if __name__ == "__main__":
    success = test_weekly_loan()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Weekly loan functionality test")