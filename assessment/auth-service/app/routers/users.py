from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from uuid import UUID

from app.schemas.user import UserOut, RoleUpdate, UserListOut
from app.models.user import User, RoleEnum
from app.core.database import get_db
from app.dependencies.auth import require_role
from app.services import user as user_service

router = APIRouter(prefix="/auth/users", tags=["users"])

@router.get("", response_model=UserListOut)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([RoleEnum.admin, RoleEnum.super_admin]))],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    users = await user_service.get_users(db, skip=skip, limit=limit)
    total = await user_service.get_total_users(db)
    return {"total_count": total, "items": users}

@router.patch("/{id}/role", response_model=UserOut)
async def update_user_role(
    id: UUID,
    role_update: RoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([RoleEnum.super_admin]))]
):
    user = await user_service.get_user_by_id(db, id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    updated_user = await user_service.update_user_role(db, user, role_update.role)
    return updated_user
