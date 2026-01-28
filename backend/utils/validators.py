"""
Validadores customizados para segurança e integridade de dados
"""
import re
import bleach
import phonenumbers
from typing import Optional


def sanitize_html(text: str) -> str:
    """Remove tags HTML e scripts maliciosos"""
    if not text:
        return text
    return bleach.clean(text, tags=[], strip=True)


def validate_cpf(cpf: str) -> bool:
    """Valida CPF brasileiro"""
    # Remove caracteres não numéricos
    cpf = re.sub(r'\D', '', cpf)
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Valida primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10 % 11) % 10
    if int(cpf[9]) != digito1:
        return False
    
    # Valida segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10 % 11) % 10
    if int(cpf[10]) != digito2:
        return False
    
    return True


def validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ brasileiro"""
    # Remove caracteres não numéricos
    cnpj = re.sub(r'\D', '', cnpj)
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Valida primeiro dígito verificador
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
    digito1 = (soma % 11)
    digito1 = 0 if digito1 < 2 else 11 - digito1
    if int(cnpj[12]) != digito1:
        return False
    
    # Valida segundo dígito verificador
    multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
    digito2 = (soma % 11)
    digito2 = 0 if digito2 < 2 else 11 - digito2
    if int(cnpj[13]) != digito2:
        return False
    
    return True


def validate_cpf_cnpj(doc: str) -> bool:
    """Valida CPF ou CNPJ"""
    doc = re.sub(r'\D', '', doc)
    if len(doc) == 11:
        return validate_cpf(doc)
    elif len(doc) == 14:
        return validate_cnpj(doc)
    return False


def normalize_cpf_cnpj(doc: str) -> str:
    """Normaliza CPF/CNPJ removendo caracteres especiais"""
    return re.sub(r'\D', '', doc)


def validate_phone(phone: str) -> bool:
    """Valida telefone brasileiro"""
    try:
        # Tenta parsear como telefone brasileiro
        parsed = phonenumbers.parse(phone, "BR")
        return phonenumbers.is_valid_number(parsed)
    except:
        return False


def normalize_phone(phone: str) -> str:
    """Normaliza telefone para formato E.164"""
    try:
        parsed = phonenumbers.parse(phone, "BR")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except:
        return phone


def validate_positive_number(value: float, field_name: str = "Valor") -> float:
    """Valida se número é positivo"""
    if value <= 0:
        raise ValueError(f"{field_name} deve ser maior que zero")
    return value


def validate_percentage(value: float, field_name: str = "Taxa") -> float:
    """Valida se percentual está entre 0 e 100"""
    if value < 0 or value > 100:
        raise ValueError(f"{field_name} deve estar entre 0 e 100")
    return value


def validate_integer_positive(value: int, field_name: str = "Valor") -> int:
    """Valida se inteiro é positivo"""
    if value <= 0:
        raise ValueError(f"{field_name} deve ser maior que zero")
    return value


def sanitize_filename(filename: str) -> str:
    """Sanitiza nome de arquivo removendo caracteres perigosos"""
    # Remove path traversal
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    # Remove caracteres especiais
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    return filename[:255]  # Limita tamanho
