import json
from uuid import UUID
from redis.asyncio import Redis
from app.schemas.product import ProductOut

async def get_cached_product(redis: Redis, product_id: UUID) -> dict | None:
    data = await redis.get(f"product:{product_id}")
    if data:
        return json.loads(data)
    return None

async def set_cached_product(redis: Redis, product_id: UUID, product_data: ProductOut):
    # Convert UUIDs and datetimes to string for JSON serialization
    json_data = product_data.model_dump_json()
    await redis.setex(f"product:{product_id}", 300, json_data)

async def invalidate_cached_product(redis: Redis, product_id: UUID):
    await redis.delete(f"product:{product_id}")
