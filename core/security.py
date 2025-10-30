# app/core/security.py
# type: ignore
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
# Revert to ABSOLUTE import
from app.schemas.auth import TokenPayload 
# ... (rest of the file)

# ***************************************************************
# 1. Configuración de Seguridad
# ***************************************************************

# Contexto para hashing de contraseñas (usa pbkdf2_sha256 por defecto)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
# Clave secreta para JWT (¡Cambia esto en producción y cárgalo de .env!)
SECRET_KEY = "SUPER_SECRETA_Y_LARGA_CLAVE_QUE_DEBERIA_ESTAR_EN_ENV"
ALGORITHM = "HS256"

# Tiempo de expiración del token (por ejemplo, 10 minutos)
ACCESS_TOKEN_EXPIRE_MINUTES = 10 
# 🚨 NUEVO: Tiempo de expiración del refresh token (por ejemplo, 7 días)
REFRESH_TOKEN_EXPIRE_DAYS = 7 

# Esquema de autenticación para FastAPI (para endpoints protegidos)
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login" # Endpoint donde se obtiene el token
)

# ***************************************************************
# 2. Funciones de Hashing de Contraseñas
# ***************************************************************

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con el hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña en texto plano."""
    return pwd_context.hash(password)

# ***************************************************************
# 3. Funciones de Creación y Verificación de JWT
# ***************************************************************

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """Crea un nuevo token de acceso JWT."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Si no se especifica, usa el valor por defecto
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Datos que se incluirán en el token (payload)
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # Genera el token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 🚨 NUEVO: Función para crear Refresh Token
def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """Crea un nuevo token de refresco JWT."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Usa el valor por defecto (7 días) si no se especifica
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Datos que se incluirán en el token (payload)
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # Genera el token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenPayload:
    """Decodifica y valida un token JWT. Lanza HTTPException si falla."""
    try:
        # Decodificar el token con la clave secreta y algoritmo
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Validar el schema de la carga útil (payload)
        token_data = TokenPayload(**payload)
        
        return token_data
    
    except (JWTError, ValidationError, TypeError) as e:
        # Si la decodificación o validación falla, se lanza una excepción 
        # para que FastAPI devuelva un error 401.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o token expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e