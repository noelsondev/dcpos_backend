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

# ***************************************************************
# 2. Importar los Routers de API
# ***************************************************************
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import platform 

# Inicializar la aplicación FastAPI
app = FastAPI(
    title="DCPOS Backend API",
    version="v1",
    description="Backend para el sistema de punto de venta basado en FastAPI, PostgreSQL y Flutter."
)

# Función para crear las tablas al iniciar la app
def create_tables():
    """Crea todas las tablas de la base de datos si no existen."""
    # Base.metadata.create_all ahora conoce Role, User, Company, y Branch
    Base.metadata.create_all(bind=engine)

# Llamar a la función para crear las tablas (EJECUTAR UNA SOLA VEZ AL INICIO)
create_tables() 

# ***************************************************************
# 3. Incluir los Routers
# ***************************************************************
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Auth & Users"]
)

app.include_router(
    platform.router,
    prefix="/api/v1/platform",
    tags=["Platform Management"]
)

# 4. Endpoint de Prueba (Existente)
@app.get("/")
def read_root(db: Session = Depends(get_db)):
    """Endpoint de bienvenida con prueba de conexión a la base de datos."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "DCPOS API", "db_connection": "successful"}
    except Exception as e:
        return {"status": "error", "service": "DCPOS API", "db_connection": f"failed: {e}"}