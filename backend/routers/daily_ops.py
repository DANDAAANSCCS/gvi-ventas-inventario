from datetime import date as date_type, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_role
from models import DailyOperation, Order, OrderStatus, User, UserRole
from schemas import DailyOpClose, DailyOpCreate, DailyOpOut

router = APIRouter(prefix="/daily-operations", tags=["daily-ops"])


def _to_out(op: DailyOperation) -> DailyOpOut:
    return DailyOpOut(
        id=op.id,
        date=op.date,
        opening_cash=op.opening_cash,
        closing_cash=op.closing_cash,
        total_sales=op.total_sales,
        notes=op.notes,
        created_by=op.created_by,
        created_at=op.created_at,
        is_closed=op.closing_cash is not None,
    )


async def _sum_sales_for_date(db: AsyncSession, day: date_type):
    """Suma total de pedidos NO cancelados creados en el dia indicado."""
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    stmt = select(func.coalesce(func.sum(Order.total), 0)).where(
        Order.created_at >= start,
        Order.created_at < end,
        Order.status != OrderStatus.cancelled,
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.get("", response_model=list[DailyOpOut])
async def list_daily_ops(
    db: AsyncSession = Depends(get_db),
    date_from: date_type | None = Query(None, alias="from"),
    date_to: date_type | None = Query(None, alias="to"),
    limit: int = Query(60, ge=1, le=365),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    """Historial de caja. Rango opcional."""
    stmt = select(DailyOperation)
    if date_from:
        stmt = stmt.where(DailyOperation.date >= date_from)
    if date_to:
        stmt = stmt.where(DailyOperation.date <= date_to)
    stmt = stmt.order_by(DailyOperation.date.desc()).limit(limit)
    result = await db.execute(stmt)
    return [_to_out(o) for o in result.scalars().all()]


@router.get("/today", response_model=DailyOpOut)
async def get_today(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    """La caja de hoy, con total_sales recalculado en tiempo real."""
    today = date_type.today()
    result = await db.execute(select(DailyOperation).where(DailyOperation.date == today))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Caja no abierta hoy")

    # Refresh total_sales on read for realtime tracking.
    op.total_sales = await _sum_sales_for_date(db, today)
    await db.commit()
    await db.refresh(op)
    return _to_out(op)


@router.post("", response_model=DailyOpOut, status_code=status.HTTP_201_CREATED)
async def open_cash(
    payload: DailyOpCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    """Abre la caja del dia. Una unica caja por fecha."""
    today = date_type.today()
    result = await db.execute(select(DailyOperation).where(DailyOperation.date == today))
    if result.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "La caja de hoy ya fue abierta")

    op = DailyOperation(
        date=today,
        opening_cash=payload.opening_cash,
        notes=payload.notes,
        created_by=current.id,
    )
    db.add(op)
    await db.commit()
    await db.refresh(op)
    return _to_out(op)


@router.patch("/{op_id}", response_model=DailyOpOut)
async def close_cash(
    op_id: UUID,
    payload: DailyOpClose,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    """Cierra la caja: guarda closing_cash y recalcula total_sales de ese dia."""
    result = await db.execute(select(DailyOperation).where(DailyOperation.id == op_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Caja no encontrada")
    if op.closing_cash is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La caja ya fue cerrada")

    op.closing_cash = payload.closing_cash
    if payload.notes is not None:
        op.notes = payload.notes
    op.total_sales = await _sum_sales_for_date(db, op.date)
    await db.commit()
    await db.refresh(op)
    return _to_out(op)
