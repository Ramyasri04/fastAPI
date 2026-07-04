from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, exc
from sqlalchemy.sql import func
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.category import generate_slug
from uuid import UUID

async def generate_unique_slug(db: AsyncSession, name: str) -> str:
    base_slug = generate_slug(name)
    slug = base_slug
    counter = 1
    while True:
        result = await db.execute(select(Product.id).where(Product.slug == slug))
        if not result.scalars().first():
            return slug
        counter += 1
        slug = f"{base_slug}-{counter}"

async def get_products(db: AsyncSession, skip: int = 0, limit: int = 20, include_inactive: bool = False, category_id: UUID = None, min_price: float = None, max_price: float = None):
    query = select(Product)
    if not include_inactive:
        query = query.where(Product.is_active == True)
    if category_id:
        query = query.where(Product.category_id == category_id)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

async def get_total_products(db: AsyncSession, include_inactive: bool = False, category_id: UUID = None, min_price: float = None, max_price: float = None) -> int:
    query = select(func.count(Product.id))
    if not include_inactive:
        query = query.where(Product.is_active == True)
    if category_id:
        query = query.where(Product.category_id == category_id)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
        
    result = await db.execute(query)
    return result.scalar()

async def get_product_by_id_or_slug(db: AsyncSession, id_or_slug: str) -> Product | None:
    try:
        # Try as UUID
        product_id = UUID(id_or_slug)
        result = await db.execute(select(Product).where(Product.id == product_id))
    except ValueError:
        # Treat as slug
        result = await db.execute(select(Product).where(Product.slug == id_or_slug))
    return result.scalars().first()

async def create_product(db: AsyncSession, product_in: ProductCreate, created_by: str) -> Product:
    slug = await generate_unique_slug(db, product_in.name)
    db_product = Product(
        name=product_in.name,
        slug=slug,
        description=product_in.description,
        price=product_in.price,
        stock_quantity=product_in.stock_quantity,
        category_id=product_in.category_id,
        is_active=product_in.is_active,
        created_by=UUID(created_by)
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

async def update_product(db: AsyncSession, product: Product, product_in: ProductUpdate) -> Product:
    update_data = product_in.model_dump(exclude_unset=True)
    if 'name' in update_data and update_data['name'] != product.name:
        product.slug = await generate_unique_slug(db, update_data['name'])
    
    for field, value in update_data.items():
        setattr(product, field, value)
        
    await db.commit()
    await db.refresh(product)
    return product

async def update_stock(db: AsyncSession, product: Product, delta: int) -> bool:
    # Use atomic update to prevent race conditions
    # Check if this operation would make stock negative
    if product.stock_quantity + delta < 0:
        return False
        
    stmt = update(Product).where(
        Product.id == product.id,
        Product.stock_quantity + delta >= 0
    ).values(stock_quantity=Product.stock_quantity + delta)
    
    result = await db.execute(stmt)
    await db.commit()
    await db.refresh(product)
    
    # Return true if row was updated (meaning condition held)
    return result.rowcount > 0

async def soft_delete_product(db: AsyncSession, product: Product):
    product.is_active = False
    await db.commit()
    await db.refresh(product)
    return product
