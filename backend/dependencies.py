from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import decode_token
from database import get_db
from models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extrae el usuario autenticado desde el JWT del header Authorization."""
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token requerido")

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido o expirado")

    result = await db.execute(
        select(User).where(User.id == UUID(user_id)).options(selectinload(User.client))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado o inactivo")
    return user


def require_role(*allowed: UserRole):
    """Dependencia que exige que el usuario tenga un rol especifico."""

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Requiere rol: {', '.join(r.value for r in allowed)}"
            )
        return user

    return checker
