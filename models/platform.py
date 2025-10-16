# app/models/platform.py (CORRECTED)
# type: ignore
import uuid
# Import Column, String, TIMESTAMP, TEXT, AND ForeignKey from sqlalchemy
from sqlalchemy import Column, String, TIMESTAMP, TEXT, ForeignKey 
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base 
from datetime import datetime

# ***************************************************************
# Modelos Placeholder (Sprint 1)
# ***************************************************************

class Company(Base):
    """Modelo para la tabla Company (necesario para la FK de User)."""
    __tablename__ = "company"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    # users = relationship("User", back_populates="company")

class Branch(Base):
    """Modelo para la tabla Branch (necesario para la FK de User)."""
    __tablename__ = "branch"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # The ForeignKey definition now works because it's imported above
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False) 
    name = Column(String(100), nullable=False)
    address = Column(TEXT)
    # users = relationship("User", back_populates="branch")