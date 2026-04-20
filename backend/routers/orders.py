from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import get_current_user, require_role
from models import (
    Client,
    InventoryMovement,
    MovementType,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    User,
    UserRole,
)
from schemas import OrderCreate, OrderItemOut, OrderOut, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


def _serialize(order: Order, include_client_name: bool = False) -> OrderOut:
    items_out = [
        OrderItemOut(
            id=it.id,
            product_id=it.product_id,
            quantity=it.quantity,
            unit_price=it.unit_price,
            product_name=it.product.name if it.product else None,
        )
        for it in order.items
    ]
    return OrderOut(
        id=order.id,
        client_id=order.client_id,
        total=order.total,
        status=order.status,
        payment_method=order.payment_method,
        notes=order.notes,
        created_at=order.created_at,
        items=items_out,
        client_name=(order.client.name if include_client_name and order.client else None),
    )


async def _get_client_for_user(db: AsyncSession, user: User) -> Client:
    result = await db.execute(select(Client).where(Client.user_id == user.id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Usuario sin perfil de cliente")
    return client


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Crea un pedido en UNA sola transaccion:
    - valida stock,
    - inserta orders + order_items,
    - decrementa stock en products,
    - registra inventory_movements (type=out).
    Si algo falla, rollback completo.
    """
    client = await _get_client_for_user(db, user)

    # Lock de productos (FOR UPDATE) para evitar races en stock
    product_ids = [item.product_id for item in payload.items]
    if len(set(product_ids)) != len(product_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Productos duplicados en el pedido")

    result = await db.execute(
        select(Product).where(Product.id.in_(product_ids)).with_for_update()
    )
    products_map = {p.id: p for p in result.scalars().all()}

    if len(products_map) != len(product_ids):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Algún producto no existe")

    # Validar stock y disponibilidad
    for item in payload.items:
        prod = products_map[item.product_id]
        if not prod.active:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Producto '{prod.name}' no está activo"
            )
        if prod.stock < item.quantity:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Stock insuficiente para '{prod.name}' (disponible: {prod.stock})",
            )

    # Calcular total con precio del momento
    total = Decimal("0")
    for item in payload.items:
        prod = products_map[item.product_id]
        total += prod.price * item.quantity

    order = Order(
        client_id=client.id,
        total=total,
        status=OrderStatus.pending,
        payment_method=payload.payment_method,
        notes=payload.notes,
    )
    db.add(order)
    await db.flush()

    for item in payload.items:
        prod = products_map[item.product_id]
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=prod.id,
                quantity=item.quantity,
                unit_price=prod.price,
            )
        )
        prod.stock -= item.quantity
        db.add(
            InventoryMovement(
                product_id=prod.id,
                type=MovementType.out,
                quantity=item.quantity,
                reason=f"Pedido {order.id}",
                user_id=user.id,
            )
        )

    await db.commit()

    # Recargar con items+product
    result = await db.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    )
    order = result.scalar_one()
    return _serialize(order)


@router.get("/me", response_model=list[OrderOut])
async def list_my_orders(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Historial del cliente autenticado."""
    client = await _get_client_for_user(db, user)
    result = await db.execute(
        select(Order)
        .where(Order.client_id == client.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.created_at.desc())
    )
    return [_serialize(o) for o in result.scalars().all()]


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.client),
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    # Clientes solo ven sus propios pedidos
    if user.role == UserRole.client:
        client = await _get_client_for_user(db, user)
        if order.client_id != client.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso a este pedido")

    return _serialize(order, include_client_name=True)


@router.get("", response_model=list[OrderOut])
async def list_all_orders(
    db: AsyncSession = Depends(get_db),
    status_filter: OrderStatus | None = None,
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    """Listado para admin/staff."""
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.client),
        )
        .order_by(Order.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    result = await db.execute(stmt)
    return [_serialize(o, include_client_name=True) for o in result.scalars().all()]


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Cancela un pedido pending y REPONE el stock atomicamente.
    Cliente solo puede cancelar los suyos.
    """
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    if user.role == UserRole.client:
        client = await _get_client_for_user(db, user)
        if order.client_id != client.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso a este pedido")

    if order.status != OrderStatus.pending:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Solo se pueden cancelar pedidos pendientes"
        )

    # Reponer stock + registrar movement
    for item in order.items:
        result = await db.execute(
            select(Product).where(Product.id == item.product_id).with_for_update()
        )
        prod = result.scalar_one()
        prod.stock += item.quantity
        db.add(
            InventoryMovement(
                product_id=prod.id,
                type=MovementType.in_,
                quantity=item.quantity,
                reason=f"Cancelacion pedido {order.id}",
                user_id=user.id,
            )
        )

    order.status = OrderStatus.cancelled
    await db.commit()
    await db.refresh(order)

    result = await db.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    )
    return _serialize(result.scalar_one())


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")

    # Nota: si se pasa a 'cancelled' por esta via no se repone stock (usar /cancel)
    order.status = payload.status
    await db.commit()
    await db.refresh(order)
    return _serialize(order)
