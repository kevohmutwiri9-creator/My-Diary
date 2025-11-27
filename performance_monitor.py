#!/usr/bin/env python3
"""
Performance Monitoring Script
Monitors application performance and provides optimization recommendations
"""

import os
import sys
import time
import psutil
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

class PerformanceMonitor:
    """Comprehensive performance monitoring"""
    
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.metrics = {}
        
    def test_endpoint_performance(self, endpoint, method="GET", data=None, iterations=3):
        """Test endpoint performance"""
        url = f"{self.base_url}{endpoint}"
        times = []
        status_codes = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                if method == "GET":
                    response = requests.get(url, timeout=10)
                elif method == "POST":
                    response = requests.post(url, data=data, timeout=10)
                
                duration = time.time() - start_time
                times.append(duration)
                status_codes.append(response.status_code)
                
                # Small delay between requests
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error testing {endpoint}: {e}")
                return None
        
        if times:
            return {
                'endpoint': endpoint,
                'method': method,
                'avg_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times),
                'status_codes': status_codes,
                'success_rate': sum(1 for code in status_codes if 200 <= code < 300) / len(status_codes) * 100
            }
        
        return None
    
    def check_system_resources(self):
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total / 1024 / 1024 / 1024,  # GB
                    'used': memory.used / 1024 / 1024 / 1024,   # GB
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk.total / 1024 / 1024 / 1024,    # GB
                    'used': disk.used / 1024 / 1024 / 1024,     # GB
                    'percent': disk.percent
                },
                'network': {
                    'bytes_sent': network.bytes_sent / 1024 / 1024,  # MB
                    'bytes_recv': network.bytes_recv / 1024 / 1024,  # MB
                }
            }
        except Exception as e:
            print(f"Error checking system resources: {e}")
            return {}
    
    def check_database_performance(self):
        """Check database performance"""
        try:
            from app import create_app, db
            from app.models.entry import Entry
            from app.models.user import User
            
            app = create_app()
            with app.app_context():
                # Test basic queries
                start_time = time.time()
                user_count = User.query.count()
                user_query_time = time.time() - start_time
                
                start_time = time.time()
                entry_count = Entry.query.count()
                entry_query_time = time.time() - start_time
                
                # Test complex query
                start_time = time.time()
                recent_entries = Entry.query.order_by(Entry.created_at.desc()).limit(10).all()
                complex_query_time = time.time() - start_time
                
                return {
                    'user_count': user_count,
                    'user_query_time': user_query_time,
                    'entry_count': entry_count,
                    'entry_query_time': entry_query_time,
                    'complex_query_time': complex_query_time,
                    'total_query_time': user_query_time + entry_query_time + complex_query_time
                }
        except Exception as e:
            print(f"Error checking database performance: {e}")
            return {}
    
    def check_cache_performance(self):
        """Check cache performance"""
        try:
            from app import create_app
            from flask_caching import Cache
            
            app = create_app()
            with app.app_context():
                cache = Cache()
                
                # Test cache set/get
                test_key = f"perf_test_{int(time.time())}"
                test_value = {"data": "test", "timestamp": time.time()}
                
                start_time = time.time()
                cache.set(test_key, test_value, timeout=60)
                set_time = time.time() - start_time
                
                start_time = time.time()
                retrieved_value = cache.get(test_key)
                get_time = time.time() - start_time
                
                # Clean up
                cache.delete(test_key)
                
                return {
                    'cache_available': True,
                    'set_time': set_time,
                    'get_time': get_time,
                    'total_time': set_time + get_time,
                    'cache_hit': retrieved_value is not None
                }
        except Exception as e:
            print(f"Error checking cache performance: {e}")
            return {'cache_available': False}
    
    def analyze_log_files(self):
        """Analyze log files for performance issues"""
        log_data = {
            'error_count': 0,
            'warning_count': 0,
            'slow_requests': 0,
            'total_requests': 0
        }
        
        try:
            # Check main log file
            if os.path.exists('logs/my_diary.log'):
                with open('logs/my_diary.log', 'r') as f:
                    lines = f.readlines()
                    
                    for line in lines[-1000:]:  # Last 1000 lines
                        if 'ERROR' in line:
                            log_data['error_count'] += 1
                        elif 'WARNING' in line:
                            log_data['warning_count'] += 1
                        elif 'Slow request' in line:
                            log_data['slow_requests'] += 1
                        if 'Request:' in line:
                            log_data['total_requests'] += 1
            
            # Check performance log file
            if os.path.exists('logs/performance.log'):
                with open('logs/performance.log', 'r') as f:
                    lines = f.readlines()
                    
                    for line in lines[-1000:]:
                        if 'Slow request' in line:
                            log_data['slow_requests'] += 1
            
            # Check security log file
            if os.path.exists('logs/security.log'):
                with open('logs/security.log', 'r') as f:
                    lines = f.readlines()
                    
                    for line in lines[-1000:]:
                        if 'WARNING' in line:
                            log_data['warning_count'] += 1
            
        except Exception as e:
            print(f"Error analyzing log files: {e}")
        
        return log_data
    
    def generate_recommendations(self, metrics):
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # System resource recommendations
        system = metrics.get('system', {})
        if system.get('cpu_percent', 0) > 80:
            recommendations.append("High CPU usage detected. Consider optimizing queries or scaling up.")
        
        if system.get('memory', {}).get('percent', 0) > 85:
            recommendations.append("High memory usage detected. Check for memory leaks or optimize data structures.")
        
        if system.get('disk', {}).get('percent', 0) > 90:
            recommendations.append("Low disk space. Clean up old logs and temporary files.")
        
        # Database recommendations
        db = metrics.get('database', {})
        if db.get('total_query_time', 0) > 1.0:
            recommendations.append("Slow database queries detected. Consider adding indexes or optimizing queries.")
        
        if db.get('entry_count', 0) > 10000 and db.get('complex_query_time', 0) > 0.5:
            recommendations.append("Large dataset detected. Consider implementing pagination and query optimization.")
        
        # Cache recommendations
        cache = metrics.get('cache', {})
        if not cache.get('cache_available', False):
            recommendations.append("Cache not available. Consider setting up Redis for better performance.")
        elif cache.get('total_time', 0) > 0.1:
            recommendations.append("Cache operations are slow. Check Redis configuration and network latency.")
        
        # Log recommendations
        logs = metrics.get('logs', {})
        if logs.get('error_count', 0) > 10:
            recommendations.append("High error count in logs. Review and fix application errors.")
        
        if logs.get('slow_requests', 0) > logs.get('total_requests', 1) * 0.1:
            recommendations.append("Many slow requests detected. Profile application and optimize bottlenecks.")
        
        return recommendations
    
    def run_comprehensive_test(self):
        """Run comprehensive performance test"""
        print("🚀 Performance Monitoring Suite")
        print("=" * 50)
        print(f"Testing URL: {self.base_url}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Test endpoint performance
        print("\n📊 Testing Endpoint Performance")
        print("-" * 40)
        
        endpoints = [
            ('/', 'GET'),
            ('/dashboard', 'GET'),
            ('/auth/login', 'GET'),
            ('/auth/register', 'GET'),
        ]
        
        endpoint_results = []
        for endpoint, method in endpoints:
            result = self.test_endpoint_performance(endpoint, method)
            if result:
                endpoint_results.append(result)
                print(f"✅ {method} {endpoint}: {result['avg_time']:.3f}s avg")
            else:
                print(f"❌ {method} {endpoint}: Failed")
        
        # Check system resources
        print("\n🖥️ System Resources")
        print("-" * 40)
        system_data = self.check_system_resources()
        if system_data:
            print(f"CPU Usage: {system_data['cpu_percent']:.1f}%")
            print(f"Memory Usage: {system_data['memory']['percent']:.1f}% ({system_data['memory']['used']:.1f}GB/{system_data['memory']['total']:.1f}GB)")
            print(f"Disk Usage: {system_data['disk']['percent']:.1f}%")
        
        # Check database performance
        print("\n🗄️ Database Performance")
        print("-" * 40)
        db_data = self.check_database_performance()
        if db_data:
            print(f"User Count: {db_data['user_count']}")
            print(f"Entry Count: {db_data['entry_count']}")
            print(f"Query Times: User={db_data['user_query_time']:.3f}s, Entry={db_data['entry_query_time']:.3f}s, Complex={db_data['complex_query_time']:.3f}s")
        
        # Check cache performance
        print("\n💾 Cache Performance")
        print("-" * 40)
        cache_data = self.check_cache_performance()
        if cache_data:
            if cache_data['cache_available']:
                print(f"Cache Available: ✅")
                print(f"Set Time: {cache_data['set_time']:.3f}s")
                print(f"Get Time: {cache_data['get_time']:.3f}s")
            else:
                print("Cache Available: ❌")
        
        # Analyze logs
        print("\n📋 Log Analysis")
        print("-" * 40)
        log_data = self.analyze_log_files()
        print(f"Errors: {log_data['error_count']}")
        print(f"Warnings: {log_data['warning_count']}")
        print(f"Slow Requests: {log_data['slow_requests']}")
        print(f"Total Requests: {log_data['total_requests']}")
        
        # Generate recommendations
        print("\n💡 Optimization Recommendations")
        print("-" * 40)
        
        all_metrics = {
            'system': system_data,
            'database': db_data,
            'cache': cache_data,
            'logs': log_data
        }
        
        recommendations = self.generate_recommendations(all_metrics)
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("✅ No performance issues detected!")
        
        # Summary
        print("\n" + "=" * 50)
        print("📈 Performance Summary")
        print("=" * 50)
        
        avg_response_time = sum(r['avg_time'] for r in endpoint_results) / len(endpoint_results) if endpoint_results else 0
        print(f"Average Response Time: {avg_response_time:.3f}s")
        print(f"System CPU: {system_data.get('cpu_percent', 0):.1f}%")
        print(f"System Memory: {system_data.get('memory', {}).get('percent', 0):.1f}%")
        print(f"Database Query Time: {db_data.get('total_query_time', 0):.3f}s")
        print(f"Cache Available: {'✅' if cache_data.get('cache_available') else '❌'}")
        
        return {
            'endpoint_results': endpoint_results,
            'system': system_data,
            'database': db_data,
            'cache': cache_data,
            'logs': log_data,
            'recommendations': recommendations
        }

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor My Diary performance')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL to test')
    parser.add_argument('--output', help='Output results to JSON file')
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(args.url)
    results = monitor.run_comprehensive_test()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📁 Results saved to {args.output}")
    
    print(f"\n🎉 Performance monitoring completed!")
