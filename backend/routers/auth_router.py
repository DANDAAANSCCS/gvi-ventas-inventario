from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import create_access_token, hash_password, verify_password
from database import get_db
from dependencies import get_current_user
from models import Client, User, UserRole
from schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Crea un usuario cliente nuevo y su perfil. Devuelve JWT."""
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya esta registrado")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=UserRole.client,
    )
    db.add(user)
    await db.flush()

    client = Client(
        user_id=user.id,
        name=payload.name.strip(),
        phone=payload.phone,
        address=payload.address,
    )
    db.add(client)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Autentica por email+password. Devuelve JWT."""
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario desactivado")

    token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
