import redis.asyncio as aioredis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

_redis_client = None


async def get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}. Caching disabled.")
            return None
    return _redis_client


async def cache_get(key: str):
    r = await get_redis()
    if not r:
        return None
    try:
        return await r.get(key)
    except Exception:
        return None


async def cache_set(key: str, value: str, ttl: int = 3600):
    r = await get_redis()
    if not r:
        return
    try:
        await r.set(key, value, ex=ttl)
    except Exception:
        pass


async def cache_delete(key: str):
    r = await get_redis()
    if not r:
        return
    try:
        await r.delete(key)
    except Exception:
        pass
