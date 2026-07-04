from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.category import Category
from app.schemas.category import CategoryCreate
import re
from uuid import UUID

def generate_slug(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')

async def get_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category))
    return result.scalars().all()

async def get_category_by_id(db: AsyncSession, category_id: str | UUID) -> Category | None:
    try:
        c_uuid = category_id if isinstance(category_id, UUID) else UUID(str(category_id))
    except ValueError:
        return None
    return await db.get(Category, c_uuid)

async def create_category(db: AsyncSession, category_in: CategoryCreate) -> Category:
    slug = generate_slug(category_in.name)
    db_category = Category(name=category_in.name, slug=slug)
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category
