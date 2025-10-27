# app/models/platform.py
# type: ignore

from sqlalchemy import Column, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from datetime import datetime
from uuid import uuid4


# ***************************************************************
# 1. Company (Plataforma/SaaS Nivel Superior)
# ***************************************************************
class Company(Base):
    """
    Representa una Compañía o Cliente de la plataforma SaaS.
    Un usuario Global Admin gestiona esto.
    """
    __tablename__ = "company"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)  # Identificador URL-friendly
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    branches = relationship("Branch", back_populates="company", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="company", cascade="all, delete-orphan")


# ***************************************************************
# 2. Branch (Sucursal o Punto de Venta Físico)
# ***************************************************************
class Branch(Base):
    """
    Representa una sucursal física perteneciente a una Compañía.
    """
    __tablename__ = "branch"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(String, nullable=True)

    # Relaciones
    company = relationship("Company", back_populates="branches")
    users = relationship("User", back_populates="branch", cascade="all, delete-orphan")

    # ⚠️ Se eliminan estas líneas hasta que Cashbox y Sale existan:
    # cashboxes = relationship("Cashbox", back_populates="branch", cascade="all, delete-orphan")
    # sales = relationship("Sale", back_populates="branch", cascade="all, delete-orphan")
