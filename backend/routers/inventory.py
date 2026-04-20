from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_role
from models import InventoryMovement, MovementType, Product, User, UserRole
from schemas import MovementCreate, MovementOut

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/movements", response_model=list[MovementOut])
async def list_movements(
    db: AsyncSession = Depends(get_db),
    product_id: UUID | None = None,
    limit: int = 200,
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    stmt = (
        select(InventoryMovement)
        .order_by(InventoryMovement.created_at.desc())
        .limit(limit)
    )
    if product_id:
        stmt = stmt.where(InventoryMovement.product_id == product_id)
    result = await db.execute(stmt)
    movs = result.scalars().all()

    # Nombres de producto en una sola consulta adicional
    prod_ids = {m.product_id for m in movs}
    prod_map: dict[UUID, str] = {}
    if prod_ids:
        r = await db.execute(select(Product).where(Product.id.in_(prod_ids)))
        prod_map = {p.id: p.name for p in r.scalars().all()}

    return [
        MovementOut(
            id=m.id,
            product_id=m.product_id,
            type=m.type,
            quantity=m.quantity,
            reason=m.reason,
            user_id=m.user_id,
            created_at=m.created_at,
            product_name=prod_map.get(m.product_id),
        )
        for m in movs
    ]


@router.post("/movements", response_model=MovementOut, status_code=status.HTTP_201_CREATED)
async def create_movement(
    payload: MovementCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    """Registra un movimiento manual y ajusta el stock de forma atomica."""
    result = await db.execute(
        select(Product).where(Product.id == payload.product_id).with_for_update()
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")

    if payload.type == MovementType.in_:
        product.stock += payload.quantity
    elif payload.type == MovementType.out:
        if product.stock < payload.quantity:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Stock insuficiente")
        product.stock -= payload.quantity
    else:  # adjustment: el campo quantity es el NUEVO stock absoluto
        product.stock = payload.quantity

    mov = InventoryMovement(
        product_id=product.id,
        type=payload.type,
        quantity=payload.quantity,
        reason=payload.reason,
        user_id=user.id,
    )
    db.add(mov)
    await db.commit()
    await db.refresh(mov)
    return MovementOut(
        id=mov.id,
        product_id=mov.product_id,
        type=mov.type,
        quantity=mov.quantity,
        reason=mov.reason,
        user_id=mov.user_id,
        created_at=mov.created_at,
        product_name=product.name,
    )
