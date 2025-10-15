from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db, Base, engine


# 1. Inicializar la aplicación FastAPI
app = FastAPI(
    title="DCPOS Backend API",
    version="v1",
    description="Backend para el sistema de punto de venta basado en FastAPI, PostgreSQL y Flutter."
)

# 2. Función para crear las tablas al iniciar la app (usaremos esto solo al principio)
# Base.metadata.create_all(bind=engine) creará todas las tablas definidas en Base
def create_tables():
    """Crea todas las tablas de la base de datos si no existen."""
    # ¡Importante! Asegúrate de que todos tus modelos (tablas) están importados
    # antes de llamar a create_all, de lo contrario no las conocerá.
    # Por ahora, solo tenemos database.py, pero luego importaremos los modelos.
    Base.metadata.create_all(bind=engine)

# Llamar a la función para crear las tablas (EJECUTAR UNA SOLA VEZ AL INICIO)
# Por ahora no hará nada porque no hemos definido modelos, pero es el lugar.
create_tables()

# 3. Endpoint de Prueba
@app.get("/")
def read_root(db: Session = Depends(get_db)):
    """Endpoint de bienvenida con prueba de conexión a la base de datos."""
    try:
        # Prueba simple de la conexión a DB
        db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "DCPOS API", "db_connection": "successful"}
    except Exception as e:
        return {"status": "error", "service": "DCPOS API", "db_connection": f"failed: {e}"}

# **Nota:** Más adelante, agregaremos aquí los 'routers' para cada módulo (auth, products, etc.).