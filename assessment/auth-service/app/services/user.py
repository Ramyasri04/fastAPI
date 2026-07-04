from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func
from app.models.user import User, RoleEnum
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash
from uuid import UUID
from datetime import datetime, timezone

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: str | UUID) -> User | None:
    try:
        user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
    except ValueError:
        return None
    return await db.get(User, user_uuid)

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email.lower(),
        hashed_password=hashed_password,
        full_name=user_in.full_name
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 20) -> list[User]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

async def get_total_users(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(User.id)))
    return result.scalar()

async def update_user(db: AsyncSession, user: User, user_in: UserUpdate) -> User:
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    await db.commit()
    await db.refresh(user)
    return user

async def update_user_role(db: AsyncSession, user: User, role: RoleEnum) -> User:
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user

async def update_last_login(db: AsyncSession, user: User):
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
