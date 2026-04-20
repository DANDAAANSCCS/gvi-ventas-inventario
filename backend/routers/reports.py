from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_role
from models import Order, OrderItem, OrderStatus, Product, User, UserRole
from schemas import SalesReportItem, TopProductItem

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/sales", response_model=list[SalesReportItem])
async def sales_by_day(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    """Ventas agregadas por dia de los ultimos N dias (pedidos no cancelados)."""
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(
            func.date_trunc("day", Order.created_at).label("day"),
            func.coalesce(func.sum(Order.total), 0).label("total"),
            func.count(Order.id).label("count"),
        )
        .where(Order.created_at >= since, Order.status != OrderStatus.cancelled)
        .group_by("day")
        .order_by("day")
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [SalesReportItem(date=r.day.date(), total=r.total, count=r.count) for r in rows]


@router.get("/top-products", response_model=list[TopProductItem])
async def top_products(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=100),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(
            Product.id.label("product_id"),
            Product.name.label("name"),
            func.sum(OrderItem.quantity).label("quantity"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.created_at >= since, Order.status != OrderStatus.cancelled)
        .group_by(Product.id, Product.name)
        .order_by(desc("quantity"))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        TopProductItem(
            product_id=r.product_id, name=r.name, quantity=int(r.quantity), revenue=r.revenue
        )
        for r in rows
    ]
