"""
OpenLI HIE Agent Runner - Redis-Based Rate Limiter

Sliding window counter implementation using Redis.
Each user+category combination gets a counter with a 60-second window.
"""

import time
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis sliding window rate limiter for tool execution."""

    def __init__(self, redis_url: str = "redis://redis:6379/0"):
        self._redis = None
        self._redis_url = redis_url

    def _get_redis(self):
        """Lazy Redis connection init."""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
                self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._redis = None
        return self._redis

    async def check(self, user_id: str, category: str, limit: int, window: int = 60) -> bool:
        """Check if the request is within rate limits.

        Uses a simple sliding window counter: one Redis key per user+category,
        with a TTL equal to the window. INCR + EXPIRE is atomic enough for
        our use case (GenAI agent tool calls, not sub-millisecond APIs).

        Args:
            user_id: The user's ID
            category: Rate limit category (bash, file_writes, api_calls, hl7_sends)
            limit: Maximum allowed calls per window
            window: Window size in seconds (default: 60)

        Returns:
            True if allowed, False if rate exceeded
        """
        r = self._get_redis()
        if r is None:
            return True  # Fail open if Redis is unavailable

        key = f"rate:{user_id}:{category}"
        try:
            current = r.get(key)
            if current is not None and int(current) >= limit:
                return False

            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            pipe.execute()
            return True
        except Exception as e:
            logger.warning(f"Rate limit check error (allowing): {e}")
            return True  # Fail open
