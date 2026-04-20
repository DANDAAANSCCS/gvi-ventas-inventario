from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependencia FastAPI: entrega una sesion por request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
