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
# Dependencia de Permisos Reutilizable para LECTURA
# ***************************************************************

def check_company_access(
    company_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dependencia para verificar si el usuario tiene permiso de LECTURA/LISTADO 
    en esta compañía.
    Permite: Global Admin o cualquier usuario asociado con company_id coincidente.
    """
    if current_user.role.name == "global_admin":
        # Global Admin siempre tiene acceso
        return current_user
    
    # Todos los demás usuarios deben estar asociados a esta compañía
    if current_user.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a esta compañía.")
        
    return current_user

# ***************************************************************
# 1. Endpoints para COMPANY (CRUD)
# ***************************************************************

@router.post("/companies", response_model=CompanyInDB, status_code=status.HTTP_201_CREATED, tags=["Companies"])
def create_company(
    company_in: CompanyCreate, 
    db: Session = Depends(get_db), 
    admin: User = Depends(get_global_admin) # 🔒 RESTRICCIÓN: SOLO GLOBAL ADMIN
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
def read_companies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Lista compañías.
    - Global Admin: Lista todas.
    - Otros Roles: Solo listan su propia compañía (si tienen una).
    """
    if user.role.name == "global_admin":
        # Global Admin ve todas
        return db.query(Company).all()
    
    # Otros roles ven solo su compañía
    if user.company_id:
        company = db.query(Company).filter(Company.id == user.company_id).all()
        return company if company else []
    
    # Si el usuario no está asociado a una compañía, devuelve una lista vacía
    return []

@router.get("/companies/{company_id}", response_model=CompanyInDB, tags=["Companies"])
def read_company(company_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Obtiene una compañía por ID. Requiere estar asociado o ser Global Admin."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compañía no encontrada.")

    # Restricción de acceso para la lectura de una compañía específica
    if user.role.name != "global_admin" and user.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado a esta compañía.")
        
    return company

@router.patch("/companies/{company_id}", response_model=CompanyInDB, tags=["Companies"])
def update_company(
    company_id: UUID,
    company_in: CompanyUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_global_admin) # 🔒 RESTRICCIÓN: SOLO GLOBAL ADMIN
):
    """Actualiza una compañía existente. Requiere global_admin."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compañía no encontrada.")

    update_data = company_in.model_dump(exclude_unset=True)
    
    # Validar que si el slug está siendo actualizado, siga siendo único
    if 'slug' in update_data and update_data['slug'] != company.slug:
        if db.query(Company).filter(Company.slug == update_data['slug']).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug ya existe.")

    for key, value in update_data.items():
        setattr(company, key, value)
        
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

# ***************************************************************
# 2. Endpoints para BRANCH (CRUD)
# ***************************************************************

@router.post("/companies/{company_id}/branches", response_model=BranchInDB, status_code=status.HTTP_201_CREATED, tags=["Branches"])
def create_branch(
    company_id: UUID,
    branch_in: BranchCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_global_admin) # 🔒 RESTRICCIÓN: SOLO GLOBAL ADMIN
):
    """Crea una nueva sucursal para una compañía. Requiere global_admin."""
    
    # 1. Verificar que la compañía existe
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
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
    user: User = Depends(check_company_access) # LECTURA: Permite Global Admin y usuarios asociados
):
    """Lista todas las sucursales de una compañía. Requiere Global Admin o estar asociado."""
    
    # Verificar que la compañía existe
    if not db.query(Company).filter(Company.id == company_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compañía no encontrada.")

    branches = db.query(Branch).filter(Branch.company_id == company_id).all()
    return branches

@router.patch("/branches/{branch_id}", response_model=BranchInDB, tags=["Branches"])
def update_branch(
    branch_id: UUID,
    branch_in: BranchUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_global_admin) # 🔒 RESTRICCIÓN: SOLO GLOBAL ADMIN
):
    """Actualiza una sucursal existente. Requiere global_admin."""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada.")

    update_data = branch_in.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(branch, key, value)
        
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch

# CRUD de Branch (eliminación omitida por brevedad)