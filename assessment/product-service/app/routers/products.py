from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import Annotated
from uuid import UUID

from app.schemas.product import ProductCreate, ProductUpdate, ProductStockUpdate, ProductOut, ProductListOut
from app.core.database import get_db
from app.dependencies.redis import get_redis
from app.dependencies.auth import require_role, CurrentUser
from app.services import product as product_service
from app.services import category as category_service
from app.services import cache as cache_service

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=ProductListOut)
async def list_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_inactive: bool = False,
    category_id: UUID = None,
    min_price: float = None,
    max_price: float = None
):
    skip = (page - 1) * page_size
    products = await product_service.get_products(
        db, skip=skip, limit=page_size, include_inactive=include_inactive,
        category_id=category_id, min_price=min_price, max_price=max_price
    )
    total = await product_service.get_total_products(
        db, include_inactive=include_inactive,
        category_id=category_id, min_price=min_price, max_price=max_price
    )
    return {"total_count": total, "items": products}

@router.get("/{id}", response_model=ProductOut)
async def get_product(
    id: str,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)]
):
    # Try fetching from cache if it's a UUID
    try:
        product_uuid = UUID(id)
        cached = await cache_service.get_cached_product(redis, product_uuid)
        if cached:
            response.headers["X-Cache"] = "HIT"
            return cached
    except ValueError:
        pass # It's a slug, we will bypass cache for slug or could cache by slug too. Let's just lookup.

    response.headers["X-Cache"] = "MISS"
    product = await product_service.get_product_by_id_or_slug(db, id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Only cache if we looked up by UUID (simplifies cache invalidation)
    try:
        product_uuid = UUID(id)
        out_model = ProductOut.model_validate(product)
        await cache_service.set_cached_product(redis, product_uuid, out_model)
    except ValueError:
        pass
        
    return product

@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_role(["admin", "super_admin"]))]
):
    category = await category_service.get_category_by_id(db, str(product_in.category_id))
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category does not exist")
    
    product = await product_service.create_product(db, product_in, current_user.id)
    return product

@router.put("/{id}", response_model=ProductOut)
async def update_product(
    id: UUID,
    product_in: ProductUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[CurrentUser, Depends(require_role(["admin", "super_admin"]))]
):
    product = await product_service.get_product_by_id_or_slug(db, str(id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        
    if product_in.category_id:
        category = await category_service.get_category_by_id(db, str(product_in.category_id))
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category does not exist")

    updated_product = await product_service.update_product(db, product, product_in)
    await cache_service.invalidate_cached_product(redis, id)
    return updated_product

@router.patch("/{id}/stock", response_model=ProductOut)
async def update_product_stock(
    id: UUID,
    stock_in: ProductStockUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[CurrentUser, Depends(require_role(["admin", "super_admin"]))]
):
    product = await product_service.get_product_by_id_or_slug(db, str(id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        
    success = await product_service.update_stock(db, product, stock_in.delta)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stock operation would result in negative stock")
        
    await cache_service.invalidate_cached_product(redis, id)
    return product

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[CurrentUser, Depends(require_role(["admin", "super_admin"]))]
):
    product = await product_service.get_product_by_id_or_slug(db, str(id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        
    await product_service.soft_delete_product(db, product)
    await cache_service.invalidate_cached_product(redis, id)
    return None
