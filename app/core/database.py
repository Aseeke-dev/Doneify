from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import Settings
from .base import Base
from collections.abc import AsyncGenerator

settings = Settings() # pyright: ignore[reportCallIssue]

database_url = settings.DATABASE_URL
if database_url.startswith("postgresql+psycopg2://"):
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

engine = create_async_engine(database_url)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
