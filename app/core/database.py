"""
Configuración de base de datos (sin modelos SQL aún)
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings


def _derive_async_url(sync_url: str) -> str:
    """Convierte URL síncrona a asíncrona cuando sea posible."""
    if sync_url.startswith("sqlite"):
        # sqlite:/// -> sqlite+aiosqlite:/// para async
        return sync_url.replace("sqlite://", "sqlite+aiosqlite://")
    if sync_url.startswith("postgresql+asyncpg://"):
        return sync_url
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://")
    # Fallback: intentar mismo driver
    return sync_url


# Motores
engine = create_engine(settings.DATABASE_URL, future=True)
async_engine = create_async_engine(_derive_async_url(settings.DATABASE_URL), future=True)

# Sesiones
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Base declarativa (no hay tablas todavía)
Base = declarative_base()
metadata = MetaData()


def get_db():
    """Sesión síncrona."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Sesión asíncrona."""
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    """Crea tablas si existieran modelos SQLAlchemy."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


