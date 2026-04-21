from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import hash_password
from database import get_db
from dependencies import get_current_user, require_role
from models import Client, User, UserRole
from schemas import UserAdminCreate, UserAdminOut, UserAdminPatch, UserResetPassword

router = APIRouter(prefix="/users", tags=["users"])


def _to_out(user: User) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        name=user.client.name if user.client else None,
    )


@router.get("", response_model=list[UserAdminOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    role: UserRole | None = None,
    only_active: bool = False,
    q: str | None = None,
    _: User = Depends(require_role(UserRole.admin)),
):
    """Lista de usuarios (admin). Filtra por rol, estado y busqueda (email/nombre)."""
    stmt = select(User).options(selectinload(User.client))
    if role is not None:
        stmt = stmt.where(User.role == role)
    if only_active:
        stmt = stmt.where(User.is_active.is_(True))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.outerjoin(Client).where(or_(User.email.ilike(like), Client.name.ilike(like)))
    stmt = stmt.order_by(User.created_at.desc())
    result = await db.execute(stmt)
    return [_to_out(u) for u in result.scalars().unique().all()]


@router.post("", response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserAdminCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Crea un usuario con el rol indicado. Si rol=client, crea tambien el Client asociado."""
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")

    if payload.role == UserRole.client and not payload.name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El rol client requiere nombre")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.flush()

    if payload.role == UserRole.client:
        client = Client(
            user_id=user.id,
            name=payload.name.strip(),
            phone=payload.phone,
            address=payload.address,
        )
        db.add(client)

    await db.commit()
    await db.refresh(user, ["client"])
    return _to_out(user)


@router.patch("/{user_id}", response_model=UserAdminOut)
async def patch_user(
    user_id: UUID,
    payload: UserAdminPatch,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(UserRole.admin)),
):
    """Actualiza rol y/o is_active. Admin no se puede auto-desactivar ni auto-degradar."""
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.client))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    data = payload.model_dump(exclude_unset=True)
    if user.id == current.id:
        if "is_active" in data and data["is_active"] is False:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes desactivar tu propia cuenta")
        if "role" in data and data["role"] != UserRole.admin:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes cambiar tu propio rol")

    for field, value in data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return _to_out(user)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def admin_reset_password(
    user_id: UUID,
    payload: UserResetPassword,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    """Admin fija una nueva contrasena directamente (bypass token email)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    user.password_hash = hash_password(payload.new_password)
    await db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(UserRole.admin)),
):
    """Soft-delete (is_active=false). Admin no se puede eliminar a si mismo."""
    if user_id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes eliminar tu propia cuenta")
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.client))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    user.is_active = False
    if user.client:
        user.client.active = False
    await db.commit()
