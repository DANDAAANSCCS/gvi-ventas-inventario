from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user, require_role
from models import Product, User, UserRole
from schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(None, description="Busqueda por nombre"),
    category: str | None = None,
    only_active: bool = True,
    only_in_stock: bool = False,
):
    """Lista publica de productos con filtros basicos."""
    stmt = select(Product)
    if only_active:
        stmt = stmt.where(Product.active.is_(True))
    if only_in_stock:
        stmt = stmt.where(Product.stock > 0)
    if category:
        stmt = stmt.where(Product.category == category)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.description.ilike(like)))
    stmt = stmt.order_by(Product.name.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/categories", response_model=list[str])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product.category)
        .where(Product.active.is_(True), Product.category.is_not(None))
        .distinct()
    )
    return [c for c in result.scalars().all() if c]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return product


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Eliminacion logica (active=false)."""
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    product.active = False
    await db.commit()
