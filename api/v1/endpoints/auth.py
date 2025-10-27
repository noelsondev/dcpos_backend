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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no encontrado o inactivo.")
        
        return user
    except HTTPException:
        raise

# ***************************************************************
# Dependencia para requerir GLOBAL_ADMIN
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
# 2. Endpoint de Login (Sin cambios)
# ***************************************************************
@router.post("/login", response_model=Token)
def login_for_access_token(user_in: UserLogin, db: Session = Depends(get_db)):
    """Autentica un usuario y devuelve un token JWT."""
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

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )

    role_name = user.role.name
    
    return {"access_token": access_token, "role": role_name}


# ***************************************************************
# 3. Endpoint de Refresh (Sin cambios)
# ***************************************************************
@router.post("/refresh", response_model=Token, tags=["Auth"])
def refresh_access_token(current_user: User = Depends(get_current_user)):
    """
    Refresca el token de acceso JWT del usuario autenticado.
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(current_user.id), expires_delta=access_token_expires
    )
    
    role_name = current_user.role.name
    
    return {"access_token": access_token, "role": role_name}


# ***************************************************************
# 4. Endpoint de Test (Protegido)
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