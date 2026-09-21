"""
Backend test for quinzenal (fortnightly) periodicity feature
Tests the public simulation endpoint POST /api/emprestimos/simular-publico
"""
import requests
from datetime import datetime, timedelta
import json

# Base URL from frontend/.env
BASE_URL = "https://gestorcred-staging-2.preview.emergentagent.com/api"

def test_quinzenal_tabela_price():
    """
    C1: Test tabela_price with quinzenal periodicity
    - 4 parcelas
    - Dates spaced 15 days apart
    """
    print("\n=== C1: Testing tabela_price with quinzenal ===")
    
    payload = {
        "valor_principal_centavos": 100000,
        "metodo_calculo": "tabela_price",
        "periodicidade": "quinzenal",
        "taxa_juros_quinzenal": 5,
        "prazo_quinzenas": 4
    }
    
    response = requests.post(f"{BASE_URL}/emprestimos/simular-publico", json=payload)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    print(f"Response periodicidade: {data.get('periodicidade')}")
    print(f"Number of parcelas: {len(data.get('parcelas', []))}")
    
    # Verify periodicidade
    if data.get('periodicidade') != 'quinzenal':
        print(f"❌ FAILED: Expected periodicidade='quinzenal', got '{data.get('periodicidade')}'")
        return False
    
    # Verify number of parcelas
    parcelas = data.get('parcelas', [])
    if len(parcelas) != 4:
        print(f"❌ FAILED: Expected 4 parcelas, got {len(parcelas)}")
        return False
    
    # Verify date spacing (15 days apart)
    print("\nVerifying date spacing:")
    for i in range(len(parcelas) - 1):
        date1 = datetime.fromisoformat(parcelas[i]['data_vencimento'].replace('Z', '+00:00'))
        date2 = datetime.fromisoformat(parcelas[i+1]['data_vencimento'].replace('Z', '+00:00'))
        diff_days = (date2 - date1).days
        
        print(f"  Parcela {i+1} -> {i+2}: {diff_days} days")
        
        if diff_days != 15:
            print(f"❌ FAILED: Expected 15 days between parcelas {i+1} and {i+2}, got {diff_days} days")
            return False
    
    print("✅ PASSED: C1 - tabela_price with quinzenal")
    return True


def test_quinzenal_juros_simples():
    """
    C2: Test juros_simples with quinzenal periodicity
    - 3 parcelas
    - valor_total_juros_centavos should be 30000 (10% * 3 * R$1000)
    - Dates spaced 15 days apart
    """
    print("\n=== C2: Testing juros_simples with quinzenal ===")
    
    payload = {
        "valor_principal_centavos": 100000,
        "metodo_calculo": "juros_simples",
        "periodicidade": "quinzenal",
        "taxa_juros_quinzenal": 10,
        "prazo_quinzenas": 3
    }
    
    response = requests.post(f"{BASE_URL}/emprestimos/simular-publico", json=payload)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    print(f"Number of parcelas: {len(data.get('parcelas', []))}")
    print(f"valor_total_juros (reais): {data.get('valor_total_juros')}")
    
    # Verify number of parcelas
    parcelas = data.get('parcelas', [])
    if len(parcelas) != 3:
        print(f"❌ FAILED: Expected 3 parcelas, got {len(parcelas)}")
        return False
    
    # Verify total interest (10% * 3 * R$1000 = R$300)
    # Note: API returns values in reais, not centavos
    expected_juros = 300.0
    actual_juros = data.get('valor_total_juros')
    if actual_juros != expected_juros:
        print(f"❌ FAILED: Expected valor_total_juros={expected_juros}, got {actual_juros}")
        return False
    
    # Verify date spacing (15 days apart)
    print("\nVerifying date spacing:")
    for i in range(len(parcelas) - 1):
        date1 = datetime.fromisoformat(parcelas[i]['data_vencimento'].replace('Z', '+00:00'))
        date2 = datetime.fromisoformat(parcelas[i+1]['data_vencimento'].replace('Z', '+00:00'))
        diff_days = (date2 - date1).days
        
        print(f"  Parcela {i+1} -> {i+2}: {diff_days} days")
        
        if diff_days != 15:
            print(f"❌ FAILED: Expected 15 days between parcelas {i+1} and {i+2}, got {diff_days} days")
            return False
    
    print("✅ PASSED: C2 - juros_simples with quinzenal")
    return True


