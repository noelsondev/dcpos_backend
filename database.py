# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import sys

# *****************************************************************
# 1. Ajuste CLAVE: Especificar la ruta del archivo .env
# *****************************************************************
# Subir un nivel para encontrar el .env en la carpeta dcpos_backend/
load_dotenv(dotenv_path='../.env') 

# Obtener la URL de conexión (el resto es igual)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    print("FATAL ERROR: La variable de entorno 'DATABASE_URL' no se encontró.")
    sys.exit(1)

engine = create_engine(
    DATABASE_URL 
)
# 2. Crear la Clase SessionLocal
# Esta es la clase que se usará para cada solicitud (request) a la API.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Crear la Clase Base
# Esta será la clase base de la que heredarán todos nuestros modelos/tablas.
Base = declarative_base()

# Función de dependencia (Dependency Injection) para obtener una sesión de DB
def get_db():
    """Provee una sesión de base de datos a un endpoint de FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()