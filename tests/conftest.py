from collections.abc import AsyncGenerator, Generator
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import EmailService
from app.core.base import Base
from app.core.database import get_db
import app.main as main_module
from app.main import app
from app.services import auth as auth_service_module


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}
        self.counters: dict[str, int] = {}

    def setex(self, key: str, seconds: int, value: str) -> None:
        self.values[key] = value
        self.expirations[key] = seconds

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def getdel(self, key: str) -> str | None:
        return self.values.pop(key, None)

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if self.values.pop(key, None) is not None:
                deleted += 1
        return deleted

    def set(self, key: str, value: str, ex: int, nx: bool) -> bool:
        if nx and key in self.values:
            return False
        self.setex(key, ex, value)
        return True

    def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = seconds
        return True


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    redis = FakeRedis()
    monkeypatch.setattr(auth_service_module, "redis_client", redis)
    return redis


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    emails: list[tuple[str, str]] = []

    async def fake_send_otp(
        self: EmailService,
        email: str,
        code: str,
        background_tasks: object,
    ) -> None:
        emails.append((email, code))

    monkeypatch.setattr(EmailService, "send_otp", fake_send_otp)
    return emails


@pytest.fixture
def db_session_factory() -> Generator[async_sessionmaker[AsyncSession], None, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def create_tables() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def drop_tables() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(create_tables())
    yield session_factory
    asyncio.run(drop_tables())


@pytest.fixture
def client(
    fake_redis: FakeRedis,
    sent_emails: list[tuple[str, str]],
    db_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with db_session_factory() as session:
            yield session

    async def no_op_reminder_worker() -> None:
        return None

    monkeypatch.setattr(main_module, "event_reminder_worker", no_op_reminder_worker)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()