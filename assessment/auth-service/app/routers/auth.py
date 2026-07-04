from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from jose import jwt, JWTError
from typing import Annotated

from app.schemas.user import UserCreate, UserOut, Token, UserUpdate, UserLogin, TokenRefresh
from app.models.user import User
from app.core.database import get_db
from app.dependencies.redis import get_redis
from app.dependencies.auth import get_current_user
from app.services import user as user_service
from app.services import auth as auth_service
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.core.logger import logger
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    existing_user = await user_service.get_user_by_email(db, user_in.email.lower())
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    user = await user_service.create_user(db, user_in)
    logger.info("User registered", user_id=str(user.id), email=user.email)
    return user

@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)]
):
    email = login_data.email.lower()
    ip = request.client.host if request.client else "unknown"
    
    is_allowed = await auth_service.check_rate_limit(redis_client, email)
    if not is_allowed:
        logger.warning("Rate limit exceeded for login", email=email, ip=ip)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed login attempts")

    user = await user_service.get_user_by_email(db, email)
    if not user or not verify_password(login_data.password, user.hashed_password):
        await auth_service.increment_rate_limit(redis_client, email)
        logger.warning("Failed login attempt", email=email, ip=ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        logger.warning("Inactive user login attempt", email=email, ip=ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    await auth_service.clear_rate_limit(redis_client, email)
    await user_service.update_last_login(db, user)

    access_token = create_access_token(subject=str(user.id), email=user.email, role=user.role.value)
    refresh_token = create_refresh_token(subject=str(user.id))
    
    logger.info("User logged in", user_id=str(user.id))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: TokenRefresh,
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        payload = jwt.decode(refresh_data.refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            
        is_blacklisted = await auth_service.is_token_blacklisted(redis_client, jti)
        if is_blacklisted:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token blacklisted")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = await user_service.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or deleted")

        # Blacklist old refresh token
        await auth_service.blacklist_token(redis_client, refresh_data.refresh_token)
        
        access_token = create_access_token(subject=str(user.id), email=user.email, role=user.role.value)
        new_refresh_token = create_refresh_token(subject=str(user.id))
        
        return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    refresh_data: TokenRefresh,
    current_user: Annotated[User, Depends(get_current_user)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)]
):
    await auth_service.blacklist_token(redis_client, refresh_data.refresh_token)
    logger.info("User logged out", user_id=str(current_user.id))
    return None

@router.get("/me", response_model=UserOut)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user

@router.patch("/me", response_model=UserOut)
async def update_me(
    user_in: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    updated_user = await user_service.update_user(db, current_user, user_in)
    return updated_user
