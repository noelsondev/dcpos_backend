# from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, Text, func
# from sqlalchemy.dialects.postgresql import UUID #NUMERIC, JSONB
# from sqlalchemy.orm import relationship, declarative_base
# import uuid

# Base = declarative_base()

# # --- Core Platform & Access Control ---

# #role de un usuario
# class Role(Base):
#     __tablename__ = "role"
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(50), unique=True, nullable=False) # e.g., 'global_admin', 'company_admin', 'cashier'
    
#     users = relationship("User", back_populates="role")

# #nombre de una emprsa
# class Company(Base):
#     __tablename__ = "company"
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     name = Column(String(100), unique=True, nullable=False)
#     slug = Column(String(50), unique=True, nullable=False)
#     created_at = Column(TIMESTAMP, default=func.now())

#     branches = relationship("Branch", back_populates="company")
#     users = relationship("User", back_populates="company")
#     products = relationship("Product", back_populates="company")

# #sucursal de una empresa
# class Branch(Base):
#     __tablename__ = "branch"
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False)
#     name = Column(String(100), nullable=False)
#     address = Column(Text)

#     company = relationship("Company", back_populates="branches")
#     users = relationship("User", back_populates="branch")
#     cashboxes = relationship("Cashbox", back_populates="branch")


# #usuario
# class User(Base):
#     __tablename__ = "user"
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=True) # nullable for global_admin
#     branch_id = Column(UUID(as_uuid=True), ForeignKey("branch.id"), nullable=True) # Cashier must have a branch_id
#     role_id = Column(Integer, ForeignKey("role.id"), nullable=False)
#     username = Column(String(50), unique=True, index=True, nullable=False)
#     password_hash = Column(String(255), nullable=False)
#     is_active = Column(Boolean, default=True)

#     company = relationship("Company", back_populates="users")
#     branch = relationship("Branch", back_populates="users")
#     role = relationship("Role", back_populates="users")

# # (Other models like Product, Sale, etc., will go here in later steps)