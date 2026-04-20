from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import hash_password
from database import get_db
from dependencies import get_current_user, require_role
from models import Client, User, UserRole
from schemas import ClientCreate, ClientOut, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])


def _to_out(client: Client) -> ClientOut:
    return ClientOut(
        id=client.id,
        user_id=client.user_id,
        name=client.name,
        phone=client.phone,
        address=client.address,
        email=client.user.email if client.user else None,
        active=client.active,
        created_at=client.created_at,
    )


@router.get("/me", response_model=ClientOut)
async def get_my_profile(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Devuelve el perfil de cliente del usuario autenticado."""
    result = await db.execute(
        select(Client).where(Client.user_id == user.id).options(selectinload(Client.user))
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perfil no encontrado")
    return _to_out(client)


@router.put("/me", response_model=ClientOut)
async def update_my_profile(
    payload: ClientUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(Client.user_id == user.id).options(selectinload(Client.user))
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perfil no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await db.commit()
    await db.refresh(client)
    return _to_out(client)


@router.get("", response_model=list[ClientOut])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    only_active: bool = True,
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    stmt = select(Client).options(selectinload(Client.user))
    if only_active:
        stmt = stmt.where(Client.active.is_(True))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.join(User).where(or_(Client.name.ilike(like), User.email.ilike(like)))
    stmt = stmt.order_by(Client.created_at.desc())
    result = await db.execute(stmt)
    return [_to_out(c) for c in result.scalars().all()]


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Admin crea cliente + usuario asociado."""
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=UserRole.client,
    )
    db.add(user)
    await db.flush()

    client = Client(
        user_id=user.id,
        name=payload.name,
        phone=payload.phone,
        address=payload.address,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client, ["user"])
    return _to_out(client)


@router.put("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id).options(selectinload(Client.user))
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await db.commit()
    await db.refresh(client)
    return _to_out(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Eliminacion logica del cliente y desactivacion de su usuario."""
    result = await db.execute(
        select(Client).where(Client.id == client_id).options(selectinload(Client.user))
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    client.active = False
    if client.user:
        client.user.is_active = False
    await db.commit()
