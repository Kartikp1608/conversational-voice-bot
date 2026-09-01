import os
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force mock mode and in-memory database before any other imports
os.environ["LLM_PROVIDER"] = "mock"
os.environ["STT_PROVIDER"] = "mock"
os.environ["TTS_PROVIDER"] = "mock"
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from config.settings import settings

settings.LLM_PROVIDER = "mock"
settings.STT_PROVIDER = "mock"
settings.TTS_PROVIDER = "mock"
settings.APP_ENV = "testing"
settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from api.main import app
from database.db import get_db_session, init_db
from database.models import Base

# Test In-Memory Database Engine
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Ensure all provider keys and settings are set to mock for entire test session."""
    settings.LLM_PROVIDER = "mock"
    settings.STT_PROVIDER = "mock"
    settings.TTS_PROVIDER = "mock"
    settings.APP_ENV = "testing"
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated in-memory SQLite database session for unit tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI TestClient with overridden database session."""
    await init_db()

    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
