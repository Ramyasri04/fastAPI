from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from typing import Annotated
from uuid import UUID

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.redis import get_redis
from app.models.user import User, RoleEnum
from app.core.logger import logger

security = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # The requirements say "payload includes sub (user_id), email, role, exp"
    # To avoid DB lookups for authorization if possible, we could just return a constructed User from payload.
    # But for `/auth/me` we might need full data. Let's do a DB lookup for now or just trust the payload.
    # Let's do DB lookup to ensure user is active and exists.
    try:
        user_uuid = UUID(str(user_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    user = await db.get(User, user_uuid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    
    return user

def require_role(allowed_roles: list[RoleEnum]):
    async def role_checker(current_user: Annotated[User, Depends(get_current_user)]):
        # Role hierarchy: customer < admin < super_admin
        role_hierarchy = {
            RoleEnum.customer: 1,
            RoleEnum.admin: 2,
            RoleEnum.super_admin: 3
        }
        user_level = role_hierarchy.get(current_user.role, 0)
        allowed_levels = [role_hierarchy.get(r, 0) for r in allowed_roles]
        
        if user_level < min(allowed_levels):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user
    return role_checker
