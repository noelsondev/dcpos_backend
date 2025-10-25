# app/api/v1/endpoints/users.py
# type: ignore

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.auth import User, Role
from app.models.platform import Company, Branch
from app.schemas.auth import UserCreate, UserInDB, UserUpdate
from app.core.security import get_password_hash
# Importar la dependencia de autenticación
from app.api.v1.endpoints.auth import get_current_user


router = APIRouter()

# ***************************************************************
# DEPENDENCIAS DE PERMISOS Y ACCESO
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

def get_user_and_check_access(
    user_id: UUID, 
    db: Session, 
    admin: User
) -> User:
    """
    Busca un usuario por ID y verifica que el administrador tenga permiso para acceder a él.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    
    # 1. Restricción de Company Admin
    if admin.role.name == "company_admin":
        # a. Solo puede acceder a usuarios en su compañía.
        if user.company_id != admin.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acceso denegado. El usuario no pertenece a tu compañía."
            )
            
        # b. NO puede modificar/eliminar a otros Global Admins
        if user.role.name == "global_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acceso denegado. No puedes modificar o eliminar un Global Admin."
            )
            
    # 2. Restricción de auto-modificación/eliminación
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Usa /api/v1/auth/me para modificar tu propio perfil."
        )

    return user

# ***************************************************************
# 1. Endpoint para Crear Usuario (POST /api/v1/users/)
# ***************************************************************
@router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Crea un nuevo usuario con las reglas de RBAC:
    - Global Admin puede crear cualquier rol.
    - Company Admin solo puede crear roles de menor privilegio dentro de su compañía.
    """
    
    # 1. Validar unicidad del nombre de usuario
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya existe.")
        
    # 2. Validar que el rol existe y obtener el objeto Role
    role_to_assign = db.query(Role).filter(Role.id == user_in.role_id).first()
    if not role_to_assign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")

    # 3. Aplicar las Reglas de RBAC
    if admin.role.name == "company_admin":
        
        # Un Company Admin (ej. Role ID 2) SOLO puede crear roles de menor ID (ej. 3, 4...)
        if role_to_assign.id <= admin.role.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Un {admin.role.name} no puede crear un usuario con el rol {role_to_assign.name} o superior."
            )
        
        # Forzar la compañía y sucursal del nuevo usuario a ser la del Company Admin
        if user_in.company_id and user_in.company_id != admin.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un Company Admin solo puede crear usuarios dentro de su propia compañía."
            )
        
        # Si no especificó company_id, se la forzamos
        user_in.company_id = admin.company_id
            
        # Si se especificó una branch, validar que pertenece a la compañía
        if user_in.branch_id:
             if not db.query(Branch).filter(Branch.id == user_in.branch_id, Branch.company_id == admin.company_id).first():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La sucursal no existe o no pertenece a tu compañía.")

    # 4. Validar Company y Branch ID para Global Admin
    elif admin.role.name == "global_admin":
        if user_in.company_id and not db.query(Company).filter(Company.id == user_in.company_id).first():
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compañía no encontrada.")

        if user_in.branch_id:
            # Validar que si hay branch_id, haya company_id y la branch pertenezca a la company
            if not user_in.company_id:
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe especificar company_id si especifica branch_id.")
            
            if not db.query(Branch).filter(Branch.id == user_in.branch_id, Branch.company_id == user_in.company_id).first():
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La sucursal no existe o no pertenece a la compañía indicada.")

    # 5. Crear el objeto User
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        password_hash=hashed_password,
        role_id=user_in.role_id,
        company_id=user_in.company_id,
        branch_id=user_in.branch_id,
        is_active=True # Por defecto activo
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # 6. Mapear para la respuesta
    user_data = db_user.__dict__.copy()
    user_data.pop('password_hash', None)
    user_data["role_name"] = db_user.role.name
    
    return UserInDB.model_validate(user_data)


