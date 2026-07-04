import redis.asyncio as redis
from app.core.logger import logger
from jose import jwt
from app.core.config import settings

async def check_rate_limit(redis_client: redis.Redis, email: str) -> bool:
    key = f"rate_limit:login:{email.lower()}"
    attempts = await redis_client.get(key)
    if attempts and int(attempts) >= 5:
        return False
    return True

async def increment_rate_limit(redis_client: redis.Redis, email: str):
    key = f"rate_limit:login:{email.lower()}"
    await redis_client.incr(key)
    ttl = await redis_client.ttl(key)
    if ttl == -1:
        await redis_client.expire(key, 15 * 60) # 15 minutes

async def clear_rate_limit(redis_client: redis.Redis, email: str):
    key = f"rate_limit:login:{email.lower()}"
    await redis_client.delete(key)

async def blacklist_token(redis_client: redis.Redis, token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            import time
            now = int(time.time())
            expires_in = exp - now
            if expires_in > 0:
                key = f"blacklist:token:{jti}"
                await redis_client.set(key, "true", ex=expires_in)
    except Exception as e:
        logger.error("Failed to blacklist token", error=str(e))

async def is_token_blacklisted(redis_client: redis.Redis, jti: str) -> bool:
    key = f"blacklist:token:{jti}"
    exists = await redis_client.exists(key)
    return exists > 0
