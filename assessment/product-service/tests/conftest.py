import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import fakeredis.aioredis

from app.main import app
from app.core.database import get_db, Base
from app.dependencies.redis import get_redis
from app.dependencies.auth import get_current_user_payload, CurrentUser
from app.core.config import settings

@pytest_asyncio.fixture(scope="function")
async def async_db_engine():
    # Use SQLite in-memory for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(async_db_engine):
    async_session = async_sessionmaker(async_db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture(scope="function")
async def redis_client():
    # Use FakeRedis for testing
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()

@pytest_asyncio.fixture(scope="function")
async def async_client(db_session, redis_client):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: redis_client
    
    # Mock JWT authentication to bypass token decoding
    def override_get_current_user_payload():
        return CurrentUser(id="123e4567-e89b-12d3-a456-426614174000", role="super_admin", email="admin@example.com")
        
    app.dependency_overrides[get_current_user_payload] = override_get_current_user_payload
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
        
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def customer_client(db_session, redis_client):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: redis_client
    
    # Mock JWT authentication for customer
    def override_get_current_user_payload():
        return CurrentUser(id="111e4567-e89b-12d3-a456-426614174000", role="customer", email="customer@example.com")
        
    app.dependency_overrides[get_current_user_payload] = override_get_current_user_payload
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
        
    app.dependency_overrides.clear()
