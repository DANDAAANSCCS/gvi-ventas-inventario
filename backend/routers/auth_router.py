import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from auth import create_access_token, hash_password, verify_password
from config import settings
from database import get_db
from dependencies import get_current_user
from email_service import send_password_reset_email
from models import Client, PasswordResetToken, User, UserRole
from schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SimpleMessage,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _hash_token(token: str) -> str:
    """SHA-256 en hex. Guardamos solo el hash en DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Crea un usuario cliente nuevo y su perfil. Devuelve JWT."""
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
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario desactivado")

    token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.post("/forgot-password", response_model=SimpleMessage)
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Genera un token de reset y manda el correo. Siempre responde 200 aunque el email no exista
    (para no filtrar si un correo esta registrado)."""
    email = payload.email.lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        # Invalidar tokens anteriores no usados para este usuario.
        await db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_expire_minutes)

        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        await db.commit()

        reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password.html?token={raw_token}"
        # Enviar el email en background para no bloquear la respuesta.
        background_tasks.add_task(send_password_reset_email, email, reset_url)

    return SimpleMessage(
        message="Si el correo está registrado, te enviaremos un enlace para restablecer tu contraseña."
    )


@router.post("/reset-password", response_model=SimpleMessage)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Valida el token y actualiza la contrasena del usuario."""
    token_hash = _hash_token(payload.token)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    token_row = result.scalar_one_or_none()

    if not token_row or token_row.used_at is not None or token_row.expires_at < now:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "El enlace es inválido o ya expiró. Solicita uno nuevo.",
        )

    result = await db.execute(select(User).where(User.id == token_row.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Usuario no disponible")

    user.password_hash = hash_password(payload.new_password)
    token_row.used_at = now
    await db.commit()

    logger.info("[auth] Password actualizada para user %s", user.email)
    return SimpleMessage(message="Contraseña actualizada correctamente.")
