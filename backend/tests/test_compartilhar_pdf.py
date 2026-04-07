"""
Test: Compartilhar PDF endpoint for empréstimos
Tests the GET /api/emprestimos/{id}/compartilhar-pdf endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCompartilharPDF:
    """Tests for the PDF sharing feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get auth token and emprestimo ID"""
        # Login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@gestorcerd.com",
            "senha": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get list of emprestimos to find a valid ID
        emprestimos_response = requests.get(
            f"{BASE_URL}/api/emprestimos",
            headers=self.headers
        )
        assert emprestimos_response.status_code == 200, f"Failed to get emprestimos: {emprestimos_response.text}"
        
        data = emprestimos_response.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        
        if items and len(items) > 0:
            self.emprestimo_id = items[0].get("id")
            self.emprestimo = items[0]
        else:
            self.emprestimo_id = None
            self.emprestimo = None
    
    def test_compartilhar_pdf_endpoint_exists(self):
        """Test that the endpoint exists and returns PDF"""
        if not self.emprestimo_id:
            pytest.skip("No emprestimos available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/emprestimos/{self.emprestimo_id}/compartilhar-pdf",
            headers=self.headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500] if response.text else 'No content'}"
    
    def test_compartilhar_pdf_returns_pdf_content_type(self):
        """Test that the response has correct content type"""
        if not self.emprestimo_id:
            pytest.skip("No emprestimos available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/emprestimos/{self.emprestimo_id}/compartilhar-pdf",
            headers=self.headers
        )
        
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF content type, got: {content_type}"
    
    def test_compartilhar_pdf_has_content_disposition(self):
        """Test that the response has content-disposition header for download"""
        if not self.emprestimo_id:
            pytest.skip("No emprestimos available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/emprestimos/{self.emprestimo_id}/compartilhar-pdf",
            headers=self.headers
        )
        
        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition, f"Expected attachment disposition, got: {content_disposition}"
        assert ".pdf" in content_disposition, f"Expected .pdf in filename, got: {content_disposition}"
    
    def test_compartilhar_pdf_has_valid_pdf_content(self):
        """Test that the response contains valid PDF data"""
        if not self.emprestimo_id:
            pytest.skip("No emprestimos available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/emprestimos/{self.emprestimo_id}/compartilhar-pdf",
            headers=self.headers
        )
        
        assert response.status_code == 200
        
        # PDF files start with %PDF
        content = response.content
        assert len(content) > 0, "PDF content is empty"
        assert content[:4] == b'%PDF', f"Content doesn't start with PDF header. First bytes: {content[:20]}"
        print(f"PDF size: {len(content)} bytes")
    
    def test_compartilhar_pdf_invalid_id_returns_404(self):
        """Test that invalid emprestimo ID returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/emprestimos/invalid-id-12345/compartilhar-pdf",
            headers=self.headers
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid ID, got {response.status_code}"
    
    def test_compartilhar_pdf_requires_auth(self):
        """Test that endpoint requires authentication"""
        if not self.emprestimo_id:
            pytest.skip("No emprestimos available for testing")
        
        response = requests.get(
            f"{BASE_URL}/api/emprestimos/{self.emprestimo_id}/compartilhar-pdf"
            # No auth headers
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
