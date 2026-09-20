#!/usr/bin/env python3
"""
Backend API Testing Script for GestorCred/Kredor
Tests high-priority endpoints with the external preview URL
"""
import requests
import json
import sys
from typing import Dict, Any, Tuple

# Base URL for external testing (preview domain)
BASE_URL = "https://gestorcred-staging-1.preview.emergentagent.com/api"
ALTERNATIVE_BASE_URL = "https://gestorcred-staging-1.preview.emergentagent.com/api"

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def log_test(test_name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   Details: {details}")
    
    if passed:
        test_results["passed"].append(test_name)
    else:
        test_results["failed"].append({"test": test_name, "details": details})


def log_warning(test_name: str, details: str):
    """Log warning"""
    print(f"⚠️  WARNING: {test_name}")
    print(f"   Details: {details}")
    test_results["warnings"].append({"test": test_name, "details": details})


def test_public_cadastro_token_validation():
    """
    Test 1: Public cadastro token validation endpoint
    - Valid token should return 200 with empresa and valido=true
    - Invalid token should return 404 with error message
    """
    print("\n" + "="*80)
    print("TEST 1: Public Cadastro Token Validation")
    print("="*80)
    
    # Test 1a: Valid token (KAora9C1Qqs - belongs to diego.haidmann@gmail.com)
    print("\n1a. Testing VALID token: KAora9C1Qqs")
    try:
        response = requests.get(
            f"{BASE_URL}/cadastro-publico/info/KAora9C1Qqs",
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("valido") == True and "empresa" in data:
                log_test(
                    "Valid token returns 200 with correct data",
                    True,
                    f"empresa={data.get('empresa')}, valido={data.get('valido')}"
                )
            else:
                log_test(
                    "Valid token returns 200 with correct data",
                    False,
                    f"Missing or incorrect fields: {data}"
                )
        else:
            log_test(
                "Valid token returns 200 with correct data",
                False,
                f"Expected 200, got {response.status_code}: {response.text[:200]}"
            )
    except Exception as e:
        log_test("Valid token returns 200 with correct data", False, f"Exception: {str(e)}")
    
    # Test 1b: Invalid token
    print("\n1b. Testing INVALID token: token_invalido_123")
    try:
        response = requests.get(
            f"{BASE_URL}/cadastro-publico/info/token_invalido_123",
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        
        if response.status_code == 404:
            data = response.json()
            if "Link inválido ou expirado" in data.get("detail", ""):
                log_test(
                    "Invalid token returns 404 with correct error",
                    True,
                    f"detail={data.get('detail')}"
                )
            else:
                log_test(
                    "Invalid token returns 404 with correct error",
                    False,
                    f"Wrong error message: {data.get('detail')}"
                )
        else:
            log_test(
                "Invalid token returns 404 with correct error",
                False,
                f"Expected 404, got {response.status_code}: {response.text[:200]}"
            )
    except Exception as e:
        log_test("Invalid token returns 404 with correct error", False, f"Exception: {str(e)}")


def test_cors_configuration():
    """
    Test 2: CORS configuration for preview domains
    - GET request with Origin header should return Access-Control-Allow-Origin
    - OPTIONS preflight should return proper CORS headers
    """
    print("\n" + "="*80)
    print("TEST 2: CORS Configuration")
    print("="*80)
    
    origins_to_test = [
        "https://gestorcred-staging-1.preview.emergentagent.com",
        "https://gestorcred-staging-1.preview.emergentagent.com"
    ]
    
    for origin in origins_to_test:
        print(f"\n2a. Testing CORS for origin: {origin}")
        
        # Test GET request with Origin header
        try:
            response = requests.get(
                f"{BASE_URL}/configuracoes/landing",
                headers={"Origin": origin},
                timeout=10
            )
            print(f"   Status Code: {response.status_code}")
            print(f"   CORS Headers: {dict(response.headers)}")
            
            acao_header = response.headers.get("Access-Control-Allow-Origin", "")
            
            if response.status_code == 200:
                if acao_header == origin or acao_header == "*":
                    log_test(
                        f"CORS GET /configuracoes/landing with Origin {origin}",
                        True,
                        f"Access-Control-Allow-Origin: {acao_header}"
                    )
                else:
                    log_test(
                        f"CORS GET /configuracoes/landing with Origin {origin}",
                        False,
                        f"Expected ACAO={origin}, got {acao_header}"
                    )
            else:
                log_test(
                    f"CORS GET /configuracoes/landing with Origin {origin}",
                    False,
                    f"Expected 200, got {response.status_code}"
                )
        except Exception as e:
            log_test(
                f"CORS GET /configuracoes/landing with Origin {origin}",
                False,
                f"Exception: {str(e)}"
            )
        
        # Test OPTIONS preflight
        print(f"\n2b. Testing OPTIONS preflight for origin: {origin}")
        try:
            response = requests.options(
                f"{BASE_URL}/auth/login",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type"
                },
                timeout=10
            )
            print(f"   Status Code: {response.status_code}")
            print(f"   CORS Headers: {dict(response.headers)}")
            
            acao_header = response.headers.get("Access-Control-Allow-Origin", "")
            acam_header = response.headers.get("Access-Control-Allow-Methods", "")
            
            if acao_header and "POST" in acam_header:
                log_test(
                    f"CORS OPTIONS preflight /auth/login with Origin {origin}",
                    True,
                    f"ACAO={acao_header}, ACAM={acam_header}"
                )
            else:
                log_test(
                    f"CORS OPTIONS preflight /auth/login with Origin {origin}",
                    False,
                    f"Missing CORS headers: ACAO={acao_header}, ACAM={acam_header}"
                )
        except Exception as e:
            log_test(
                f"CORS OPTIONS preflight /auth/login with Origin {origin}",
                False,
                f"Exception: {str(e)}"
            )


def test_public_landing_config():
    """
    Test 3: Public landing config endpoint
    - Should return 200 with configuration data
    - nome_empresa should be "Kredor"
    """
    print("\n" + "="*80)
    print("TEST 3: Public Landing Config")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/configuracoes/landing",
            timeout=10
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            nome_empresa = data.get("nome_empresa", "")
            
            if nome_empresa:
                log_test(
                    "GET /configuracoes/landing returns 200 with data",
                    True,
                    f"nome_empresa={nome_empresa}"
                )
                
                if nome_empresa != "Kredor":
                    log_warning(
                        "Landing config nome_empresa",
                        f"Expected 'Kredor', got '{nome_empresa}'"
                    )
            else:
                log_test(
                    "GET /configuracoes/landing returns 200 with data",
                    False,
                    "Missing nome_empresa field"
                )
        else:
            log_test(
                "GET /configuracoes/landing returns 200 with data",
                False,
                f"Expected 200, got {response.status_code}: {response.text[:200]}"
            )
    except Exception as e:
        log_test("GET /configuracoes/landing returns 200 with data", False, f"Exception: {str(e)}")


def test_auth_flow():
    """
    Test 4: Auth + verification flow
    - Register a new test user
    - Attempt login (may trigger 2FA)
    - Test verification endpoints if applicable
    """
    print("\n" + "="*80)
    print("TEST 4: Auth + Verification Flow")
    print("="*80)
    
    # Generate unique test user email
    import time
    timestamp = int(time.time())
    test_email = f"test_user_{timestamp}@testgestorcred.com"
    test_password = "TestPassword123!@#"
    test_name = "Test User Automated"
    
    print(f"\n4a. Registering new test user: {test_email}")
    
    # Test 4a: Register new user
    try:
        register_payload = {
            "nome": test_name,
            "email": test_email,
            "senha": test_password,
            "turnstile_token": ""  # Empty for testing (Turnstile may be disabled or in test mode)
        }
        
        response = requests.post(
            f"{BASE_URL}/auth/registro",
            json=register_payload,
            timeout=15
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        
        if response.status_code == 200:
            user_data = response.json()
            log_test(
                "Register new user via /auth/registro",
                True,
                f"User created: {user_data.get('email')}, id={user_data.get('id')}"
            )
            
            # Test 4b: Login with new user
            print(f"\n4b. Attempting login with new user: {test_email}")
            try:
                login_payload = {
                    "email": test_email,
                    "senha": test_password,
                    "turnstile_token": ""
                }
                
                login_response = requests.post(
                    f"{BASE_URL}/auth/login",
                    json=login_payload,
                    timeout=15
                )
                print(f"   Status Code: {login_response.status_code}")
                print(f"   Response: {login_response.text[:500]}")
                
                if login_response.status_code == 200:
                    login_data = login_response.json()
                    
                    # Check if 2FA is required
                    if login_data.get("requires_2fa"):
                        log_test(
                            "Login triggers 2FA flow",
                            True,
                            f"2FA required for {login_data.get('email')}"
                        )
                        
                        # Test 4c: Verify 2FA endpoints exist (without actual code)
                        print("\n4c. Testing 2FA verification endpoint (without valid code)")
                        try:
                            verify_payload = {
                                "email": test_email,
                                "codigo": "000000"  # Invalid code
                            }
                            verify_response = requests.post(
                                f"{BASE_URL}/auth/verify-2fa",
                                json=verify_payload,
                                timeout=10
                            )
                            print(f"   Status Code: {verify_response.status_code}")
                            
                            # Should return 401 for invalid code, not 500
                            if verify_response.status_code in [401, 400]:
                                log_test(
                                    "2FA verify endpoint responds without 500 error",
                                    True,
                                    f"Returns {verify_response.status_code} for invalid code"
                                )
                            elif verify_response.status_code == 500:
                                log_test(
                                    "2FA verify endpoint responds without 500 error",
                                    False,
                                    f"500 Internal Server Error: {verify_response.text[:200]}"
                                )
                            else:
                                log_warning(
                                    "2FA verify endpoint",
                                    f"Unexpected status {verify_response.status_code}"
                                )
                        except Exception as e:
                            log_test(
                                "2FA verify endpoint responds without 500 error",
                                False,
                                f"Exception: {str(e)}"
                            )
                    
                    elif login_data.get("access_token"):
                        # Login successful without 2FA
                        log_test(
                            "Login returns access token (2FA disabled)",
                            True,
                            f"Token received, user_id={login_data.get('usuario', {}).get('id')}"
                        )
                    else:
                        log_test(
                            "Login response format",
                            False,
                            f"Unexpected response format: {login_data}"
                        )
                
                elif login_response.status_code == 500:
                    log_test(
                        "Login endpoint responds without 500 error",
                        False,
                        f"500 Internal Server Error: {login_response.text[:200]}"
                    )
                else:
                    log_warning(
                        "Login with new user",
                        f"Status {login_response.status_code}: {login_response.text[:200]}"
                    )
            
            except Exception as e:
                log_test("Login with new user", False, f"Exception: {str(e)}")
        
        elif response.status_code == 400:
            # May fail due to Turnstile or other validation
            log_warning(
                "Register new user",
                f"Registration failed (may be Turnstile): {response.text[:200]}"
            )
        elif response.status_code == 500:
            log_test(
                "Register endpoint responds without 500 error",
                False,
                f"500 Internal Server Error: {response.text[:200]}"
            )
        else:
            log_warning(
                "Register new user",
                f"Status {response.status_code}: {response.text[:200]}"
            )
    
    except Exception as e:
        log_test("Register new user", False, f"Exception: {str(e)}")


def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total_tests = len(test_results["passed"]) + len(test_results["failed"])
    print(f"\nTotal Tests: {total_tests}")
    print(f"✅ Passed: {len(test_results['passed'])}")
    print(f"❌ Failed: {len(test_results['failed'])}")
    print(f"⚠️  Warnings: {len(test_results['warnings'])}")
    
    if test_results["failed"]:
        print("\n" + "-"*80)
        print("FAILED TESTS:")
        print("-"*80)
        for failure in test_results["failed"]:
            print(f"\n❌ {failure['test']}")
            print(f"   {failure['details']}")
    
    if test_results["warnings"]:
        print("\n" + "-"*80)
        print("WARNINGS:")
        print("-"*80)
        for warning in test_results["warnings"]:
            print(f"\n⚠️  {warning['test']}")
            print(f"   {warning['details']}")
    
    print("\n" + "="*80)
    
    # Return exit code
    return 0 if len(test_results["failed"]) == 0 else 1


def main():
    """Main test execution"""
    print("="*80)
    print("GestorCred/Kredor Backend API Testing")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Alternative URL: {ALTERNATIVE_BASE_URL}")
    print("="*80)
    
    # Run all tests
    test_public_cadastro_token_validation()
    test_cors_configuration()
    test_public_landing_config()
    test_auth_flow()
    
    # Print summary and exit
    exit_code = print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
