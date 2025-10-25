# app/api/v1/endpoints/auth.py
 # type: ignore

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import UserCreate, UserLogin, Token, UserInDB
from app.models.auth import User, Role
from app.core.security import get_password_hash, verify_password, create_access_token, reusable_oauth2, decode_token, ACCESS_TOKEN_EXPIRE_MINUTES
from uuid import uuid4
from datetime import timedelta
from app.schemas.auth import UserInDB


router = APIRouter()

# ... (Dependencias get_current_user y get_global_admin sin cambios)
# ***************************************************************
# Dependencia para obtener el usuario autenticado (RBAC básico)
# ***************************************************************
def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """Decodifica el token, obtiene el ID del usuario y lo busca en la DB."""
    try:
        token_data = decode_token(token)
        user_id = token_data.sub
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no contiene ID de usuario.")
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado o inactivo.")
        
        return user
    except HTTPException:
        # Re-lanza las HTTPException de decode_token
        raise

# ***************************************************************
# Dependencia para requerir GLOBAL_ADMIN
# ***************************************************************
def get_global_admin(current_user: User = Depends(get_current_user)):
    """Verifica si el usuario actual tiene el rol de global_admin."""
    # Nota: El rol 'global_admin' tiene ID 1 si seguiste el initial_data.py
    # Una solución más robusta sería consultar el nombre del rol.
    
    # Solución robusta: Consultar el nombre del rol a través de la relación
    if current_user.role.name != "global_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requiere rol 'global_admin'."
        )
    return current_user

# ... (Endpoint register_user sin cambios)

# ***************************************************************
# 2. Endpoint de Login
# ***************************************************************
@router.post("/login", response_model=Token)
def login_for_access_token(user_in: UserLogin, db: Session = Depends(get_db)):
    """Autentica un usuario y devuelve un token JWT."""
    # 1. Buscar usuario por nombre de usuario
    user = db.query(User).filter(User.username == user_in.username).first()
    
    # 2. Verificar credenciales
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Asegurarse de que el usuario esté activo
    if not user.is_active:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario está inactiva.",
        )

    # 4. Generar el token (Subject 'sub' es el ID del usuario)
    # Se usa la variable ACCESS_TOKEN_EXPIRE_MINUTES del archivo security
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )

    # 5. Obtener el nombre del rol para la respuesta
    # La relación 'role' debería estar cargada debido al lazy='joined' en el modelo User
    role_name = user.role.name
    
    return {"access_token": access_token, "role": role_name}


# ***************************************************************
# 3. Endpoint de Refresh (NUEVO)
# ***************************************************************
@router.post("/refresh", response_model=Token, tags=["Auth"])
def refresh_access_token(current_user: User = Depends(get_current_user)):
    """
    Refresca el token de acceso JWT del usuario autenticado.
    El token actual se usa para autenticar, y se emite uno nuevo.
    """
    # 1. El get_current_user ya verificó el token y la actividad del usuario.
    
    # 2. Generar un nuevo token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(current_user.id), expires_delta=access_token_expires
    )
    
    # 3. Obtener el nombre del rol (ya cargado)
    role_name = current_user.role.name
    
    return {"access_token": access_token, "role": role_name}


# ***************************************************************
# 4. Endpoint de Test (Protegido)
# ***************************************************************
@router.get("/me", response_model=UserInDB)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Obtiene la información del usuario autenticado."""
    
    # 1. Convertir el objeto SQLAlchemy a un diccionario.
    # Usamos .__dict__.copy() para evitar modificar el objeto de SQLAlchemy.
    user_data = current_user.__dict__.copy()
    
    # 2. Añadir el campo calculado 'role_name'
    user_data["role_name"] = current_user.role.name
    
    # 3. Eliminar la relación 'role' antes de la validación
    user_data.pop('role', None) 
    
    # 4. Validar el diccionario contra el esquema
    return UserInDB.model_validate(user_data)