# ***************************************************************
# 2. Endpoint para Buscar Usuario por ID (GET /api/v1/users/{user_id})
# ***************************************************************
@router.get("/{user_id}", response_model=UserInDB, tags=["Users"])
def read_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Obtiene la información de un usuario por su ID, respetando el RBAC."""
    
    # La dependencia get_user_and_check_access ya realiza la búsqueda y todas las comprobaciones de permisos.
    db_user = get_user_and_check_access(user_id, db, admin)
    
    # Mapear para la respuesta
    user_data = db_user.__dict__.copy()
    user_data.pop('password_hash', None)
    user_data["role_name"] = db_user.role.name
    
    return UserInDB.model_validate(user_data)


# ***************************************************************
# 3. Endpoint para Actualizar Usuario (PATCH /api/v1/users/{user_id}) - ARREGLADO
# ***************************************************************
@router.patch("/{user_id}", response_model=UserInDB, tags=["Users"])
def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Actualiza campos de un usuario, con restricciones de acceso/rol."""
    
    # Usamos la función de acceso. Si el Admin es Global, puede acceder a cualquiera (excepto a sí mismo).
    # Si es Company Admin, el acceso ya está restringido a su compañía.
    db_user = get_user_and_check_access(user_id, db, admin)
    
    update_data = user_in.model_dump(exclude_unset=True)

    # 1. Manejar el cambio de Contraseña
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        update_data["password_hash"] = hashed_password
        update_data.pop("password") 
    
    # 2. VALIDACIONES DE CAMPOS ÚNICOS y FKs
    
    # Validar unicidad de Username
    if "username" in update_data and update_data["username"] != db_user.username:
        if db.query(User).filter(User.username == update_data["username"]).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya existe.")
            
    # Validar Role ID
    if "role_id" in update_data:
        role = db.query(Role).filter(Role.id == update_data["role_id"]).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")
            
        # Restricción de Roles para Company Admin: Solo puede asignar roles de menor privilegio
        if admin.role.name == "company_admin" and update_data["role_id"] <= admin.role.id:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para asignar este tipo de rol o superior.")

    # 3. Manejar la reasignación de Compañía/Sucursal
    new_company_id = update_data.get("company_id")
    new_branch_id = update_data.get("branch_id")
    
    # LÓGICA DE ACTUALIZACIÓN DEL COMPANY_ID Y BRANCH_ID
    
    if new_company_id is not None:
         # Solo Global Admin puede reasignar Company ID
         if admin.role.name != "global_admin":
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un Global Admin puede reasignar el ID de Compañía.")
         
         # Validar que la compañía exista
         if not db.query(Company).filter(Company.id == new_company_id).first():
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compañía no encontrada.")
        
    # Validar Branch ID (si se proporciona)
    if new_branch_id is not None:
        # Usar el nuevo company_id si se especificó, sino usar el actual del usuario
        # ¡IMPORTANTE!: Si se está actualizando el company_id, usamos el nuevo ID para validar la sucursal.
        target_company_id = new_company_id if new_company_id is not None else db_user.company_id
        
        if target_company_id is None:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede asignar una sucursal si el usuario no tiene compañía asignada.")

        if not db.query(Branch).filter(Branch.id == new_branch_id, Branch.company_id == target_company_id).first():
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La sucursal no existe o no pertenece a la compañía objetivo.")
             
    # 4. Aplicar los cambios a la DB
    # Aseguramos que solo aplicamos los campos que se enviaron en `update_data`
    for key, value in update_data.items():
        if key != "password": # 'password' ya se manejó
            setattr(db_user, key, value)

    # Si se actualiza company_id, y no se envió branch_id, la branch_id anterior podría ser inválida.
    # Por seguridad, si el company_id se cambió, y la branch_id no se envió, la seteamos a NULL.
    if new_company_id is not None and new_branch_id is None:
        db_user.branch_id = None
            
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # 5. Mapear para la respuesta
    user_data = db_user.__dict__.copy()
    user_data.pop('password_hash', None)
    # Refrescar el nombre del rol en caso de que haya cambiado
    user_data["role_name"] = db_user.role.name
    
    return UserInDB.model_validate(user_data)


# ***************************************************************
# 4. Endpoint para Eliminar Usuario (DELETE /api/v1/users/{user_id})
# ***************************************************************
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Elimina un usuario por ID, respetando el RBAC."""
    
    # 1. Busca el usuario y verifica los permisos
    db_user = get_user_and_check_access(user_id, db, admin)
    
    # 2. Eliminar el usuario
    db.delete(db_user)
    db.commit()
    
    # No retorna contenido (204 NO CONTENT)
    return