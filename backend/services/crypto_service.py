"""
Serviço de Criptografia para Dados Sensíveis
Implementa criptografia de campo (Field-Level Encryption)
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
from config import FIELD_ENCRYPTION_KEY


class CryptoService:
    """
    Serviço de criptografia para proteger dados sensíveis
    
    Uso:
        crypto = CryptoService()
        encrypted = crypto.encrypt("123.456.789-00")
        decrypted = crypto.decrypt(encrypted)
    """
    
    def __init__(self):
        """Inicializa o serviço com chave de criptografia"""
        # A chave precisa ser estável entre reinicializações: sem ela, dados já
        # criptografados ficariam ilegíveis. Em produção a ausência é erro fatal.
        encryption_key = FIELD_ENCRYPTION_KEY

        # Derivar chave Fernet da chave mestre
        self.fernet = Fernet(self._derive_key(encryption_key))
    
    def _derive_key(self, password: str) -> bytes:
        """Deriva uma chave Fernet válida a partir de uma senha"""
        # Se já é uma chave Fernet válida (44 caracteres base64), usar direto
        if len(password) == 44:
            try:
                return password.encode()
            except Exception:
                pass
        
        # Caso contrário, derivar usando PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'jurofacil_salt_v1',  # Salt fixo (OK para derivação de chave mestre)
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Criptografa texto plano
        
        Args:
            plaintext: Texto a ser criptografado
        
        Returns:
            str: Texto criptografado em base64
        """
        if not plaintext:
            return plaintext
        
        encrypted = self.fernet.encrypt(plaintext.encode())
        return encrypted.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Descriptografa texto
        
        Args:
            ciphertext: Texto criptografado
        
        Returns:
            str: Texto original descriptografado
        """
        if not ciphertext:
            return ciphertext
        
        try:
            decrypted = self.fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            print(f"Erro ao descriptografar: {e}")
            return "[DADOS CRIPTOGRAFADOS]"
    
    def encrypt_if_needed(self, value: Optional[str]) -> Optional[str]:
        """Criptografa apenas se valor existir"""
        if value:
            return self.encrypt(value)
        return value
    
    def decrypt_if_needed(self, value: Optional[str]) -> Optional[str]:
        """Descriptografa apenas se valor existir"""
        if value:
            return self.decrypt(value)
        return value


# Instância singleton
_crypto_service = None


def get_crypto_service() -> CryptoService:
    """Retorna instância singleton do serviço de criptografia"""
    global _crypto_service
    if _crypto_service is None:
        _crypto_service = CryptoService()
    return _crypto_service


# Funções de conveniência
def encrypt_field(value: Optional[str]) -> Optional[str]:
    """Criptografa um campo"""
    if not value:
        return value
    return get_crypto_service().encrypt(value)


def decrypt_field(value: Optional[str]) -> Optional[str]:
    """Descriptografa um campo"""
    if not value:
        return value
    return get_crypto_service().decrypt(value)


# Campos que devem ser criptografados
ENCRYPTED_FIELDS = {
    'cpf_cnpj',
    'conta',
    'agencia',
    'pix',
    'telefone'  # Opcional, dependendo dos requisitos
}


def encrypt_sensitive_data(data: dict) -> dict:
    """
    Criptografa campos sensíveis em um dicionário
    
    Args:
        data: Dicionário com dados
    
    Returns:
        dict: Dicionário com campos sensíveis criptografados
    """
    encrypted_data = data.copy()
    crypto = get_crypto_service()
    
    for field in ENCRYPTED_FIELDS:
        if field in encrypted_data and encrypted_data[field]:
            encrypted_data[field] = crypto.encrypt(encrypted_data[field])
    
    return encrypted_data


def decrypt_sensitive_data(data: dict) -> dict:
    """
    Descriptografa campos sensíveis em um dicionário
    
    Args:
        data: Dicionário com dados criptografados
    
    Returns:
        dict: Dicionário com campos descriptografados
    """
    decrypted_data = data.copy()
    crypto = get_crypto_service()
    
    for field in ENCRYPTED_FIELDS:
        if field in decrypted_data and decrypted_data[field]:
            decrypted_data[field] = crypto.decrypt(decrypted_data[field])
    
    return decrypted_data
