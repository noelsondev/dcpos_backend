# app/api/v1/endpoints/platform.py
# type: ignore
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.platform import Company, Branch
from app.schemas.platform import CompanyCreate, CompanyInDB, CompanyUpdate, BranchCreate, BranchInDB, BranchUpdate
from app.api.v1.endpoints.auth import get_global_admin, get_current_user
from app.models.auth import User # Para tipado

router = APIRouter()

# ***************************************************************
# 1. Endpoints para COMPANY (Solo Global Admin)
# ***************************************************************

@router.post("/companies", response_model=CompanyInDB, status_code=status.HTTP_201_CREATED, tags=["Companies"])
def create_company(
    company_in: CompanyCreate, 
    db: Session = Depends(get_db), 
    admin: User = Depends(get_global_admin) # Protegido
):
    """Crea una nueva compañía. Requiere global_admin."""
    # 1. Validar unicidad del slug
    if db.query(Company).filter(Company.slug == company_in.slug).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug ya existe.")
    
    # 2. Crear y guardar
    db_company = Company(**company_in.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

@router.get("/companies", response_model=List[CompanyInDB], tags=["Companies"])
def read_companies(db: Session = Depends(get_db), admin: User = Depends(get_global_admin)):
    """Lista todas las compañías. Requiere global_admin."""
    return db.query(Company).all()

@router.get("/companies/{company_id}", response_model=CompanyInDB, tags=["Companies"])
def read_company(company_id: UUID, db: Session = Depends(get_db), admin: User = Depends(get_global_admin)):
    """Obtiene una compañía por ID. Requiere global_admin."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compañía no encontrada.")
    return company

# ***************************************************************
# 2. Endpoints para BRANCH (Admin de Compañía y Global Admin)
# ***************************************************************

def check_company_ownership(
    company_id: UUID, 
    current_user: User = Depends(get_current_user)
):
    """
    Dependencia para verificar si el usuario tiene permiso para actuar en esta compañía.
    Permite: Global Admin (sin company_id) o Company Admin (con company_id coincidente).
    """
    if current_user.role.name == "global_admin":
        # Global Admin siempre tiene acceso
        return current_user
    
    if current_user.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a esta compañía.")
        
    return current_user


@router.post("/companies/{company_id}/branches", response_model=BranchInDB, status_code=status.HTTP_201_CREATED, tags=["Branches"])
def create_branch(
    company_id: UUID,
    branch_in: BranchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(check_company_ownership) # Protegido
):
    """Crea una nueva sucursal para una compañía. Requiere Company Admin o Global Admin."""
    
    # 1. Verificar que la compañía existe (check_company_ownership lo hace indirectamente para Company Admin)
    # Para Global Admin, aún debemos verificar si la compañía existe
    if not db.query(Company).filter(Company.id == company_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compañía no encontrada.")
    
    # 2. Crear y guardar
    db_branch = Branch(**branch_in.model_dump(), company_id=company_id)
    db.add(db_branch)
    db.commit()
    db.refresh(db_branch)
    return db_branch


@router.get("/companies/{company_id}/branches", response_model=List[BranchInDB], tags=["Branches"])
def read_branches(
    company_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(check_company_ownership) # Protegido
):
    """Lista todas las sucursales de una compañía. Requiere Company Admin o Global Admin."""
    branches = db.query(Branch).filter(Branch.company_id == company_id).all()
    return branches

# CRUD de Branch (actualización y eliminación, omitidos por brevedad, pero seguirían el mismo patrón de permisos)