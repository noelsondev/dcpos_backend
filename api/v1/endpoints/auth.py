# app/api/v1/endpoints/auth.py
 # type: ignore

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import UserCreate, UserLogin, Token, UserInDB
from app.models.auth import User, Role
from app.core.security import get_password_hash, verify_password, create_access_token, reusable_oauth2, decode_token
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado o inactivo.")
        
        return user
    except HTTPException:
        # Re-lanza las HTTPException de decode_token
        raise

# ***************************************************************
# Dependencia de Permisos: Company Admin o Global Admin
# ***************************************************************
def get_admin_user(current_user: User = Depends(get_current_user)):
    """Requiere que el usuario sea global_admin o company_admin."""
    if current_user.role.name not in ["global_admin", "company_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado. Se requiere rol 'admin'."
        )
    return current_user

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

# ***************************************************************
# 1. Endpoint de Registro (Solo para desarrollo/admin inicial)
# ***************************************************************
@router.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo usuario. Debería ser restringido a solo 'global_admin'
    o 'company_admin' en producción.
    """
    # 1. Validar unicidad del nombre de usuario
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado."
        )

    # 2. Validar que el Role ID existe
    role = db.query(Role).filter(Role.id == user_in.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El Role con ID {user_in.role_id} no existe."
        )

    # 3. Crear el hash de la contraseña
    hashed_password = get_password_hash(user_in.password)

    # 4. Crear el objeto de la DB
    db_user = User(
        id=uuid4(),
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
    return db_user

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
    access_token_expires = timedelta(minutes=60 )#ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )

    # 5. Obtener el nombre del rol para la respuesta
    role_name = db.query(Role.name).filter(Role.id == user.role_id).scalar()
    
    return {"access_token": access_token, "role": role_name}


# ***************************************************************
# 3. Endpoint de Test (Protegido)
# ***************************************************************
@router.get("/me", response_model=UserInDB)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Obtiene la información del usuario autenticado."""
    
    # 1. Convertir el objeto SQLAlchemy a un diccionario.
    # Usamos .__dict__.copy() para evitar modificar el objeto de SQLAlchemy.
    user_data = current_user.__dict__.copy()
    
    # 2. Añadir el campo calculado 'role_name'
    user_data["role_name"] = current_user.role.name
    
    # 3. Validar el diccionario contra el esquema
    # (Pydantic sabe cómo manejar los campos extra y omite la relación 'role')
    return UserInDB.model_validate(user_data)

