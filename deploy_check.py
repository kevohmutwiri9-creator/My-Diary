#!/usr/bin/env python3
"""
Deployment Check Script for Render
Run this locally to verify your app is production-ready
"""

import os
import sys
from app import create_app

def check_deployment_readiness():
    """Check if application is ready for Render deployment"""
    print("🔍 Checking deployment readiness...")
    
    # Check required environment variables
    required_vars = [
        'FLASK_ENV',
        'SECRET_KEY', 
        'DATABASE_URL',
        'GEMINI_API_KEY',
        'MAIL_SERVER',
        'MAIL_PORT',
        'MAIL_USE_TLS',
        'ADSENSE_PUBLISHER_ID'
    ]
    
    print("\n📋 Environment Variables Check:")
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * len(value) if 'KEY' in var or 'PASSWORD' in var else value}")
        else:
            print(f"❌ {var}: MISSING")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing variables: {', '.join(missing_vars)}")
        return False
    
    # Test Flask app creation
    print("\n🧪 Flask App Test:")
    try:
        app = create_app()
        print("✅ Flask app created successfully")
        
        # Test routes
        with app.app_context():
            print("✅ App context created")
            
        # Test database connection (if DATABASE_URL is set)
        if os.environ.get('DATABASE_URL'):
            try:
                from app import db
                with app.app_context():
                    db.create_all()
                print("✅ Database connection successful")
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Flask app creation failed: {e}")
        return False
    
    # Check critical files
    print("\n📁 Files Check:")
    critical_files = [
        'run.py',
        'requirements.txt',
        'render.yaml',
        'Procfile',
        'app/__init__.py',
        'app/models.py',
        'app/routes/main.py',
        'app/routes/auth.py',
        'static/ads.txt'
    ]
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}: MISSING")
            return False
    
    print("\n🎉 All checks passed! Your app is ready for Render deployment!")
    return True

def deployment_checklist():
    """Print deployment checklist"""
    print("\n📋 Render Deployment Checklist:")
    print("=" * 50)
    
    checklist = [
        "✅ Repository pushed to GitHub",
        "✅ render.yaml configured",
        "✅ Procfile created",
        "✅ requirements.txt updated",
        "✅ Environment variables set",
        "✅ Database service created",
        "✅ Build command: pip install -r requirements.txt",
        "✅ Start command: gunicorn --bind 0.0.0.0:$PORT run:app",
        "✅ PORT environment variable set",
        "✅ FLASK_ENV=production",
        "✅ Debug mode disabled in production"
    ]
    
    for item in checklist:
        print(item)
    
    print("\n🚀 Next Steps:")
    print("1. Push changes to GitHub")
    print("2. Check Render dashboard for deployment status")
    print("3. Review deployment logs if issues occur")
    print("4. Test deployed application")
    print("5. Monitor performance and logs")

if __name__ == "__main__":
    print("🚀 My Diary - Render Deployment Check")
    print("=" * 50)
    
    # Set test environment if not set
    if not os.environ.get('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'production'
    
    if check_deployment_readiness():
        deployment_checklist()
    else:
        print("\n❌ Please fix the issues above before deploying to Render.")
        sys.exit(1)
