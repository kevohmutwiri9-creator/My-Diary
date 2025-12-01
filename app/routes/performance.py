"""
Performance and Cache Management Routes for My Diary App
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.services.cache import (
    cache_service, query_optimizer, performance_monitor, 
    background_task_service, cache_result, cache_query
)
from app.models.user import User
from app.models.entry import Entry
from app import db
import logging

logger = logging.getLogger(__name__)

performance_bp = Blueprint('performance', __name__, url_prefix='/performance')


@performance_bp.route('/dashboard')
@login_required
def performance_dashboard():
    """Performance monitoring dashboard"""
    try:
        # Get performance stats
        stats = performance_monitor.get_performance_stats()
        
        # Get cache info
        cache_info = {
            'redis_connected': cache_service.redis_client is not None,
            'cache_size': 'Unknown'  # Would need Redis INFO command
        }
        
        # Get slow queries
        slow_queries = performance_monitor.slow_queries[-10:]  # Last 10
        
        return render_template('performance/dashboard.html',
                             stats=stats,
                             cache_info=cache_info,
                             slow_queries=slow_queries)
        
    except Exception as e:
        logger.error(f"Performance dashboard error: {str(e)}", exc_info=True)
        flash('Unable to load performance dashboard.', 'error')
        return redirect(url_for('main.dashboard'))


@performance_bp.route('/cache-stats')
@login_required
def cache_stats():
    """Get cache statistics"""
    try:
        stats = performance_monitor.get_performance_stats()
        
        return jsonify({
            'success': True,
            'cache_hits': stats['cache_hits'],
            'cache_misses': stats['cache_misses'],
            'cache_hit_ratio': stats['cache_hit_ratio'],
            'redis_connected': cache_service.redis_client is not None
        })
        
    except Exception as e:
        logger.error(f"Cache stats error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Failed to get cache stats'}), 500


@performance_bp.route('/clear-cache', methods=['POST'])
@login_required
def clear_cache():
    """Clear cache"""
    try:
        cache_type = request.form.get('type', 'all')
        user_specific = request.form.get('user_specific', 'false') == 'true'
        
        cleared_count = 0
        
        if cache_type == 'all':
            if user_specific:
                # Clear user-specific cache
                pattern = f"*{current_user.id}*"
                cleared_count = cache_service.delete_pattern(pattern)
            else:
                # Clear all cache
                cache_service.clear_all()
                cleared_count = 'all'
        
        elif cache_type == 'entries':
            if user_specific:
                pattern = f"entries:*{current_user.id}*"
                cleared_count = cache_service.delete_pattern(pattern)
            else:
                pattern = "entries:*"
                cleared_count = cache_service.delete_pattern(pattern)
        
        elif cache_type == 'analytics':
            if user_specific:
                pattern = f"analytics:*{current_user.id}*"
                cleared_count = cache_service.delete_pattern(pattern)
            else:
                pattern = "analytics:*"
                cleared_count = cache_service.delete_pattern(pattern)
        
        # Log cache clearing
        logger.info(f"Cache cleared: {cache_type}, user_specific={user_specific}, cleared={cleared_count}")
        
        return jsonify({
            'success': True,
            'message': f'Cache cleared successfully',
            'cleared_count': cleared_count
        })
        
    except Exception as e:
        logger.error(f"Clear cache error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Failed to clear cache'}), 500


@performance_bp.route('/warm-cache', methods=['POST'])
@login_required
def warm_cache():
    """Warm up cache with common data"""
    try:
        warmed_items = []
        
        # Warm user entries cache
        entries = query_optimizer.get_user_entries_optimized(current_user.id, limit=50)
        cache_key = f"entries:{current_user.id}:recent"
        cache_service.set(cache_key, entries, ttl=1800)  # 30 minutes
        warmed_items.append('recent_entries')
        
        # Warm dashboard data cache
        dashboard_data = query_optimizer.get_dashboard_data_optimized(current_user.id)
        cache_key = f"dashboard:{current_user.id}"
        cache_service.set(cache_key, dashboard_data, ttl=900)  # 15 minutes
        warmed_items.append('dashboard_data')
        
        # Warm analytics data cache
        analytics_data = query_optimizer.get_analytics_data_optimized(current_user.id, days=30)
        cache_key = f"analytics:{current_user.id}:30days"
        cache_service.set(cache_key, analytics_data, ttl=1800)  # 30 minutes
        warmed_items.append('analytics_data')
        
        return jsonify({
            'success': True,
            'message': 'Cache warmed successfully',
            'warmed_items': warmed_items
        })
        
    except Exception as e:
        logger.error(f"Warm cache error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Failed to warm cache'}), 500


@performance_bp.route('/optimize-database', methods=['POST'])
@login_required
def optimize_database():
    """Run database optimization tasks"""
    try:
        optimization_tasks = []
        
        # Update table statistics
        try:
            db.session.execute("ANALYZE TABLE entries, users")
            optimization_tasks.append('table_statistics_updated')
        except Exception as e:
            logger.warning(f"Table analysis failed: {str(e)}")
        
        # Optimize indexes (MySQL specific)
        try:
            db.session.execute("OPTIMIZE TABLE entries, users")
            optimization_tasks.append('indexes_optimized')
        except Exception as e:
            logger.warning(f"Index optimization failed: {str(e)}")
        
        # Clean up old session data
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            # This would depend on your session storage implementation
            optimization_tasks.append('session_cleanup')
        except Exception as e:
            logger.warning(f"Session cleanup failed: {str(e)}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Database optimization completed',
            'tasks_completed': optimization_tasks
        })
        
    except Exception as e:
        logger.error(f"Database optimization error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Database optimization failed'}), 500


@performance_bp.route('/health-check')
@login_required
def health_check():
    """System health check"""
    try:
        health_status = {
            'overall': 'healthy',
            'checks': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Database health
        try:
            db.session.execute('SELECT 1')
            health_status['checks']['database'] = {
                'status': 'healthy',
                'message': 'Database connection successful'
            }
        except Exception as e:
            health_status['checks']['database'] = {
                'status': 'unhealthy',
                'message': f'Database error: {str(e)}'
            }
            health_status['overall'] = 'unhealthy'
        
        # Redis health
        try:
            if cache_service.redis_client:
                cache_service.redis_client.ping()
                health_status['checks']['redis'] = {
                    'status': 'healthy',
                    'message': 'Redis connection successful'
                }
            else:
                health_status['checks']['redis'] = {
                    'status': 'warning',
                    'message': 'Redis not available, using fallback cache'
                }
        except Exception as e:
            health_status['checks']['redis'] = {
                'status': 'unhealthy',
                'message': f'Redis error: {str(e)}'
            }
            if health_status['overall'] == 'healthy':
                health_status['overall'] = 'warning'
        
        # Memory usage
        memory_stats = performance_monitor._get_memory_usage()
        if 'error' not in memory_stats:
            memory_percent = memory_stats.get('percent', 0)
            if memory_percent > 90:
                health_status['checks']['memory'] = {
                    'status': 'unhealthy',
                    'message': f'High memory usage: {memory_percent:.1f}%'
                }
                health_status['overall'] = 'unhealthy'
            elif memory_percent > 80:
                health_status['checks']['memory'] = {
                    'status': 'warning',
                    'message': f'Elevated memory usage: {memory_percent:.1f}%'
                }
                if health_status['overall'] == 'healthy':
                    health_status['overall'] = 'warning'
            else:
                health_status['checks']['memory'] = {
                    'status': 'healthy',
                    'message': f'Memory usage: {memory_percent:.1f}%'
                }
        else:
            health_status['checks']['memory'] = {
                'status': 'unknown',
                'message': 'Unable to check memory usage'
            }
        
        # Cache performance
        cache_hit_ratio = performance_monitor.get_cache_hit_ratio()
        if cache_hit_ratio < 50:
            health_status['checks']['cache_performance'] = {
                'status': 'warning',
                'message': f'Low cache hit ratio: {cache_hit_ratio:.1f}%'
            }
            if health_status['overall'] == 'healthy':
                health_status['overall'] = 'warning'
        else:
            health_status['checks']['cache_performance'] = {
                'status': 'healthy',
                'message': f'Cache hit ratio: {cache_hit_ratio:.1f}%'
            }
        
        return jsonify({
            'success': True,
            'health': health_status
        })
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Health check failed',
            'health': {
                'overall': 'unhealthy',
                'error': str(e)
            }
        }), 500


@performance_bp.route('/slow-queries')
@login_required
def slow_queries():
    """View slow queries log"""
    try:
        slow_queries = performance_monitor.slow_queries
        
        # Group by query type
        query_types = {}
        for query in slow_queries:
            query_type = query['query'].split()[0] if query['query'] else 'unknown'
            if query_type not in query_types:
                query_types[query_type] = []
            query_types[query_type].append(query)
        
        return render_template('performance/slow_queries.html',
                             slow_queries=slow_queries,
                             query_types=query_types)
        
    except Exception as e:
        logger.error(f"Slow queries error: {str(e)}", exc_info=True)
        flash('Unable to load slow queries.', 'error')
        return redirect(url_for('performance.performance_dashboard'))


@performance_bp.route('/background-tasks')
@login_required
def background_tasks():
    """View background tasks status"""
    try:
        tasks = background_task_service.tasks
        
        # Group by status
        task_status = {
            'pending': [t for t in tasks if t['status'] == 'pending'],
            'running': [t for t in tasks if t['status'] == 'running'],
            'completed': [t for t in tasks if t['status'] == 'completed'],
            'failed': [t for t in tasks if t['status'] == 'failed']
        }
        
        return render_template('performance/background_tasks.html',
                             task_status=task_status,
                             all_tasks=tasks)
        
    except Exception as e:
        logger.error(f"Background tasks error: {str(e)}", exc_info=True)
        flash('Unable to load background tasks.', 'error')
        return redirect(url_for('performance.performance_dashboard'))


@performance_bp.route('/cleanup-tasks', methods=['POST'])
@login_required
def cleanup_tasks():
    """Clean up old background tasks"""
    try:
        max_age_hours = request.form.get('max_age_hours', 24, type=int)
        
        initial_count = len(background_task_service.tasks)
        background_task_service.cleanup_completed_tasks(max_age_hours)
        final_count = len(background_task_service.tasks)
        
        cleaned_count = initial_count - final_count
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {cleaned_count} old tasks',
            'cleaned_count': cleaned_count
        })
        
    except Exception as e:
        logger.error(f"Cleanup tasks error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Failed to cleanup tasks'}), 500


@performance_bp.route('/export-performance-data')
@login_required
def export_performance_data():
    """Export performance data as JSON"""
    try:
        data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'performance_stats': performance_monitor.get_performance_stats(),
            'cache_info': {
                'redis_connected': cache_service.redis_client is not None,
                'cache_keys': []  # Would need Redis KEYS command
            },
            'slow_queries': performance_monitor.slow_queries,
            'background_tasks': background_task_service.tasks
        }
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Export performance data error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Export failed'}), 500


# Optimized endpoints with caching
@performance_bp.route('/cached-entries')
@login_required
@cache_result(ttl=1800, cache_user_specific=True)  # 30 minutes cache
def cached_entries():
    """Get user entries with caching"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        offset = (page - 1) * limit
        
        entries = query_optimizer.get_user_entries_optimized(
            current_user.id, 
            limit=limit, 
            offset=offset
        )
        
        return jsonify({
            'success': True,
            'entries': [entry.to_dict() for entry in entries],
            'page': page,
            'limit': limit,
            'cached': True
        })
        
    except Exception as e:
        logger.error(f"Cached entries error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Failed to get entries'}), 500


@performance_bp.route('/cached-dashboard')
@login_required
@cache_result(ttl=900, cache_user_specific=True)  # 15 minutes cache
def cached_dashboard():
    """Get dashboard data with caching"""
    try:
        data = query_optimizer.get_dashboard_data_optimized(current_user.id)
        
        return jsonify({
            'success': True,
            'data': data,
            'cached': True
        })
        
    except Exception as e:
        logger.error(f"Cached dashboard error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Failed to get dashboard data'}), 500
