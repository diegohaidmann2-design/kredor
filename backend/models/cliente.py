"""
Modelo de Cliente
"""
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Optional, Literal, Union, Any
from datetime import datetime, timezone
import uuid

from utils.validators import (
    sanitize_html, validate_cpf_cnpj, normalize_cpf_cnpj,
    validate_phone, normalize_phone
)


class Endereco(BaseModel):
    rua: str = Field(default="", max_length=200)
    numero: str = Field(default="S/N", max_length=20)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: str = Field(default="", max_length=100)
    cidade: str = Field(default="", max_length=100)
    estado: str = Field(default="", max_length=2)  # UF
    cep: str = Field(default="", max_length=10)
    
    @field_validator('rua', 'bairro', 'cidade', 'complemento')
    @classmethod
    def sanitize_text_fields(cls, v):
        if v:
            return sanitize_html(v)
        return v


def parse_endereco(value: Any) -> Endereco:
    """Converte string ou dict para Endereco"""
    if value is None:
        return Endereco()
    if isinstance(value, Endereco):
        return value
    if isinstance(value, dict):
        return Endereco(**value)
    if isinstance(value, str):
        # Parse string de endereço (ex: "Rua X, 123")
        parts = value.split(',')
        rua = parts[0].strip() if parts else value
        numero = parts[1].strip() if len(parts) > 1 else "S/N"
        return Endereco(rua=rua, numero=numero)
    return Endereco()


class Cliente(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str = Field(..., min_length=3, max_length=200)
    cpf_cnpj: Optional[str] = Field(None, min_length=11, max_length=18)
    telefone: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = None  # Aceitar qualquer string para compatibilidade com dados existentes
    endereco: Union[Endereco, str, None] = Field(default=None)
    observacoes: Optional[str] = Field(None, max_length=1000)
    status: Literal["ativo", "inativo", "bloqueado"] = "ativo"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @model_validator(mode='before')
    @classmethod
    def convert_fields(cls, data: Any) -> Any:
        """Converte campos antes da validação"""
        if isinstance(data, dict):
            # Converter endereco
            endereco = data.get('endereco')
            data['endereco'] = parse_endereco(endereco)
            
            # Converter created_at se for string
            created_at = data.get('created_at')
            if isinstance(created_at, str):
                try:
                    data['created_at'] = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    data['created_at'] = datetime.now(timezone.utc)
            elif created_at is None:
                data['created_at'] = datetime.now(timezone.utc)
            
            # Garantir que email é string ou None
            email = data.get('email')
            if email is not None and not isinstance(email, str):
                data['email'] = str(email)
                
            # Tratamento de CPF vazio -> None
            cpf = data.get('cpf_cnpj')
            if cpf == "":
                data['cpf_cnpj'] = None
                
        return data
    
    @field_validator('nome', 'observacoes')
    @classmethod
    def sanitize_text(cls, v):
        if v:
            return sanitize_html(v)
        return v


class ClienteCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200)
    cpf_cnpj: Optional[str] = Field(None, max_length=18)
    telefone: str = Field(..., min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    endereco: Endereco
    observacoes: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('nome', 'observacoes')
    @classmethod
    def sanitize_text(cls, v):
        if v:
            return sanitize_html(v)
        return v
    
    @field_validator('cpf_cnpj')
    @classmethod
    def validate_and_normalize_cpf_cnpj(cls, v):
        if not v:
            return None
        if not validate_cpf_cnpj(v):
            raise ValueError('CPF/CNPJ inválido')
        return normalize_cpf_cnpj(v)
    
    @field_validator('telefone')
    @classmethod
    def validate_and_normalize_phone(cls, v):
        if not validate_phone(v):
            raise ValueError('Telefone inválido')
        return normalize_phone(v)


class ClienteUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=200)
    telefone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    endereco: Optional[Endereco] = None
    observacoes: Optional[str] = Field(None, max_length=1000)
    status: Optional[Literal["ativo", "inativo", "bloqueado"]] = None
    
    @field_validator('nome', 'observacoes')
    @classmethod
    def sanitize_text(cls, v):
        if v:
            return sanitize_html(v)
        return v
    
    @field_validator('telefone')
    @classmethod
    def validate_and_normalize_phone(cls, v):
        if v and not validate_phone(v):
            raise ValueError('Telefone inválido')
        if v:
            return normalize_phone(v)
        return v
