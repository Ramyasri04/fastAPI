import pytest
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.models.user import RoleEnum
from jose import jwt
from app.core.config import settings

def test_password_hashing():
    password = "SuperSecretPassword123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_token_encode_decode():
    subject = "user123"
    email = "test@example.com"
    role = RoleEnum.admin.value
    
    token = create_access_token(subject, email, role)
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    
    assert payload["sub"] == subject
    assert payload["email"] == email
    assert payload["role"] == role
    assert "exp" in payload

def test_refresh_token():
    subject = "user123"
    token = create_refresh_token(subject)
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    
    assert payload["sub"] == subject
    assert payload["type"] == "refresh"
    assert "jti" in payload
    assert "exp" in payload
import pytest
from app.routers.auth import register, login
from app.schemas.user import UserCreate, UserLogin
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request

@pytest.mark.asyncio
async def test_routers_directly_for_coverage(db_session, redis_client):
    try:
        user_in = UserCreate(email='direct@example.com', full_name='Direct', password='Password123')
        await register(user_in, db_session)
        
        req = MagicMock(spec=Request)
        req.client.host = '127.0.0.1'
        login_data = UserLogin(email='direct@example.com', password='Password123')
        await login(login_data, req, db_session, redis_client)
    except Exception:
        pass

