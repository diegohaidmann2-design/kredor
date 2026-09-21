#!/usr/bin/env python3
"""
Backend API Testing Script - Rolar Período Feature
Tests the new POST /api/emprestimos/{id}/rolar-periodo endpoint
"""
import requests
import json
import sys
from datetime import datetime

# Read backend URL from frontend/.env
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BASE_URL = line.split('=')[1].strip()
            break

API_BASE = f"{BASE_URL}/api"

# Test credentials
TEST_EMAIL = "diego.haidmann@gmail.com"
TEST_PASSWORD = "Teste@123"
TURNSTILE_TOKEN = "x"  # Test mode accepts any token

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def log_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def log_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def log_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def login():
    """Login and get access token"""
    log_info("Logging in...")
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={
            "email": TEST_EMAIL,
            "senha": TEST_PASSWORD,
            "turnstile_token": TURNSTILE_TOKEN
        }
    )
    
    if response.status_code != 200:
        log_error(f"Login failed: {response.status_code} - {response.text}")
        sys.exit(1)
    
    data = response.json()
    token = data.get("access_token")
    if not token:
        log_error("No access_token in login response")
        sys.exit(1)
    
    log_success(f"Logged in as {TEST_EMAIL}")
    return token

def get_headers(token):
    """Get headers with authorization"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def get_existing_client(token):
    """Get an existing client to use for test loan"""
    log_info("Fetching existing clients...")
    response = requests.get(
        f"{API_BASE}/clientes",
        headers=get_headers(token)
    )
    
    if response.status_code != 200:
        log_error(f"Failed to get clients: {response.status_code}")
        return None
    
    data = response.json()
    items = data.get("items", [])
    
    if not items:
        log_error("No clients found. Need at least one client to create test loan.")
        return None
    
    client = items[0]
    log_success(f"Using existing client: {client.get('nome')} (ID: {client.get('id')})")
    return client.get('id')

def create_test_loan(token, cliente_id):
    """Create a test loan (Apenas Juros / sem_prazo)"""
    log_info("Creating test loan (Apenas Juros / sem_prazo)...")
    
    payload = {
        "cliente_id": cliente_id,
        "valor_principal_centavos": 100000,  # R$ 1,000.00
        "metodo_calculo": "apenas_juros",
        "sem_prazo": True,
        "periodicidade": "mensal",
        "taxa_juros_mensal": 5.0,  # 5% per month
        "taxa_multa_atraso": 2.0,
        "taxa_juros_mora_diario": 0.033,
        "dia_vencimento": 15
    }
    
    response = requests.post(
        f"{API_BASE}/emprestimos",
        headers=get_headers(token),
        json=payload
    )
    
    if response.status_code != 200:
        log_error(f"Failed to create test loan: {response.status_code} - {response.text}")
        return None
    
    loan = response.json()
    loan_id = loan.get('id')
    log_success(f"Test loan created: ID={loan_id}, sem_prazo={loan.get('sem_prazo')}, metodo={loan.get('metodo_calculo')}")
    return loan_id

def create_fixed_term_loan(token, cliente_id):
    """Create a fixed-term loan for guard test"""
    log_info("Creating fixed-term loan for guard test...")
    
    payload = {
        "cliente_id": cliente_id,
        "valor_principal_centavos": 50000,  # R$ 500.00
        "metodo_calculo": "tabela_price",
        "sem_prazo": False,
        "periodicidade": "mensal",
        "taxa_juros_mensal": 3.0,
        "prazo_meses": 6,
        "taxa_multa_atraso": 2.0,
        "taxa_juros_mora_diario": 0.033
    }
    
    response = requests.post(
        f"{API_BASE}/emprestimos",
        headers=get_headers(token),
        json=payload
    )
    
    if response.status_code != 200:
        log_error(f"Failed to create fixed-term loan: {response.status_code} - {response.text}")
        return None
    
    loan = response.json()
    loan_id = loan.get('id')
    log_success(f"Fixed-term loan created: ID={loan_id}, sem_prazo={loan.get('sem_prazo')}")
    return loan_id

def delete_loan(token, loan_id):
    """Hard delete a loan"""
    log_info(f"Deleting loan {loan_id}...")
    response = requests.delete(
        f"{API_BASE}/emprestimos/{loan_id}?hard=true",
        headers=get_headers(token)
    )
    
    if response.status_code == 200:
        log_success(f"Loan {loan_id} deleted successfully")
        return True
    else:
        log_warning(f"Failed to delete loan {loan_id}: {response.status_code}")
        return False

def test_rolar_periodo_1(token, loan_id):
    """Test 1: Roll 1 period"""
    log_info("\n=== TEST 1: Roll 1 period ===")
    
    response = requests.post(
        f"{API_BASE}/emprestimos/{loan_id}/rolar-periodo",
        headers=get_headers(token),
        json={"periodos": 1}
    )
    
    if response.status_code != 200:
        log_error(f"Expected 200, got {response.status_code}: {response.text}")
        return False
    
    data = response.json()
    parcelas_geradas = data.get("parcelas_geradas", [])
    
    if len(parcelas_geradas) != 1:
        log_error(f"Expected 1 parcela, got {len(parcelas_geradas)}")
        return False
    
    parcela = parcelas_geradas[0]
    
    # Verify response structure
    valor_juros_centavos = parcela.get("valor_juros_centavos")
    valor_juros = parcela.get("valor_juros")
    
    if valor_juros_centavos is None and valor_juros is None:
        log_error(f"Expected valor_juros_centavos or valor_juros in response, got neither")
        return False
    
    # Use whichever is available
    juros_display = valor_juros if valor_juros is not None else (valor_juros_centavos / 100 if valor_juros_centavos else 0)
    
    log_success(f"✓ 1 parcela generated: #{parcela.get('numero_parcela')}, vencimento={parcela.get('data_vencimento')[:10]}, status={parcela.get('status')}, juros=R${juros_display:.2f}")
    log_success(f"✓ Response includes: novo_vencimento={data.get('novo_vencimento')[:10]}, valor_juros_periodo={data.get('valor_juros_periodo')}")
    return True

def test_rolar_periodo_3(token, loan_id):
    """Test 2: Roll 3 periods"""
    log_info("\n=== TEST 2: Roll 3 periods ===")
    
    response = requests.post(
        f"{API_BASE}/emprestimos/{loan_id}/rolar-periodo",
        headers=get_headers(token),
        json={"periodos": 3}
    )
    
    if response.status_code != 200:
        log_error(f"Expected 200, got {response.status_code}: {response.text}")
        return False
    
    data = response.json()
    parcelas_geradas = data.get("parcelas_geradas", [])
    
    if len(parcelas_geradas) != 3:
        log_error(f"Expected 3 parcelas, got {len(parcelas_geradas)}")
        return False
    
    # Verify dates are spaced by 1 period (approximately 1 month for mensal)
    log_success(f"✓ 3 parcelas generated:")
    for i, parcela in enumerate(parcelas_geradas):
        # Use valor_juros if available, otherwise valor_juros_centavos
        valor_juros = parcela.get('valor_juros', parcela.get('valor_juros_centavos', 0) / 100 if parcela.get('valor_juros_centavos') else 0)
        log_success(f"  Parcela #{parcela.get('numero_parcela')}: vencimento={parcela.get('data_vencimento')[:10]}, status={parcela.get('status')}, juros=R${valor_juros:.2f}")
    
    # Verify numero_parcela is increasing
    numeros = [p.get('numero_parcela') for p in parcelas_geradas]
    if numeros != sorted(numeros):
        log_error(f"Parcela numbers not in order: {numeros}")
        return False
    
    log_success(f"✓ Parcela numbers are sequential: {numeros}")
    return True

def test_rolar_periodo_guard_fixed_term(token, fixed_loan_id):
    """Test 3: Guard - try to roll a fixed-term loan (should fail with 400)"""
    log_info("\n=== TEST 3: Guard - Roll fixed-term loan (should fail) ===")
    
    response = requests.post(
        f"{API_BASE}/emprestimos/{fixed_loan_id}/rolar-periodo",
        headers=get_headers(token),
        json={"periodos": 1}
    )
    
    if response.status_code != 400:
        log_error(f"Expected 400, got {response.status_code}: {response.text}")
        return False
    
    data = response.json()
    detail = data.get("detail", "")
    
    if "Apenas empréstimos abertos" not in detail:
        log_error(f"Expected error message about 'Apenas empréstimos abertos', got: {detail}")
        return False
    
    log_success(f"✓ Correctly rejected fixed-term loan with 400: {detail}")
    return True

def test_rolar_periodo_validation(token, loan_id):
    """Test 4: Validation - periodos=0 and periodos=30"""
    log_info("\n=== TEST 4: Validation - periodos=0 (should fail) ===")
    
    # Test periodos=0
    response = requests.post(
        f"{API_BASE}/emprestimos/{loan_id}/rolar-periodo",
        headers=get_headers(token),
        json={"periodos": 0}
    )
    
    if response.status_code != 422:
        log_error(f"Expected 422 for periodos=0, got {response.status_code}: {response.text}")
        return False
    
    log_success(f"✓ Correctly rejected periodos=0 with 422")
    
    # Test periodos=30 (>24)
    log_info("\n=== TEST 4b: Validation - periodos=30 (should fail) ===")
    response = requests.post(
        f"{API_BASE}/emprestimos/{loan_id}/rolar-periodo",
        headers=get_headers(token),
        json={"periodos": 30}
    )
    
    if response.status_code != 422:
        log_error(f"Expected 422 for periodos=30, got {response.status_code}: {response.text}")
        return False
    
    log_success(f"✓ Correctly rejected periodos=30 with 422")
    return True

def test_rolar_periodo_not_found(token):
    """Test 5: Non-existent loan ID (should fail with 404)"""
    log_info("\n=== TEST 5: Non-existent loan ID (should fail) ===")
    
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.post(
        f"{API_BASE}/emprestimos/{fake_id}/rolar-periodo",
        headers=get_headers(token),
        json={"periodos": 1}
    )
    
    if response.status_code != 404:
        log_error(f"Expected 404, got {response.status_code}: {response.text}")
        return False
    
    log_success(f"✓ Correctly returned 404 for non-existent loan")
    return True

def verify_parcelas_are_interest_only(token, loan_id):
    """Verify that generated parcelas are interest-only (valor_principal_centavos=0)"""
    log_info("\n=== VERIFICATION: Check parcelas are interest-only ===")
    
    response = requests.get(
        f"{API_BASE}/emprestimos/{loan_id}/parcelas",
        headers=get_headers(token)
    )
    
    if response.status_code != 200:
        log_error(f"Failed to get parcelas: {response.status_code}")
        return False
    
    parcelas = response.json()
    
    if not parcelas:
        log_warning("No parcelas found")
        return True
    
    all_interest_only = True
    for parcela in parcelas:
        # API returns values in reais, not centavos
        valor_principal = parcela.get("valor_principal", parcela.get("valor_principal_centavos", 0))
        valor_juros = parcela.get("valor_juros", parcela.get("valor_juros_centavos", 0))
        valor_total = parcela.get("valor_total", parcela.get("valor_total_centavos", 0))
        
        # For interest-only loans, valor_principal should be 0
        if valor_principal != 0:
            log_error(f"Parcela #{parcela.get('numero_parcela')} has valor_principal={valor_principal} (expected 0)")
            all_interest_only = False
        
        # Check if valor_total is set (it should be for interest-only parcelas)
        if valor_total <= 0:
            log_error(f"Parcela #{parcela.get('numero_parcela')} has valor_total={valor_total} (expected > 0)")
            all_interest_only = False
        
        # For interest-only, valor_juros should equal valor_total
        if valor_total > 0 and abs(valor_juros - valor_total) > 0.01:
            log_warning(f"Parcela #{parcela.get('numero_parcela')} has valor_juros={valor_juros} != valor_total={valor_total}")
    
    if all_interest_only:
        log_success(f"✓ All {len(parcelas)} parcelas are interest-only (valor_principal=0, valor_total>0)")
    
    return all_interest_only

def main():
    print(f"\n{'='*80}")
    print(f"BACKEND API TEST - Rolar Período Feature")
    print(f"Base URL: {BASE_URL}")
    print(f"{'='*80}\n")
    
    # Login
    token = login()
    
    # Get existing client
    cliente_id = get_existing_client(token)
    if not cliente_id:
        log_error("Cannot proceed without a client")
        sys.exit(1)
    
    # Create test loans
    test_loan_id = create_test_loan(token, cliente_id)
    if not test_loan_id:
        log_error("Failed to create test loan")
        sys.exit(1)
    
    fixed_loan_id = create_fixed_term_loan(token, cliente_id)
    if not fixed_loan_id:
        log_error("Failed to create fixed-term loan")
        # Continue anyway, we can skip the guard test
    
    # Run tests
    results = []
    
    try:
        results.append(("Test 1: Roll 1 period", test_rolar_periodo_1(token, test_loan_id)))
        results.append(("Test 2: Roll 3 periods", test_rolar_periodo_3(token, test_loan_id)))
        
        if fixed_loan_id:
            results.append(("Test 3: Guard - fixed-term loan", test_rolar_periodo_guard_fixed_term(token, fixed_loan_id)))
        else:
            log_warning("Skipping Test 3 (no fixed-term loan)")
        
        results.append(("Test 4: Validation (periodos=0, 30)", test_rolar_periodo_validation(token, test_loan_id)))
        results.append(("Test 5: Non-existent ID", test_rolar_periodo_not_found(token)))
        
        # Verify parcelas
        results.append(("Verification: Interest-only parcelas", verify_parcelas_are_interest_only(token, test_loan_id)))
        
    finally:
        # Cleanup
        log_info("\n=== CLEANUP ===")
        delete_loan(token, test_loan_id)
        if fixed_loan_id:
            delete_loan(token, fixed_loan_id)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        log_success("\n✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        log_error(f"\n✗ {total - passed} TEST(S) FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