def test_quinzenal_validation():
    """
    C3: Test validation - missing taxa_juros_quinzenal and prazo_quinzenas
    Should return 422
    """
    print("\n=== C3: Testing validation (missing required fields) ===")
    
    payload = {
        "valor_principal_centavos": 100000,
        "metodo_calculo": "tabela_price",
        "periodicidade": "quinzenal"
        # Missing: taxa_juros_quinzenal and prazo_quinzenas
    }
    
    response = requests.post(f"{BASE_URL}/emprestimos/simular-publico", json=payload)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 422:
        print(f"❌ FAILED: Expected 422, got {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    detail = data.get('detail', '')
    print(f"Error detail: {detail}")
    
    # Verify error message mentions required fields
    if 'taxa_juros_quinzenal' not in detail.lower() or 'prazo_quinzenas' not in detail.lower():
        print(f"❌ FAILED: Error message should mention taxa_juros_quinzenal and prazo_quinzenas")
        return False
    
    print("✅ PASSED: C3 - validation for missing fields")
    return True


def test_regression_mensal():
    """
    C4a: Regression test - mensal periodicity should still work
    """
    print("\n=== C4a: Regression test - mensal ===")
    
    payload = {
        "valor_principal_centavos": 100000,
        "metodo_calculo": "tabela_price",
        "periodicidade": "mensal",
        "taxa_juros_mensal": 5,
        "prazo_meses": 6
    }
    
    response = requests.post(f"{BASE_URL}/emprestimos/simular-publico", json=payload)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    parcelas = data.get('parcelas', [])
    print(f"Number of parcelas: {len(parcelas)}")
    
    if len(parcelas) != 6:
        print(f"❌ FAILED: Expected 6 parcelas, got {len(parcelas)}")
        return False
    
    print("✅ PASSED: C4a - mensal regression test")
    return True


def test_regression_semanal():
    """
    C4b: Regression test - semanal periodicity should still work
    Dates should be spaced 7 days apart
    """
    print("\n=== C4b: Regression test - semanal ===")
    
    payload = {
        "valor_principal_centavos": 100000,
        "metodo_calculo": "juros_simples",
        "periodicidade": "semanal",
        "taxa_juros_semanal": 2,
        "prazo_semanas": 4
    }
    
    response = requests.post(f"{BASE_URL}/emprestimos/simular-publico", json=payload)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    parcelas = data.get('parcelas', [])
    print(f"Number of parcelas: {len(parcelas)}")
    
    if len(parcelas) != 4:
        print(f"❌ FAILED: Expected 4 parcelas, got {len(parcelas)}")
        return False
    
    # Verify date spacing (7 days apart for semanal)
    print("\nVerifying date spacing (should be 7 days):")
    for i in range(len(parcelas) - 1):
        date1 = datetime.fromisoformat(parcelas[i]['data_vencimento'].replace('Z', '+00:00'))
        date2 = datetime.fromisoformat(parcelas[i+1]['data_vencimento'].replace('Z', '+00:00'))
        diff_days = (date2 - date1).days
        
        print(f"  Parcela {i+1} -> {i+2}: {diff_days} days")
        
        if diff_days != 7:
            print(f"❌ FAILED: Expected 7 days between parcelas {i+1} and {i+2}, got {diff_days} days")
            return False
    
    print("✅ PASSED: C4b - semanal regression test")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("TESTING QUINZENAL PERIODICITY FEATURE")
    print("Endpoint: POST /api/emprestimos/simular-publico")
    print("=" * 60)
    
    results = {
        "C1 - tabela_price quinzenal": test_quinzenal_tabela_price(),
        "C2 - juros_simples quinzenal": test_quinzenal_juros_simples(),
        "C3 - validation": test_quinzenal_validation(),
        "C4a - regression mensal": test_regression_mensal(),
        "C4b - regression semanal": test_regression_semanal()
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
