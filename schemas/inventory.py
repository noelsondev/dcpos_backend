# app/schemas/inventory.py
# type: ignore

from pydantic import BaseModel, Field, field_serializer 
from typing import Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime # Necesario para el type hint del serializador

# -------------------------------------------------------------------
# Base Schemas
# -------------------------------------------------------------------

class ProductBase(BaseModel):
    name: str = Field(..., max_length=255)
    sku: str = Field(..., max_length=50, description="Stock Keeping Unit (Unique per company)")
    price: Decimal = Field(..., gt=0, decimal_places=2, description="Default selling price") 
    cost: Decimal = Field(..., ge=0, decimal_places=2, description="Cost of Goods")
    is_active: bool = True
    
    # Configuración de Pydantic v2
    model_config = {
        "from_attributes": True, # Habilita la lectura desde objetos ORM
    }

    # Serializador: convierte Decimal a float para la salida JSON
    @field_serializer('price', 'cost')
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value)

# -------------------------------------------------------------------
# Input Schemas
# -------------------------------------------------------------------

class ProductCreate(ProductBase):
    company_id: UUID = Field(..., description="The UUID of the company this product belongs to.")
    pass 

class ProductUpdate(ProductBase):
    name: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    is_active: Optional[bool] = None
    
# -------------------------------------------------------------------
# Output Schemas (Data In Database)
# -------------------------------------------------------------------

class ProductInDB(ProductBase):
    id: UUID
    company_id: UUID
    # El type hint sigue siendo 'str' porque el serializador se encarga de convertirlo
    created_at: str 
    
    # Serializador: convierte el objeto datetime a una cadena ISO 8601
    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        # Formatear la fecha y hora al estándar ISO 8601 (ej. "2025-10-25T01:30:20.168191")
        return value.isoformat()