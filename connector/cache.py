from functools import wraps
import time
from typing import Any, Dict, Optional, Callable
from config import logger

class Cache:
    """Simple in-memory cache with TTL support"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires'] > time.time():
                return entry['value']
            else:
                # Expired entry
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL in seconds"""
        self._cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }

    def invalidate(self, key: str) -> None:
        """Remove key from cache"""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()


cache = Cache()


def cached(ttl: int = 300, key_prefix: str = ''):
    """Decorator to cache function results"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"

            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {key}")
                return cached_value

            logger.debug(f"Cache miss for {key}")
            result = await func(*args, **kwargs)

            cache.set(key, result, ttl)
            return result

        return wrapper

    return decorator
