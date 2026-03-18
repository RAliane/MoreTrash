from typing import Any, Optional
import json
import redis.asyncio as redis
import structlog

from app.infrastructure.config import settings
from app.infrastructure.logging import get_database_logger

logger = get_database_logger()


class RedisCache:
    """Redis cache implementation."""

    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.ttl = settings.CACHE_TTL
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url)
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            client = await self._get_client()
            ttl_value = ttl or self.ttl
            json_value = json.dumps(value)
            await client.setex(key, ttl_value, json_value)
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            client = await self._get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning("Cache exists check failed", key=key, error=str(e))
            return False
