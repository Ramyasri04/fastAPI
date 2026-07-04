from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.schemas.category import CategoryCreate, CategoryOut
from app.core.database import get_db
from app.dependencies.auth import require_role
from app.services import category as category_service

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=list[CategoryOut])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    categories = await category_service.get_categories(db)
    return categories

@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user = Depends(require_role(["admin", "super_admin"]))
):
    # Check for name uniqueness
    categories = await category_service.get_categories(db)
    for c in categories:
        if c.name.lower() == category_in.name.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category with this name already exists")
    
    category = await category_service.create_category(db, category_in)
    return category
