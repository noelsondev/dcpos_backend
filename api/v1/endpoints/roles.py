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
    """
    Lista todos los roles disponibles en la base de datos.
    Requiere autenticación.
    """
    
    # 1. Consultar todos los objetos Role en la base de datos
    roles_from_db = db.query(Role).all()
    
    # 2. Convertir la lista de objetos Role a la lista de esquemas RoleInDB
    # Esto es necesario para asegurar que el formato de salida cumpla con RoleList
    roles_in_db_format = [
        RoleInDB(id=str(r.id), name=r.name) for r in roles_from_db
    ]
    
    # 3. Devolver la respuesta en el formato RoleList: {"roles": [...]}
    return {"roles": roles_in_db_format}