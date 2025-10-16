# app/schemas/platform.py
# type: ignore
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

# ***************************************************************
# 1. Schemas para COMPANY
# ***************************************************************
class CompanyBase(BaseModel):
    """Base para la creación y lectura de Compañías."""
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=50) # Identificador URL/Sistema
    
class CompanyCreate(CompanyBase):
    """Schema de entrada para crear una Compañía."""
    pass

class CompanyUpdate(CompanyBase):
    """Schema de entrada para actualizar una Compañía (todos opcionales)."""
    name: Optional[str] = None
    slug: Optional[str] = None

class CompanyInDB(CompanyBase):
    """Schema de salida para una Compañía (incluye ID y metadata de la DB)."""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

# ***************************************************************
# 2. Schemas para BRANCH (Sucursal)
# ***************************************************************
class BranchBase(BaseModel):
    """Base para la creación y lectura de Sucursales."""
    name: str = Field(..., max_length=100)
    address: Optional[str] = Field(None)

class BranchCreate(BranchBase):
    """Schema de entrada para crear una Sucursal."""
    #company_id no se pide en el request, se toma del token o del path
    pass 

class BranchUpdate(BranchBase):
    """Schema de entrada para actualizar una Sucursal (todos opcionales)."""
    name: Optional[str] = None
    address: Optional[str] = None

class BranchInDB(BranchBase):
    """Schema de salida para una Sucursal."""
    id: UUID
    company_id: UUID
    
    class Config:
        from_attributes = True