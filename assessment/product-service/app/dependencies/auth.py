from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Annotated

from app.core.config import settings

security = HTTPBearer()

class CurrentUser:
    def __init__(self, id: str, role: str, email: str):
        self.id = id
        self.role = role
        self.email = email

async def get_current_user_payload(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role")
        email = payload.get("email")
        if not user_id or not role:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return CurrentUser(id=user_id, role=role, email=email)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

def require_role(allowed_roles: list[str]):
    async def role_checker(current_user: Annotated[CurrentUser, Depends(get_current_user_payload)]):
        role_hierarchy = {
            "customer": 1,
            "admin": 2,
            "super_admin": 3
        }
        user_level = role_hierarchy.get(current_user.role, 0)
        allowed_levels = [role_hierarchy.get(r, 0) for r in allowed_roles]
        
        if user_level < min(allowed_levels):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user
    return role_checker
