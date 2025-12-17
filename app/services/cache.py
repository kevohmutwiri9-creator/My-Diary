"""
Caching and Performance Optimization Services for My Diary App
"""

import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Union
from functools import wraps
import redis
from flask import current_app, request, g, has_app_context
from flask_login import current_user
from app import db
from app.models.user import User
from app.models.entry import Entry
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service"""
    
    def __init__(self):
        self.redis_client = None
        self.default_ttl = 3600  # 1 hour

        if has_app_context():
            self._connect()

    def init_app(self, app):
        """Initialize the service with a Flask app instance."""
        self._connect(app=app)
    
    def _connect(self, app=None):
        """Connect to Redis"""
        try:
            if app is None:
                if not has_app_context():
                    return
                app = current_app

            redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=False)
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {str(e)}. Using in-memory cache fallback.")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return pickle.loads(value)
            else:
                # Fallback to in-memory cache
                return getattr(g, f'_cache_{key}', None)
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or self.default_ttl
            serialized_value = pickle.dumps(value)
            
            if self.redis_client:
                return self.redis_client.setex(key, ttl, serialized_value)
            else:
                # Fallback to in-memory cache
                setattr(g, f'_cache_{key}', value)
                return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                # Fallback to in-memory cache
                if hasattr(g, f'_cache_{key}'):
                    delattr(g, f'_cache_{key}')
                return True
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # Fallback - limited in-memory pattern matching
                count = 0
                for attr in list(g.__dict__.keys()):
                    if attr.startswith('_cache_') and pattern.replace('*', '') in attr:
                        delattr(g, attr)
                        count += 1
                return count
        except Exception as e:
            logger.error(f"Cache delete pattern error: {str(e)}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            else:
                return hasattr(g, f'_cache_{key}')
        except Exception as e:
            logger.error(f"Cache exists error: {str(e)}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment numeric value"""
        try:
            if self.redis_client:
                return self.redis_client.incr(key, amount)
            else:
                # Fallback to in-memory
                current = getattr(g, f'_cache_{key}', 0)
                new_value = current + amount
                setattr(g, f'_cache_{key}', new_value)
                return new_value
        except Exception as e:
            logger.error(f"Cache increment error: {str(e)}")
            return None
    
    def get_ttl(self, key: str) -> Optional[int]:
        """Get time-to-live for key"""
        try:
            if self.redis_client:
                return self.redis_client.ttl(key)
            else:
                return -1  # In-memory cache doesn't have TTL
        except Exception as e:
            logger.error(f"Cache TTL error: {str(e)}")
            return None
    
    def clear_all(self) -> bool:
        """Clear all cache"""
        try:
            if self.redis_client:
                return self.redis_client.flushdb()
            else:
                # Clear in-memory cache
                for attr in list(g.__dict__.keys()):
                    if attr.startswith('_cache_'):
                        delattr(g, attr)
                return True
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            return False


