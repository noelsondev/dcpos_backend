# app/api/v1/endpoints/auth.py
# type: ignore

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import UserCreate, UserLogin, Token, UserInDB
from app.models.auth import User, Role 
# 🚨 Importaciones de seguridad actualizadas
from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    create_refresh_token, # 🚨 Nueva función
    reusable_oauth2, 
    decode_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS # 🚨 Nueva constante
)
from uuid import uuid4
from datetime import timedelta
from app.schemas.auth import UserInDB


router = APIRouter()

# ***************************************************************
# Dependencia para obtener el usuario autenticado (RBAC básico)
# ***************************************************************
def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """Decodifica el token, obtiene el ID del usuario y lo busca en la DB. (Usa ACCESS TOKEN)"""
    try:
        token_data = decode_token(token)
        user_id = token_data.sub
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no contiene ID de usuario.")
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no encontrado o inactivo.")
        
        return user
    except HTTPException:
        raise

# 🚨 NUEVA DEPENDENCIA para validar el Refresh Token
def get_user_from_refresh_token(token: str, db: Session = Depends(get_db)) -> User:
    """Decodifica el token de refresco y busca al usuario. Lanza 401 si falla."""
    try:
        # Usamos decode_token para verificar la expiración y firma
        token_data = decode_token(token)
        user_id = token_data.sub
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no contiene ID de usuario.")
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no encontrado o inactivo.")
        
        return user
    except HTTPException:
        # Re-lanza la excepción (ej: token expirado, inválido)
        raise


# ***************************************************************
# Dependencia para requerir GLOBAL_ADMIN (sin cambios)
# ***************************************************************
def get_global_admin(current_user: User = Depends(get_current_user)):
    """Verifica si el usuario actual tiene el rol de global_admin."""
    if current_user.role.name != "global_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requiere rol 'global_admin'."
        )
    return current_user

# ***************************************************************
# 2. Endpoint de Login (ACTUALIZADO para devolver refresh_token)
# ***************************************************************
@router.post("/login", response_model=Token, tags=["Auth"])
def login_for_access_token(user_in: UserLogin, db: Session = Depends(get_db)):
    """Autentica un usuario y devuelve un token JWT y un Refresh Token."""
    user = db.query(User).filter(User.username == user_in.username).first()
    
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
         raise HTTPException(
             status_code=status.HTTP_403_FORBIDDEN,
             detail="La cuenta de usuario está inactiva.",
          )

    # 1. Crear ACCESS TOKEN 
    access_token_expires = timedelta(seconds=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )

    # 2. Crear REFRESH TOKEN 🚨 NUEVO
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        subject=str(user.id), expires_delta=refresh_token_expires
    )

    role_name = user.role.name
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token, # 🚨 Devolver Refresh Token
        "token_type": "bearer",
        "role": role_name
    }


# ***************************************************************
# 3. Endpoint de Refresh (FIX de Seguridad con Token Rotation)
# ***************************************************************
@router.post("/refresh", response_model=Token, tags=["Auth"])
def refresh_access_token(
    # 🚨 Se espera el refresh_token en el header 'Authorization: Bearer <token>'
    refresh_token: str = Depends(reusable_oauth2), 
    db: Session = Depends(get_db)
):
    """
    Refresca el token de acceso JWT usando un Refresh Token. 
    Implementa Token Rotation: devuelve un nuevo access_token y un nuevo refresh_token.
    """
    
    # 1. Validar el refresh token y obtener el usuario.
    current_user = get_user_from_refresh_token(refresh_token, db)
    
    # 2. Crear nuevo ACCESS TOKEN (Corta duración)
    access_token_expires = timedelta(seconds=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        subject=str(current_user.id), expires_delta=access_token_expires
    )
    
    # 3. CREAR NUEVO REFRESH TOKEN (Token Rotation) 🚨 NUEVO
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = create_refresh_token(
        subject=str(current_user.id), expires_delta=refresh_token_expires
    )
    
    role_name = current_user.role.name
    
    return {
        "access_token": new_access_token, 
        "refresh_token": new_refresh_token, # 🚨 Devolver un nuevo Refresh Token
        "token_type": "bearer",
        "role": role_name
    }


# ***************************************************************
# 4. Endpoint de Test (Protegido) (sin cambios)
# ***************************************************************
@router.get("/me", response_model=UserInDB)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Obtiene la información del usuario autenticado."""
    
    user_data = current_user.__dict__.copy()
    
    # 🛑 ESTO ES CRUCIAL: Asignar el datetime al diccionario. 
    # El esquema UserInDB ahora espera un datetime.
    user_data['created_at'] = current_user.created_at 
    
    user_data["role_name"] = current_user.role.name
    
    # Limpieza de campos internos de SQLAlchemy y sensibles
    user_data.pop('role', None) 
    user_data.pop('password_hash', None) 
    user_data.pop('_sa_instance_state', None) 
    
    # 4. Validar el diccionario.
    # Pydantic valida que created_at es datetime, luego el serializador lo convierte a string para la salida.
    return UserInDB.model_validate(user_data)