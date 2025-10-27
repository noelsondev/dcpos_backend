# app/main.py
# type: ignore

from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db, Base, engine

# ***************************************************************
# 1. Importar todos los modelos para que SQLAlchemy los registre
# ***************************************************************
# Importar los modelos de Auth y Platform (Roles, Users, Companies, Branches)
import app.models.auth # Esto registra Role y User
import app.models.platform # Esto registra Company y Branch
import app.models.inventory # <-- NUEVO: Registra el modelo Product

# ***************************************************************
# 2. Importar los Routers de API
# ***************************************************************
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import platform 
from app.api.v1.endpoints import users
from app.api.v1.endpoints import products # <-- NUEVO: Importar el router de productos

# Inicializar la aplicación FastAPI
app = FastAPI(
    title="DCPOS Backend API",
    version="v1",
    description="Backend para el sistema de punto de venta basado en FastAPI, PostgreSQL y Flutter."
)

# Función para crear las tablas al iniciar la app
def create_tables():
    """Crea todas las tablas de la base de datos si no existen."""
    # Base.metadata.create_all ahora conoce Role, User, Company, Branch, y Product
    Base.metadata.create_all(bind=engine)

# Llamar a la función para crear las tablas (EJECUTAR UNA SOLA VEZ AL INICIO)
create_tables() 

# ***************************************************************
# 3. Incluir los Routers
# ***************************************************************

# Router de Autenticación
app.include_router(auth.router, tags=["Auth"], prefix="/api/v1/auth")

# Routers de Plataforma
app.include_router(platform.router, tags=["Platform"], prefix="/api/v1/platform") 

# Routers de Usuarios (Administración de usuarios)
app.include_router(users.router, tags=["Users"], prefix="/api/v1/users")

# Routers de Productos <-- NUEVO
app.include_router(products.router, tags=["Products"], prefix="/api/v1/products")