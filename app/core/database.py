from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import Settings
from sqlalchemy.ext.declarative import declarative_base

settings = Settings() # pyright: ignore[reportCallIssue]

database_url = settings.DATABASE_URL
if database_url.startswith("posgresql+psycopg2://"):
    database_url = database_url.replace("posgresql+psycopg2://", "postgresql+asyncpg://", 1)

engine = create_async_engine(database_url)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()