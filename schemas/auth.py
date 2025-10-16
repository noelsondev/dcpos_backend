# app/schemas/auth.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

# ***************************************************************
# 1. Schemas de Autenticación (JWT)
# ***************************************************************
class Token(BaseModel):
    """Modelo para la respuesta de un token de acceso."""
    access_token: str
    token_type: str = "bearer"
    role: str

class TokenPayload(BaseModel):
    """Modelo para la carga útil (payload) del JWT."""
    sub: Optional[str] = None # 'sub' contendrá el ID del usuario
    exp: Optional[int] = None # Expiración

# ***************************************************************
# 2. Schemas de Usuario (Request/Response)
# ***************************************************************
class UserBase(BaseModel):
    """Base para la creación y lectura de usuarios."""
    username: str = Field(..., max_length=50)
    is_active: bool = True

class UserCreate(UserBase):
    """Schema para la creación de un nuevo usuario."""
    password: str = Field(..., min_length=6)
    # IDs para las FK (se validarán en la lógica de negocio)
    company_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    role_id: int

class UserInDB(UserBase):
    """Schema para la representación del usuario desde la DB (sin hash)."""
    id: UUID
    company_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    role_id: int
    
    # Configuración de Pydantic para mapeo con SQLAlchemy
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """Schema para la solicitud de login."""
    username: str
    password: str