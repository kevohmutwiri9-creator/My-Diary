#!/usr/bin/env python3
"""
Database Health Check and Optimization Script
This script checks database health, performance, and optimizes queries
"""

import os
import sys
import time
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

def check_database_health():
    """Comprehensive database health check"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///my_diary.db'
    
    print("Database Health Check")
    print(f"Database URL: {database_url.split('///')[-1] if '///' in database_url else database_url}")
    print("=" * 50)
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Test basic connection
        print("1. Testing database connection...")
        start_time = time.time()
        with engine.connect() as conn:
            if 'sqlite' in database_url:
                result = conn.execute(text("SELECT sqlite_version()"))
            elif 'postgresql' in database_url:
                result = conn.execute(text("SELECT version()"))
            else:
                result = conn.execute(text("SELECT 1"))
            version = result.fetchone()[0]
        connection_time = time.time() - start_time
        print(f"Connection successful ({connection_time:.3f}s)")
        print(f"Database version: {str(version).split('\\n')[0] if '\\n' in str(version) else version}")
        
        # Check tables
        print("\n2. Checking database tables...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # Check table sizes
        print("\n3. Analyzing table sizes...")
        with engine.connect() as conn:
            for table in tables:
                if 'sqlite' in database_url:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                else:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                print(f"{table}: {count:,} records")
        
        # Check indexes
        print("\n4. Checking database indexes...")
        with engine.connect() as conn:
            for table in tables:
                indexes = inspector.get_indexes(table)
                if indexes:
                    print(f"{table}: {len(indexes)} indexes")
                    for idx in indexes:
                        print(f"   - {idx['name']}: {', '.join(idx['column_names'])}")
        
        # Performance test
        print("\n5. Running performance tests...")
        with engine.connect() as conn:
            # Test common queries
            queries = [
                ("User count", "SELECT COUNT(*) FROM users"),
                ("Entry count", "SELECT COUNT(*) FROM entries"),
                ("Recent entries", "SELECT COUNT(*) FROM entries WHERE created_at > datetime('now', '-7 days')" if 'sqlite' in database_url else 
                "SELECT COUNT(*) FROM entries WHERE created_at > DATEADD(day, -7, GETDATE())" if 'mssql' in database_url else
                "SELECT COUNT(*) FROM entries WHERE created_at > NOW() - INTERVAL '7 days'")
            ]
            
            for query_name, query in queries:
                start_time = time.time()
                try:
                    result = conn.execute(text(query))
                    count = result.fetchone()[0]
                    query_time = time.time() - start_time
                    print(f"{query_name}: {count:,} results ({query_time:.3f}s)")
                except Exception as e:
                    print(f"{query_name}: ERROR - {e}")
        
        # Check for potential issues
        print("\n6. Checking for potential issues...")
        
        # Check for missing indexes on foreign keys
        with engine.connect() as conn:
            if 'entries' in tables:
                # Check if entries.user_id has an index
                try:
                    if 'sqlite' in database_url:
                        result = conn.execute(text("EXPLAIN QUERY PLAN SELECT * FROM entries WHERE user_id = 1"))
                        plan = result.fetchall()
                        has_index = any('USING INDEX' in str(row) for row in plan)
                    elif 'mssql' in database_url:
                        # SQL Server check
                        result = conn.execute(text("""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('entries') AND name LIKE '%user_id%'
                        """))
                        has_index = result.fetchone()[0] > 0
                    else:
                        # PostgreSQL check
                        result = conn.execute(text("""
                            SELECT COUNT(*) FROM pg_indexes 
                            WHERE tablename = 'entries' AND indexdef LIKE '%user_id%'
                        """))
                        has_index = result.fetchone()[0] > 0
                    
                    if has_index:
                        print("entries.user_id is indexed")
                    else:
                        print("WARNING: entries.user_id may need an index for better performance")
                except Exception as e:
                    print(f"Could not check entries.user_id index: {e}")
        
        # Recommendations
        print("\n7. Optimization Recommendations:")
        recommendations = []
        
        # Check if database is SQLite
        if 'sqlite' in database_url:
            recommendations.append("Consider migrating to PostgreSQL for better performance")
            recommendations.append("Run VACUUM command to optimize SQLite database")
        
        # Check table sizes
        with engine.connect() as conn:
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                if count > 10000:
                    recommendations.append(f"Consider archiving old {table} records (>{count:,})")
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("No specific recommendations at this time")
        
        print("\n" + "=" * 50)
        print("Database health check completed!")
        
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False
    
    return True

def optimize_database():
    """Apply database optimizations"""
    
    database_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///my_diary.db'
    
    print("Database Optimization")
    print("=" * 30)
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            if 'sqlite' in database_url:
                print("Cleaning up SQLite database...")
                # SQLite optimizations
                optimizations = [
                    ("VACUUM", "Reclaim unused space"),
                    ("ANALYZE", "Update query planner statistics"),
                    ("PRAGMA optimize", "Automatic optimization")
                ]
                
                for cmd, desc in optimizations:
                    try:
                        start_time = time.time()
                        conn.execute(text(cmd))
                        conn.commit()
                        opt_time = time.time() - start_time
                        print(f"{desc} ({opt_time:.3f}s)")
                    except Exception as e:
                        print(f"{desc} failed: {e}")
            
            elif 'mssql' in database_url:
                print("Cleaning up SQL Server database...")
                # SQL Server optimizations
                optimizations = [
                    ("UPDATE STATISTICS entries", "Update table statistics"),
                    ("UPDATE STATISTICS users", "Update user statistics"),
                    ("UPDATE STATISTICS tags", "Update tag statistics")
                ]
                
                for cmd, desc in optimizations:
                    try:
                        start_time = time.time()
                        conn.execute(text(cmd))
                        conn.commit()
                        opt_time = time.time() - start_time
                        print(f"{desc} ({opt_time:.3f}s)")
                    except Exception as e:
                        print(f"{desc} failed: {e}")
        
        print("\nDatabase optimization completed!")
        
    except Exception as e:
        print(f"Database optimization failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Database health check and optimization')
    parser.add_argument('--optimize', action='store_true', help='Apply optimizations')
    args = parser.parse_args()
    
    # Run health check
    if check_database_health():
        if args.optimize:
            optimize_database()
    else:
        print("Cannot proceed with optimization due to health check failures")
        sys.exit(1)
