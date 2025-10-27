# app/api/v1/endpoints/products.py
# type: ignore

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.inventory import Product
from app.models.auth import User
from app.schemas.inventory import ProductCreate, ProductUpdate, ProductInDB
# Importar la dependencia de autenticación y get_admin_user
from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.endpoints.users import get_admin_user # Reutilizamos la dependencia de admin


router = APIRouter()

# ***************************************************************
# DEPENDENCIAS ESPECÍFICAS PARA PRODUCTOS
# ***************************************************************

def get_product_management_access(current_user: User = Depends(get_admin_user)):
    """
    Dependencia que asegura que el usuario puede crear/modificar productos.
    (Solo Global Admin o Company Admin)
    """
    return current_user

def get_product_and_check_access(
    product_id: UUID, 
    db: Session, 
    admin: User
) -> Product:
    """Busca un producto por ID y verifica que el admin tenga permiso."""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")
        
    # Restricción de Company Admin: Solo puede acceder a productos en su compañía.
    if admin.role.name == "company_admin":
        if product.company_id != admin.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acceso denegado. El producto no pertenece a tu compañía."
            )
            
    return product


# ***************************************************************
# 1. Endpoint para Crear Producto (POST /)
# ***************************************************************
@router.post("/", response_model=ProductInDB, status_code=status.HTTP_201_CREATED, tags=["Products"])
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    # Solo administradores pueden crear productos
    admin: User = Depends(get_product_management_access) 
):
    """
    Crea un nuevo producto.
    Un Company Admin solo puede crear productos en su propia compañía.
    """
    
    # 1. Restricción de Company Admin: Forzar el company_id
    if admin.role.name == "company_admin":
        if product_in.company_id != admin.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Un Company Admin solo puede crear productos en su propia compañía."
            )
            
    # 2. Validar unicidad del SKU dentro de la compañía
    if db.query(Product).filter(
        Product.sku == product_in.sku, 
        Product.company_id == product_in.company_id
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Ya existe un producto con este SKU en esta compañía."
        )

    # 3. Crear el objeto Product
    db_product = Product(**product_in.model_dump())

    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return db_product

# ***************************************************************
# 2. Endpoint para Listar Productos (GET /)
# ***************************************************************
@router.get("/", response_model=List[ProductInDB], tags=["Products"])
def read_products(
    db: Session = Depends(get_db),
    # Permitimos a cualquier usuario autenticado ver productos
    current_user: User = Depends(get_current_user), 
    limit: int = Query(100, gt=0),
    skip: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Buscar por nombre o SKU."),
    company_id: Optional[UUID] = Query(None, description="Filtrar por Company ID (solo Global Admin).")
):
    """
    Lista productos con filtros.
    - Global Admin puede filtrar por company_id o listar todos.
    - Company Admin/Cashier solo ve productos de su compañía.
    """
    query = db.query(Product)

    # 1. Aplicar restricción de compañía basada en el rol
    if current_user.role.name == "global_admin":
        # Global Admin puede filtrar o ver todo el sistema
        if company_id:
            query = query.filter(Product.company_id == company_id)
    else:
        # Company Admin, Cashier, etc., solo ven productos de su compañía.
        query = query.filter(Product.company_id == current_user.company_id)
        # Ignoramos cualquier company_id que intente pasar el usuario
        
    # 2. Aplicar búsqueda por nombre o SKU
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_pattern)) | 
            (Product.sku.ilike(search_pattern))
        )

    # 3. Aplicar paginación
    products = query.offset(skip).limit(limit).all()
    
    return products


# ***************************************************************
# 3. Endpoint para Leer Producto por ID (GET /{product_id})
# ***************************************************************
@router.get("/{product_id}", response_model=ProductInDB, tags=["Products"])
def read_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    # Permitimos a cualquier usuario autenticado ver productos
    current_user: User = Depends(get_current_user) 
):
    """Obtiene un producto por ID, respetando el RBAC (solo ver los de su compañía)."""
    
    db_product = db.query(Product).filter(Product.id == product_id).first()
    
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")

    # Restricción: Si no es Global Admin, debe pertenecer a su compañía
    if current_user.role.name != "global_admin":
        if db_product.company_id != current_user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acceso denegado. Este producto no pertenece a tu compañía."
            )
            
    return db_product


# ***************************************************************
# 4. Endpoint para Actualizar Producto (PATCH /{product_id})
# ***************************************************************
@router.patch("/{product_id}", response_model=ProductInDB, tags=["Products"])
def update_product(
    product_id: UUID,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_product_management_access)
):
    """Actualiza campos de un producto, restringido a Global/Company Admin."""
    
    # 1. Busca y comprueba permisos
    db_product = get_product_and_check_access(product_id, db, admin)
    
    update_data = product_in.model_dump(exclude_unset=True)

    # 2. Validar unicidad del SKU si se está actualizando
    if "sku" in update_data and update_data["sku"] != db_product.sku:
        if db.query(Product).filter(
            Product.sku == update_data["sku"], 
            Product.company_id == db_product.company_id # Mismo company_id
        ).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Ya existe otro producto con este SKU en esta compañía."
            )

    # 3. Aplicar los cambios
    for key, value in update_data.items():
        # Validar que los valores Decimal se mantengan como Decimal
        if key in ['price', 'cost'] and value is not None:
             setattr(db_product, key, value)
        elif value is not None:
             setattr(db_product, key, value)

    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return db_product

# ***************************************************************
# 5. Endpoint para Eliminar Producto (DELETE /{product_id})
# ***************************************************************
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Products"])
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_product_management_access)
):
    """Elimina un producto por ID, restringido a Global/Company Admin."""
    
    # 1. Busca el producto y verifica los permisos
    db_product = get_product_and_check_access(product_id, db, admin)
    
    # 2. Eliminar el producto
    db.delete(db_product)
    db.commit()
    
    return