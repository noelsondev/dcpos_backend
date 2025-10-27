# app/models/inventory.py
# type: ignore

import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Numeric, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.database import Base


class Product(Base):
    """Modelo para la tabla Product."""
    __tablename__ = "product"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    sku = Column(String(50), nullable=False)

    # NUMERIC(10,2) para precisión financiera
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relación con Company
    company = relationship("Company", back_populates="products")

    # Constraint de unicidad (SKU único por compañía)
    __table_args__ = (
        UniqueConstraint('sku', 'company_id', name='uq_product_sku_company'),
    )
