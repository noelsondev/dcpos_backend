# app/models/auth.py
import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

# Asegúrate de importar Base desde el archivo database.py
from app.database import Base 

# ***************************************************************
# 1. Modelo Role (Tabla Role)
# ***************************************************************
class Role(Base):
    """Define los roles de usuario en el sistema (Global Admin, Cashier, etc.)."""
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False) # ej: 'global_admin'
    
    # Relación uno-a-muchos con User
    users = relationship("User", back_populates="role")

# ***************************************************************
# 2. Modelo User (Tabla User)
# ***************************************************************
class User(Base):
    """Define un usuario del sistema con sus permisos y pertenencias."""
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign Keys para la jerarquía de la plataforma
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=True) # Global Admin puede no tener
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branch.id"), nullable=True)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)

    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False) # Almacena el hash de la contraseña
    is_active = Column(Boolean, default=True)

    # Relaciones (necesitarán que los otros modelos existan, por ahora las ponemos comentadas)
    # company = relationship("Company", back_populates="users")
    # branch = relationship("Branch", back_populates="users")
    role = relationship("Role", back_populates="users")
    
    # Relación uno-a-muchos con CashSession (para saber quién abrió la caja)
    # sessions = relationship("CashSession", back_populates="user")