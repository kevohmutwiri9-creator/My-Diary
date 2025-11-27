"""
Performance Optimization System
Provides comprehensive performance monitoring and optimization
"""

import time
import functools
import logging
from datetime import datetime, timedelta
from flask import current_app, request, g
from flask_login import current_user
from typing import Dict, List, Any, Optional

# Optional Redis dependency
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

import json

class PerformanceOptimizer:
    """Comprehensive performance optimization system"""
    
    def __init__(self, app=None):
        self.app = app
        self.redis_client = None
        self.metrics = {}
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize performance optimization features"""
        # Setup Redis if available
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(
                    app.config.get('REDIS_URL', 'redis://localhost:6379'),
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                app.logger.info("Redis connected for performance optimization")
            except Exception as e:
                app.logger.warning(f"Redis not available for performance optimization: {e}")
                self.redis_client = None
        else:
            app.logger.info("Redis not installed, using in-memory caching")
            self.redis_client = None
        
        # Add performance monitoring to all requests
        @app.before_request
        def before_request():
            g.start_time = time.time()
            g.request_id = self.generate_request_id()
        
        @app.after_request
        def after_request(response):
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                self.record_request_metric(
                    endpoint=request.endpoint,
                    method=request.method,
                    status_code=response.status_code,
                    duration=duration,
                    user_id=current_user.id if current_user.is_authenticated else None
                )
            
            # Add performance headers
            response.headers['X-Response-Time'] = f"{getattr(g, 'start_time', 0) and (time.time() - g.start_time):.3f}s"
            return response
        
        # Setup performance logging
        self.setup_performance_logging(app)
    
    def setup_performance_logging(self, app):
        """Setup performance-specific logging"""
        perf_logger = logging.getLogger('performance')
        
        if not perf_logger.handlers:
            handler = logging.FileHandler('logs/performance.log')
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - PERF - %(levelname)s - %(message)s'
            ))
            perf_logger.addHandler(handler)
            perf_logger.setLevel(logging.INFO)
        
        app.performance_logger = perf_logger
    
    def generate_request_id(self):
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def record_request_metric(self, endpoint, method, status_code, duration, user_id=None):
        """Record request performance metrics"""
        metric = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration': duration,
            'user_id': user_id,
            'ip': request.remote_addr
        }
        
        # Store in Redis if available, otherwise use in-memory storage
        if self.redis_client:
            key = f"perf:{endpoint}:{method}"
            self.redis_client.lpush(key, json.dumps(metric))
            self.redis_client.expire(key, 3600)  # Keep 1 hour of data
        else:
            # Fallback to in-memory storage (not persistent)
            if not hasattr(self, '_memory_cache'):
                self._memory_cache = {}
            key = f"perf:{endpoint}:{method}"
            if key not in self._memory_cache:
                self._memory_cache[key] = []
            self._memory_cache[key].append(metric)
            # Keep only last 100 items in memory
            if len(self._memory_cache[key]) > 100:
                self._memory_cache[key] = self._memory_cache[key][-100:]
        
        # Log slow requests
        if duration > 2.0:  # Requests over 2 seconds
            if hasattr(current_app, 'performance_logger'):
                current_app.performance_logger.warning(
                    f"Slow request: {method} {endpoint} - {duration:.3f}s"
                )
    
    def get_performance_stats(self, endpoint=None, hours=1):
        """Get performance statistics"""
        stats = {}
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        if endpoint:
            endpoints = [endpoint]
        else:
            # Get all endpoints from cache
            endpoints = []
            if self.redis_client:
                for key in self.redis_client.scan_iter("perf:*"):
                    parts = key.decode().split(':') if isinstance(key, bytes) else key.split(':')
                    if len(parts) >= 3:
                        endpoints.append(parts[-2])
            elif hasattr(self, '_memory_cache'):
                for key in self._memory_cache.keys():
                    parts = key.split(':')
                    if len(parts) >= 3:
                        endpoints.append(parts[-2])
        
        for ep in endpoints:
            for method in ['GET', 'POST', 'PUT', 'DELETE']:
                key = f"perf:{ep}:{method}"
                data = []
                
                if self.redis_client:
                    try:
                        raw_data = self.redis_client.lrange(key, 0, -1)
                        data = [json.loads(item) for item in raw_data]
                    except:
                        continue
                elif hasattr(self, '_memory_cache') and key in self._memory_cache:
                    data = self._memory_cache[key]
                
                if data:
                    durations = []
                    status_codes = {}
                    
                    for item in data:
                        try:
                            metric_time = datetime.fromisoformat(item['timestamp'])
                            
                            if metric_time >= start_time:
                                durations.append(item['duration'])
                                status_code = item['status_code']
                                status_codes[status_code] = status_codes.get(status_code, 0) + 1
                        except:
                            continue
                    
                    if durations:
                        stats[f"{ep}:{method}"] = {
                            'count': len(durations),
                            'avg_duration': sum(durations) / len(durations),
                            'min_duration': min(durations),
                            'max_duration': max(durations),
                            'status_codes': status_codes
                        }
        
        return stats

# Query Optimization
class QueryOptimizer:
    """Database query optimization"""
    
    @staticmethod
    def optimize_query(query, limit=None, offset=None):
        """Optimize database query"""
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        return query
    
    @staticmethod
    def cache_query_result(cache_key, query_func, timeout=300):
        """Cache query results"""
        def wrapper(*args, **kwargs):
            from flask import current_app
            cache = current_app.extensions.get('cache')
            
            if cache:
                result = cache.get(cache_key)
                if result is not None:
                    return result
            
            result = query_func(*args, **kwargs)
            
            if cache:
                cache.set(cache_key, result, timeout=timeout)
            
            return result
        
        return wrapper

# Response Caching
class ResponseCache:
    """Response caching system"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize response caching"""
        self.cache = app.extensions.get('cache')
    
    def cache_response(self, timeout=300, key_func=None):
        """Decorator for caching responses"""
        def decorator(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                if not self.cache:
                    return f(*args, **kwargs)
                
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"response:{request.endpoint}:{request.url}"
                
                # Try to get cached response
                cached_response = self.cache.get(cache_key)
                if cached_response is not None:
                    return cached_response
                
                # Generate and cache response
                response = f(*args, **kwargs)
                self.cache.set(cache_key, response, timeout=timeout)
                
                return response
            
            return decorated_function
        return decorator

# Asset Optimization
class AssetOptimizer:
    """Static asset optimization"""
    
    @staticmethod
    def get_asset_version(asset_path):
        """Get asset version for cache busting"""
        try:
            import os
            full_path = os.path.join(current_app.static_folder, asset_path.lstrip('/'))
            if os.path.exists(full_path):
                mtime = os.path.getmtime(full_path)
                return int(mtime)
        except:
            pass
        return 1
    
    @staticmethod
    def get_asset_url(asset_path):
        """Get versioned asset URL"""
        version = AssetOptimizer.get_asset_version(asset_path)
        if version > 1:
            return f"{asset_path}?v={version}"
        return asset_path

# Database Connection Pooling
class ConnectionPoolOptimizer:
    """Database connection pooling optimization"""
    
    @staticmethod
    def get_optimized_engine(database_url, pool_size=10, max_overflow=20):
        """Get optimized database engine"""
        from sqlalchemy import create_engine
        from sqlalchemy.pool import QueuePool
        
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
            echo=False  # Disable SQL logging in production
        )
        
        return engine

