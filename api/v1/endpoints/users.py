# app/api/v1/endpoints/users.py
# type: ignore

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.auth import User, Role
from app.models.platform import Company, Branch
from app.schemas.auth import UserCreate, UserInDB
from app.core.security import get_password_hash
# Importar todas las dependencias desde auth.py (donde se definieron)
from app.api.v1.endpoints.auth import get_current_user


router = APIRouter()

# ***************************************************************
# Dependencia de Permisos: Global Admin o Company Admin
# ***************************************************************
def get_admin_user(current_user: User = Depends(get_current_user)):
    """Requiere que el usuario sea global_admin o company_admin."""
    # Nota: current_user.role.name funciona porque la relación en el modelo User es lazy="joined"
    if current_user.role.name not in ["global_admin", "company_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requiere rol 'admin' (Global o Company)."
        )
    return current_user

# ***************************************************************
# 1. Endpoint para Crear Usuario (POST /api/v1/users/)
# ***************************************************************
@router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db), 
    admin: User = Depends(get_admin_user)
):
    """Crea un nuevo usuario con validación de permisos y estructura."""
    
    # 1. Validar unicidad del username
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya existe.")

    # 2. Validar que el Role y las FKs existan
    role = db.query(Role).filter(Role.id == user_in.role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")

    # 3. Lógica de Permisos (RBAC y Multi-tenancy)
    if admin.role.name == "company_admin":
        
        # Restricción de Roles: Solo puede crear roles con ID mayor (cashier, accountant)
        if user_in.role_id <= admin.role_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para crear este tipo de rol.")
        
        # Restricción de Compañía: El usuario debe ser creado en la misma compañía que el admin
        if user_in.company_id is None or user_in.company_id != admin.company_id:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe asignar el usuario a su propia compañía.")
        
        # Validar Branch: Debe pertenecer a la compañía
        if user_in.branch_id and not db.query(Branch).filter(Branch.id == user_in.branch_id, Branch.company_id == user_in.company_id).first():
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La sucursal no existe en esta compañía.")
    
    elif admin.role.name == "global_admin":
        # Global Admin: Simplemente asegura que Company/Branch existan si se especifican
        if user_in.company_id and not db.query(Company).filter(Company.id == user_in.company_id).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compañía no encontrada.")
        
        if user_in.branch_id and not db.query(Branch).filter(Branch.id == user_in.branch_id).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada.")


    # 4. Crear y guardar el objeto
    hashed_password = get_password_hash(user_in.password)
    
    db_user = User(
        username=user_in.username,
        password_hash=hashed_password,
        role_id=user_in.role_id,
        company_id=user_in.company_id,
        branch_id=user_in.branch_id,
        is_active=user_in.is_active,
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # 5. Mapear para la respuesta (Pydantic v2)
    user_data = db_user.__dict__.copy()
    user_data.pop('password_hash', None)
    
    # Inyectar el nombre del rol antes de la validación
    user_data["role_name"] = role.name 
    
    return UserInDB.model_validate(user_data)


# ***************************************************************
# 2. Endpoint para Listar Usuarios (GET /api/v1/users/)
# ***************************************************************
@router.get("/", response_model=List[UserInDB], tags=["Users"])
def read_users(
    db: Session = Depends(get_db), 
    admin: User = Depends(get_admin_user),
    company_id: Optional[UUID] = Query(None, description="Filtrar por ID de Compañía"),
    branch_id: Optional[UUID] = Query(None, description="Filtrar por ID de Sucursal")
):
    """
    Lista usuarios.
    - Global Admin: puede listar todos o filtrar.
    - Company Admin: solo lista usuarios de SU compañía.
    """
    
    query = db.query(User).join(Role)

    # 1. Determinar el filtro de compañía obligatorio (CORRECCIÓN DE LÓGICA)
    effective_company_id = None
    
    if admin.role.name == "company_admin":
        # Company Admin: DEBE estar asignado a una compañía.
        if admin.company_id is None:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acceso denegado. El administrador de compañía no está asignado a ninguna compañía."
             )
        # Forzar el filtro a la propia compañía del admin
        effective_company_id = admin.company_id
        # Ignorar cualquier 'company_id' que el admin intente pasar en la query
        
    elif company_id:
        # Global Admin: usa el 'company_id' opcional de la query
        effective_company_id = company_id

    # 2. Aplicar el filtro de compañía
    if effective_company_id:
        query = query.filter(User.company_id == effective_company_id)

    # 3. Aplicar el filtro de sucursal (se aplica dentro de la restricción de compañía)
    if branch_id:
        query = query.filter(User.branch_id == branch_id)
        
    users = query.all()
    
    # 4. Mapear la respuesta (Usando la sintaxis de Pydantic v2)
    users_list = []
    for u in users:
        # Crear un diccionario limpio del objeto SQLAlchemy
        user_data = u.__dict__.copy()
        user_data.pop('role', None) 
        user_data.pop('password_hash', None)
        
        # Inyectar el nombre del rol antes de la validación
        user_data["role_name"] = u.role.name
        
        users_list.append(
            UserInDB.model_validate(user_data)
        )
    return users_list

# ***************************************************************
# 3. Endpoint para Leer, Actualizar y Eliminar (Pendientes)
# ***************************************************************
# Se omiten por brevedad, pero usarían la misma lógica de permisos:
# Company Admin solo puede afectar a usuarios dentro de su effective_company_id.