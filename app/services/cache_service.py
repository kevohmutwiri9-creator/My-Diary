import os
import redis
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import current_app

class CacheService:
    def __init__(self):
        self.redis_client = None
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()  # Test connection
            print("Redis cache connected successfully")  # Use print instead of current_app.logger
        except Exception as e:
            print(f"Redis connection failed: {str(e)}. Using in-memory cache.")  # Use print instead of current_app.logger
            self.redis_client = None
            self.cache = {}  # Fallback to in-memory cache
    
    def get(self, key: str):
        """Get value from cache"""
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                print(f"Redis get error: {str(e)}")  # Use print instead of current_app.logger
                return None
        else:
            return self.cache.get(key)
    
    def set(self, key: str, value, timeout: int = 3600):
        """Set value in cache with timeout in seconds"""
        if self.redis_client:
            try:
                self.redis_client.setex(key, timeout, json.dumps(value))
                return True
            except Exception as e:
                print(f"Redis set error: {str(e)}")  # Use print instead of current_app.logger
                return False
        else:
            self.cache[key] = value
            return True
    
    def delete(self, key: str):
        """Delete key from cache"""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                print(f"Redis delete error: {str(e)}")  # Use print instead of current_app.logger
                return False
        else:
            if key in self.cache:
                del self.cache[key]
            return True
    
    def clear(self):
        """Clear all cache"""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                return True
            except Exception as e:
                print(f"Redis clear error: {str(e)}")  # Use print instead of current_app.logger
                return False
        else:
            self.cache.clear()
            return True

# Global cache service instance
cache_service = CacheService()


def cache_key(prefix: str, *args):
    """Generate cache key"""
    key_parts = [prefix] + [str(arg) for arg in args]
    return ":".join(key_parts)


def cached(timeout: int = 3600, key_prefix: str = "default"):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_data = [func.__name__] + list(args) + list(kwargs.values())
            key = cache_key(key_prefix, *cache_key_data)
            
            # Try to get from cache
            cached_result = cache_service.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_service.set(key, result, timeout)
            return result
        return wrapper
    return decorator


def cache_user_data(timeout: int = 1800):
    """Cache user-specific data"""
    return cached(timeout=timeout, key_prefix="user")


def cache_analytics(timeout: int = 3600):
    """Cache analytics data"""
    return cached(timeout=timeout, key_prefix="analytics")


def cache_entries(timeout: int = 1800):
    """Cache entry data"""
    return cached(timeout=timeout, key_prefix="entries")


def cache_ai_response(timeout: int = 7200):
    """Cache AI responses"""
    return cached(timeout=timeout, key_prefix="ai")
