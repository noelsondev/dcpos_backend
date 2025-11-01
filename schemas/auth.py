# app/schemas/auth.py
#type: ignore

from pydantic import BaseModel, Field, field_serializer , ConfigDict# <-- ¡NUEVA IMPORTACIÓN!
from typing import Optional
from uuid import UUID
from typing import List
from datetime import datetime # <-- ¡NUEVA IMPORTACIÓN!

# ***************************************************************
# 1. Schemas de Autenticación (JWT)
# ***************************************************************
class Token(BaseModel):
    """Modelo para la respuesta de un token de acceso."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    role: str

class TokenPayload(BaseModel):
    """Modelo para la carga útil (payload) del JWT."""
    sub: Optional[str] = None
    exp: Optional[int] = None

# ***************************************************************
# 2. Schemas de Usuario (Request/Response)
# ***************************************************************
class UserBase(BaseModel):
    """Base para la creación y lectura de usuarios."""
    username: str = Field(..., max_length=50)
    is_active: bool = True
    role_id: UUID # El ID del rol que se le asignará

    # Configuración de Pydantic v2
    model_config = {
        "from_attributes": True,
    }


class UserCreate(UserBase):
    """Schema para la creación de un nuevo usuario (incluye password)."""
    password: str = Field(..., min_length=6)
    # IDs de la estructura (necesarios para el Company Admin)
    company_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None

class UserUpdate(BaseModel):
    """Schema para la actualización de un usuario (campos opcionales)."""
    username: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    role_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None # Permitir mover el usuario de Branch
    password: Optional[str] = Field(None, min_length=6)

class UserInDB(UserBase):
    """Schema para la representación del usuario desde la DB (sin hash)."""
    id: UUID
    role_name: str 
    company_id: Optional[UUID] = None
    branch_id: Optional[UUID] = None
    
    # 🛑 FIX CRÍTICO: La entrada (input) ahora se define como datetime.
    # El diccionario 'user_data' tiene un datetime, por eso falla.
    created_at: datetime 

    # Serializador: convierte el objeto datetime (la entrada) a una cadena ISO 8601 (la salida)
    @field_serializer('created_at', when_used='always') # Asegurar que se aplique
    def serialize_datetime(self, value: datetime) -> str:
        """Convierte datetime de la base de datos a string ISO 8601 para la respuesta."""
        return value.isoformat() 

class UserLogin(BaseModel):
    """Schema para la solicitud de login."""
    username: str
    password: str

# 🚨 NUEVO ESQUEMA
class RoleBase(BaseModel):
    """Esquema base para representar un Rol (Role)."""
    name: str

class RoleInDB(RoleBase):
    """Esquema extendido para devolver el Rol con su ID."""
    id: UUID
    
    # Configuración para que Pydantic pueda leer modelos SQLAlchemy
    model_config = ConfigDict(from_attributes=True)
    
# 🚨 NUEVO ESQUEMA: Lista de Roles
class RoleList(BaseModel):
    """Esquema para la respuesta del endpoint que lista todos los roles."""
    roles: list[RoleInDB]