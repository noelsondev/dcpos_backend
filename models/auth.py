# app/models/auth.py
# type: ignore
import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship # <-- Asegúrate de tener 'relationship' importado
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base 
# Necesitamos importar los modelos de platform para la relación
from app.models.platform import Company, Branch 

# ***************************************************************
# 1. Modelo Role (SIN CAMBIOS)
# ***************************************************************
class Role(Base):
    __tablename__ = "role"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False) 
    users = relationship("User", back_populates="role")

# ***************************************************************
# 2. Modelo User (AÑADIR RELACIONES)
# ***************************************************************
class User(Base):
    __tablename__ = "user"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=True) 
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branch.id"), nullable=True)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)

    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)

    # RELACIONES AÑADIDAS/DESCOMENTADAS:
    role = relationship("Role", back_populates="users", lazy="joined") # <-- join el rol automáticamente
    company = relationship("Company") # Nota: Company no tiene relación de vuelta 'users' aún.
    branch = relationship("Branch")   # Nota: Branch no tiene relación de vuelta 'users' aún.
    
    # sessions = relationship("CashSession", back_populates="user")