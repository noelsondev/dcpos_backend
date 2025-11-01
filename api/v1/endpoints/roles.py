# app/api/v1/endpoints/roles.py
# type: ignore

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import RoleList, RoleInDB
from app.models.auth import Role
# 🚨 Importamos la dependencia necesaria para la autenticación
from app.api.v1.endpoints.auth import get_current_user
from app.models.auth import User # Importamos User para la anotación de tipo

router = APIRouter()


# ***************************************************************
# 1. Endpoint para listar todos los Roles (ACCESO AUTENTICADO)
# ***************************************************************

@router.get("/", response_model=RoleList, tags=["Roles"])
def get_all_roles(
    _: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Temporalmente, devuelve datos dummy para saltar la DB."""
    # ⚠️ SI ESTO FUNCIONA, EL PROBLEMA ES DB/SQLACHEMY.
    
    # Datos dummy: Usamos el UUID de ejemplo en el servidor
    dummy_role = RoleInDB(id="a1b2c3d4-e5f6-7890-1234-567890abcdef", name="Admin Temporal")
    
    return {"roles": [dummy_role]} # Debería ser un diccionario