# Memory Optimization
class MemoryOptimizer:
    """Memory usage optimization"""
    
    @staticmethod
    def monitor_memory_usage():
        """Monitor memory usage"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'vms': memory_info.vms / 1024 / 1024,  # MB
                'percent': process.memory_percent()
            }
        except ImportError:
            return {}
    
    @staticmethod
    def optimize_large_objects(obj):
        """Optimize large objects in memory"""
        if hasattr(obj, '__dict__'):
            # Clear unnecessary attributes
            for attr in list(obj.__dict__.keys()):
                if attr.startswith('_'):
                    delattr(obj, attr)
        
        return obj

# Performance Monitoring Decorators
def monitor_performance(threshold=2.0):
    """Monitor function performance"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                
                if duration > threshold:
                    if hasattr(current_app, 'performance_logger'):
                        current_app.performance_logger.warning(
                            f"Slow function: {f.__name__} - {duration:.3f}s"
                        )
                
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                if hasattr(current_app, 'performance_logger'):
                    current_app.performance_logger.error(
                        f"Function error: {f.__name__} - {duration:.3f}s - {str(e)}"
                    )
                raise
        
        return decorated_function
    return decorator

def cache_function_result(timeout=300, key_func=None):
    """Cache function results"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import current_app
            cache = current_app.extensions.get('cache')
            
            if not cache:
                return f(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"func:{f.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get cached result
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Generate and cache result
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            
            return result
        
        return decorated_function
    return decorator

# Lazy Loading
class LazyLoader:
    """Lazy loading for expensive operations"""
    
    def __init__(self, load_func, *args, **kwargs):
        self.load_func = load_func
        self.args = args
        self.kwargs = kwargs
        self._loaded = False
        self._value = None
    
    def get_value(self):
        """Get loaded value"""
        if not self._loaded:
            self._value = self.load_func(*self.args, **self.kwargs)
            self._loaded = True
        
        return self._value
    
    def __call__(self):
        return self.get_value()

# Pagination Optimization
class PaginationOptimizer:
    """Optimized pagination"""
    
    @staticmethod
    def get_paginated_query(query, page, per_page=20, max_per_page=100):
        """Get optimized paginated query"""
        # Validate per_page
        per_page = min(max(per_page, 1), max_per_page)
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get total count efficiently
        total = query.count()
        
        # Apply pagination
        items = query.offset(offset).limit(per_page).all()
        
        return {
            'items': items,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'current_page': page,
            'per_page': per_page,
            'has_prev': page > 1,
            'has_next': page * per_page < total
        }

# Initialize performance optimizer
performance_optimizer = PerformanceOptimizer()
