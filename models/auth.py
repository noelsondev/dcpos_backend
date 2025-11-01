# app/models/auth.py
# type: ignore

import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID 
from datetime import datetime
from app.database import Base




class Role(Base):
    __tablename__ = "roles"
    
    # Debe coincidir con UUID en la DB y en RoleInDB
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True, unique=True)

    # Relación con usuarios
    users = relationship("User", back_populates="role", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # ✅ CORRECCIÓN 1: El tipo debe ser UUID, no Integer.
    # ✅ CORRECCIÓN 2: La tabla de referencia debe ser "roles" (en plural).
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True) 
    
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=True)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branch.id", ondelete="SET NULL"), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relaciones bidireccionales sin duplicar backrefs
    role = relationship("Role", back_populates="users")
    company = relationship("Company", back_populates="users")
    branch = relationship("Branch", back_populates="users")
