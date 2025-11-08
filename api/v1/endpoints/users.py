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
# ... (Funciones get_admin_user y get_user_and_check_access sin cambios)
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
    current_user: User,
    is_update_or_delete: bool = False # Nuevo parámetro para diferenciar lectura de modificación/eliminación
) -> User:
    """
    Busca un usuario por ID y verifica que el usuario actual tenga permiso para acceder a él.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    
    # 1. Regla Universal: Permiso de Auto-acceso (Lectura/Modificación)
    if user.id == current_user.id:
        # Se permite auto-modificación/lectura para todos.
        return user 

    # A partir de aquí, el acceso a OTROS usuarios solo está permitido para los administradores.
    if current_user.role.name not in ["global_admin", "company_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso denegado. No tienes permisos para acceder a otros usuarios."
        )

    # El usuario actual es Global Admin o Company Admin.
    admin_role = current_user.role.name
    
    # 2. Restricción de Company Admin
    if admin_role == "company_admin":
        
        # a. Solo puede acceder a usuarios en su compañía.
        if user.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acceso denegado. El usuario no pertenece a tu compañía."
            )
        
        # b. Restricción de jerarquía (Global Admin y Company Admin)
        target_role_name = user.role.name
        
        # Si es una operación de modificación o eliminación, no puede afectar a administradores.
        if is_update_or_delete and target_role_name in ["global_admin", "company_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Acceso denegado. No puedes modificar/eliminar un usuario con rol '{target_role_name}'."
            )

    # 3. Global Admin
    # Si el usuario actual es Global Admin, y el objetivo no era él mismo, el acceso está permitido.
    
    return user
# ... (El resto de endpoints de LISTAR, BUSCAR y ACTUALIZAR usuarios sin cambios)
# ***************************************************************
# 1. Endpoint para Listar Usuarios (GET /api/v1/users/)
# ***************************************************************
@router.get("/", response_model=List[UserInDB], tags=["Users"])
def read_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
    company_id: Optional[UUID] = Query(None, description="Filtrar por ID de compañía (Solo Global Admin)"),
    branch_id: Optional[UUID] = Query(None, description="Filtrar por ID de sucursal")
):
    """
    Obtiene una lista de usuarios, con restricciones de acceso por rol y filtros.
    """
    query = db.query(User)

    if admin.role.name == "company_admin":
        # Company Admin solo puede ver usuarios en su compañía.
        query = query.filter(User.company_id == admin.company_id)

        # Si intenta filtrar por otra compañía, denegar.
        if company_id is not None and company_id != admin.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acceso denegado. Company Admin solo puede listar usuarios de su compañía."
            )
        
        # Aplicar filtro de sucursal dentro de su compañía
        if branch_id:
             query = query.filter(User.branch_id == branch_id)

    elif admin.role.name == "global_admin":
        # Global Admin puede aplicar filtros de compañía y sucursal.
        if company_id:
            query = query.filter(User.company_id == company_id)
        
        if branch_id:
            query = query.filter(User.branch_id == branch_id)

    users = query.all()
    
    # Mapear la lista de objetos User a List[UserInDB]
    response_list = []
    for user in users:
        user_data = user.__dict__.copy()
        user_data.pop('password_hash', None)
        # Asegurarse de que el campo 'created_at' se incluye si es necesario para el schema
        if hasattr(user, 'created_at'):
            user_data['created_at'] = user.created_at 
        
        user_data["role_name"] = user.role.name
        # Usamos model_validate para garantizar la correcta serialización a Pydantic
        response_list.append(UserInDB.model_validate(user_data))
        
    return response_list


# ***************************************************************
# 2. Endpoint para Crear Usuario (POST /api/v1/users/)
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
        # Devolver 400 Bad Request es semánticamente correcto para un dato inválido.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya existe.")
        
    # 2. Validar que el rol existe y obtener el objeto Role
    role_to_assign = db.query(Role).filter(Role.id == user_in.role_id).first()
    if not role_to_assign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")

    # 3. Aplicar las Reglas de RBAC
    if admin.role.name == "company_admin":
        
        # Un Company Admin SOLO puede crear roles de menor ID/privilegio
        if role_to_assign.id <= admin.role.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Un {admin.role.name} no puede crear un usuario con el rol {role_to_assign.name} o superior."
            )
        
        # 🚀 CORRECCIÓN CLAVE: Aseguramos que el company_id se use correctamente.
        admin_company_id = admin.company_id

        # Si el admin no tiene compañía (Debería ser un 500/error de setup, pero lo manejamos)
        if admin_company_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Error: El Company Admin actual no tiene una compañía asignada."
            )

        # Si el usuario NO especificó compañía, forzamos la compañía del administrador.
        if user_in.company_id is None:
            user_in.company_id = admin_company_id
        
        # Si el usuario ESPECIFICÓ una compañía, debe ser la misma que la del administrador.
        elif user_in.company_id != admin_company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Un Company Admin solo puede crear usuarios dentro de su propia compañía."
            )
            
        # Si se especificó una branch, validar que pertenece a la compañía
        if user_in.branch_id:
            # Usamos user_in.company_id que ya fue forzado/validado
            if not db.query(Branch).filter(Branch.id == user_in.branch_id, Branch.company_id == user_in.company_id).first():
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
# 3. Endpoint para Buscar Usuario por ID (GET /api/v1/users/{user_id})
# ***************************************************************
@router.get("/{user_id}", response_model=UserInDB, tags=["Users"])
def read_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    # Usamos get_current_user para que un cashier pueda leer su propio perfil.
    current_user: User = Depends(get_current_user) 
):
    """Obtiene la información de un usuario por su ID, respetando el RBAC."""
    
    # La función de acceso chequea si el usuario actual puede leer al usuario objetivo.
    db_user = get_user_and_check_access(user_id, db, current_user, is_update_or_delete=False)
    
    # Mapear para la respuesta
    user_data = db_user.__dict__.copy()
    user_data.pop('password_hash', None)
    user_data["role_name"] = db_user.role.name
    
    return UserInDB.model_validate(user_data)


# ***************************************************************
# 4. Endpoint para Actualizar Usuario (PATCH /api/v1/users/{user_id})
# ***************************************************************
@router.patch("/{user_id}", response_model=UserInDB, tags=["Users"])
def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    """Actualiza campos de un usuario, con restricciones de acceso/rol."""
    
    # 1. Verifica permisos y acceso
    db_user = get_user_and_check_access(user_id, db, current_user, is_update_or_delete=True)
    
    update_data = user_in.model_dump(exclude_unset=True)

    # Identificadores de ayuda
    is_self_update = str(current_user.id) == str(user_id)
    is_global_admin = current_user.role.name == "global_admin"

    # 2. VALIDAR CAMBIOS SENSIBLES (ROLE_ID y COMPANY_ID)

    # 2a. Validar el cambio de Role ID
    if "role_id" in update_data:
        role_id_to_assign = update_data["role_id"]
        role = db.query(Role).filter(Role.id == role_id_to_assign).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado.")
            
        # RESTRICCIÓN 1: Prohibir a Company Admin cambiar el rol de OTRO usuario.
        if not is_self_update and not is_global_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un Global Admin puede cambiar el rol de otro usuario.")
            
        # RESTRICCIÓN 2: Company Admin no puede asignarse un rol igual o superior, incluso a sí mismo.
        if current_user.role.name == "company_admin" and role_id_to_assign <= current_user.role.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para asignar este tipo de rol o superior.")


    # 2b. Validar el cambio de Company ID
    new_company_id = update_data.get("company_id")
    
    if new_company_id is not None:
        # RESTRICCIÓN 3: SOLO Global Admin puede tocar el campo 'company_id'.
        if not is_global_admin:
            # Si se envía el campo 'company_id' en el payload, pero no eres Global Admin, denegar.
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un Global Admin puede reasignar el ID de Compañía.")
        
        # Si es Global Admin, validar que la compañía exista
        if not db.query(Company).filter(Company.id == new_company_id).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compañía no encontrada.")
        
    # 3. Manejar el cambio de Contraseña
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        update_data["password_hash"] = hashed_password
        update_data.pop("password") 
    
    # 4. Validar unicidad de Username
    if "username" in update_data and update_data["username"] != db_user.username:
        if db.query(User).filter(User.username == update_data["username"]).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya existe.")
            
    # 5. Validar Branch ID
    new_branch_id = update_data.get("branch_id")
    
    if new_branch_id is not None:
        target_company_id = new_company_id if new_company_id is not None else db_user.company_id
        
        if target_company_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede asignar una sucursal si el usuario no tiene compañía asignada.")

        if not db.query(Branch).filter(Branch.id == new_branch_id, Branch.company_id == target_company_id).first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La sucursal no existe o no pertenece a la compañía objetivo.")
            
    # 6. Aplicar los cambios a la DB
    for key, value in update_data.items():
        if key not in ["password"]:
            setattr(db_user, key, value)

    # Si se actualiza company_id, y no se envió branch_id, la branch_id anterior podría ser inválida.
    if new_company_id is not None and new_branch_id is None:
        db_user.branch_id = None
            
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # 7. Mapear para la respuesta
    user_data = db_user.__dict__.copy()
    user_data.pop('password_hash', None)
    user_data["role_name"] = db_user.role.name
    
    return UserInDB.model_validate(user_data)


# ***************************************************************
# 5. Endpoint para Eliminar Usuario (DELETE /api/v1/users/{user_id})
# ***************************************************************
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Users"])
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """Elimina un usuario por ID, respetando el RBAC."""
    
    # 1. Busca el usuario y verifica los permisos
    # Usamos is_update_or_delete=True para aplicar las restricciones de jerarquía.
    db_user = get_user_and_check_access(user_id, db, admin, is_update_or_delete=True)
    
    # 2. No permitir auto-eliminación
    if db_user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No puedes eliminar tu propia cuenta de administrador."
        )

    # 3. Eliminar el usuario
    db.delete(db_user)
    db.commit()
    
    return