from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
from typing import Annotated
from sqlalchemy import text

from app.core.database import get_db
from app.dependencies.redis import get_redis
from app.core.logger import logger

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)]
):
    status_data = {"status": "ok", "db": "unknown", "redis": "unknown"}
    
    try:
        await db.execute(text("SELECT 1"))
        status_data["db"] = "ok"
    except Exception as e:
        status_data["db"] = "error"
        logger.error("Database health check failed", error=str(e))
        
    try:
        await redis_client.ping()
        status_data["redis"] = "ok"
    except Exception as e:
        status_data["redis"] = "error"
        logger.error("Redis health check failed", error=str(e))
        
    if status_data["db"] == "error" or status_data["redis"] == "error":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=status_data)
        
    return status_data