class QueryOptimizer:
    """Database query optimization service"""
    
    @staticmethod
    def get_user_entries_optimized(user_id: int, limit: int = 50, offset: int = 0) -> List[Entry]:
        """Optimized query for user entries"""
        try:
            return db.session.query(Entry).filter(
                Entry.user_id == user_id
            ).options(
                db.joinedload(Entry.user)  # Eager load user
            ).order_by(
                Entry.created_at.desc()
            ).limit(limit).offset(offset).all()
        except Exception as e:
            logger.error(f"Optimized entries query error: {str(e)}")
            return []
    
    @staticmethod
    def get_dashboard_data_optimized(user_id: int) -> Dict[str, Any]:
        """Optimized dashboard data query"""
        try:
            # Use raw SQL for better performance
            sql = """
            SELECT 
                COUNT(*) as total_entries,
                COUNT(CASE WHEN DATE(created_at) = CURRENT_DATE THEN 1 END) as entries_today,
                COUNT(CASE WHEN created_at >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY) THEN 1 END) as entries_this_week,
                COUNT(CASE WHEN created_at >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY) THEN 1 END) as entries_this_month,
                MAX(created_at) as last_entry_date,
                (SELECT COUNT(*) FROM entries WHERE user_id = :user_id AND DATE(created_at) = CURRENT_DATE) as today_count
            FROM entries 
            WHERE user_id = :user_id
            """
            
            result = db.session.execute(sql, {'user_id': user_id}).fetchone()
            
            return {
                'total_entries': result.total_entries or 0,
                'entries_today': result.entries_today or 0,
                'entries_this_week': result.entries_this_week or 0,
                'entries_this_month': result.entries_this_month or 0,
                'last_entry_date': result.last_entry_date.isoformat() if result.last_entry_date else None,
                'today_count': result.today_count or 0
            }
            
        except Exception as e:
            logger.error(f"Optimized dashboard query error: {str(e)}")
            return {}
    
    @staticmethod
    def get_analytics_data_optimized(user_id: int, days: int = 30) -> Dict[str, Any]:
        """Optimized analytics data query"""
        try:
            # Use window functions for better performance
            sql = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as entry_count,
                AVG(word_count) as avg_word_count,
                mood,
                COUNT(*) OVER (PARTITION BY mood ORDER BY DATE(created_at)) as mood_streak
            FROM entries 
            WHERE user_id = :user_id 
                AND created_at >= DATE_SUB(CURRENT_DATE, INTERVAL :days DAY)
            GROUP BY DATE(created_at), mood
            ORDER BY date DESC
            """
            
            results = db.session.execute(sql, {'user_id': user_id, 'days': days}).fetchall()
            
            # Process results
            dates = []
            counts = []
            moods = {}
            
            for row in results:
                dates.append(row.date.isoformat())
                counts.append(row.entry_count)
                
                if row.mood:
                    if row.mood not in moods:
                        moods[row.mood] = []
                    moods[row.mood].append({
                        'date': row.date.isoformat(),
                        'count': row.entry_count,
                        'streak': row.mood_streak
                    })
            
            return {
                'dates': dates,
                'counts': counts,
                'moods': moods,
                'total_entries': sum(counts)
            }
            
        except Exception as e:
            logger.error(f"Optimized analytics query error: {str(e)}")
            return {}


class PerformanceMonitor:
    """Performance monitoring service"""
    
    def __init__(self):
        self.metrics = {}
        self.slow_queries = []
        self.cache_hits = 0
        self.cache_misses = 0
    
    def track_query_time(self, query: str, time_ms: float):
        """Track query execution time"""
        if time_ms > 1000:  # Slow query threshold
            self.slow_queries.append({
                'query': query[:100],  # Truncate for storage
                'time_ms': time_ms,
                'timestamp': datetime.utcnow().isoformat()
            })
            logger.warning(f"Slow query detected: {time_ms:.2f}ms - {query[:100]}")
    
    def track_cache_hit(self):
        """Track cache hit"""
        self.cache_hits += 1
    
    def track_cache_miss(self):
        """Track cache miss"""
        self.cache_misses += 1
    
    def get_cache_hit_ratio(self) -> float:
        """Get cache hit ratio"""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_ratio': self.get_cache_hit_ratio(),
            'slow_queries_count': len(self.slow_queries),
            'slow_queries': self.slow_queries[-10:],  # Last 10 slow queries
            'memory_usage': self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                'percent': process.memory_percent()
            }
        except ImportError:
            return {'error': 'psutil not installed'}
        except Exception as e:
            return {'error': str(e)}


# Decorators for caching
def cache_result(ttl: int = 3600, key_prefix: str = '', cache_user_specific: bool = True):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            
            if cache_user_specific and hasattr(current_user, 'id'):
                key_parts.append(str(current_user.id))
            
            # Add args and kwargs to key
            for arg in args:
                key_parts.append(str(arg))
            
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}:{v}")
            
            cache_key = hashlib.md5(':'.join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache_service.get(cache_key)
            
            if cached_result is not None:
                performance_monitor.track_cache_hit()
                return cached_result
            
            # Execute function and cache result
            performance_monitor.track_cache_miss()
            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_query(ttl: int = 3600, key_prefix: str = 'query'):
    """Decorator to cache database queries"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key based on function name and parameters
            key_data = f"{key_prefix}:{func.__name__}:{hashlib.md5(str(args + tuple(sorted(kwargs.items()))).encode()).hexdigest()}"
            
            cached_result = cache_service.get(key_data)
            
            if cached_result is not None:
                performance_monitor.track_cache_hit()
                return cached_result
            
            # Time the query
            start_time = datetime.utcnow()
            performance_monitor.track_cache_miss()
            
            result = func(*args, **kwargs)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            performance_monitor.track_query_time(str(func.__name__), execution_time)
            
            # Cache the result
            cache_service.set(key_data, result, ttl)
            
            return result
        
        return wrapper
    return decorator


class BackgroundTaskService:
    """Background task service for performance optimization"""
    
    def __init__(self):
        self.tasks = []
    
    def schedule_task(self, func: callable, *args, **kwargs):
        """Schedule a background task"""
        task = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'scheduled_at': datetime.utcnow(),
            'status': 'pending'
        }
        self.tasks.append(task)
        
        # In production, use Celery or Redis Queue
        # For now, execute immediately (simplified)
        self._execute_task(task)
    
    def _execute_task(self, task: Dict[str, Any]):
        """Execute a task"""
        try:
            task['status'] = 'running'
            task['started_at'] = datetime.utcnow()
            
            # Execute the function
            result = task['func'](*task['args'], **task['kwargs'])
            
            task['status'] = 'completed'
            task['completed_at'] = datetime.utcnow()
            task['result'] = result
            
        except Exception as e:
            task['status'] = 'failed'
            task['error'] = str(e)
            task['failed_at'] = datetime.utcnow()
            logger.error(f"Background task failed: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        for task in self.tasks:
            if task.get('id') == task_id:
                return task
        return None
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        self.tasks = [
            task for task in self.tasks
            if task['status'] in ['pending', 'running'] or 
            (task['status'] in ['completed', 'failed'] and 
             task.get('completed_at', task.get('failed_at', datetime.utcnow())) > cutoff_time)
        ]


# Initialize services
cache_service = CacheService()
query_optimizer = QueryOptimizer()
performance_monitor = PerformanceMonitor()
background_task_service = BackgroundTaskService()
