# app/models/platform.py
# type: ignore
import uuid
from sqlalchemy import Column, String, TIMESTAMP, TEXT, ForeignKey
from sqlalchemy.orm import relationship # <--- IMPORTANTE: Nueva Importación
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base 
from datetime import datetime

# ***************************************************************
# 1. Modelo Company
# ***************************************************************
class Company(Base):
    """Modelo para la tabla Company."""
    __tablename__ = "company"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relaciones
    branches = relationship("Branch", back_populates="company")
    # users = relationship("User", back_populates="company") # (Necesita importación de auth.py)

# ***************************************************************
# 2. Modelo Branch
# ***************************************************************
class Branch(Base):
    """Modelo para la tabla Branch."""
    __tablename__ = "branch"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(TEXT)
    
    # Relaciones
    company = relationship("Company", back_populates="branches")
    # users = relationship("User", back_populates="branch") # (Necesita importación de auth.py)