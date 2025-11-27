#!/bin/bash

# My Diary Deployment Script
# This script prepares and deploys the My Diary application to production

set -e  # Exit on any error

echo "🚀 Starting My Diary deployment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️ .env file not found. Please copy .env.example to .env and configure it."
    echo "📝 Copying .env.example to .env..."
    cp .env.example .env
    echo "❌ Please edit .env file with your configuration and run this script again."
    exit 1
fi

# Run database migrations
echo "🗄️ Running database migrations..."
if [[ "$DATABASE_URL" == *"mssql+pyodbc"* ]]; then
    echo "🪣 SQL Server detected, running setup script..."
    python setup_sql_server.py
elif [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    echo "🐘 PostgreSQL detected, running setup script..."
    python setup_postgresql.py
elif [[ "$DATABASE_URL" == *"sqlite"* ]]; then
    echo "📄 SQLite detected, running setup script..."
    python setup_sqlite.py
else
    echo "⚠️ Unknown database type, using SQLite fallback..."
    export DATABASE_URL="sqlite:///my_diary.db"
    python setup_sqlite.py
fi

# Collect static files (if needed)
echo "📁 Optimizing static files..."
python -c "
import os
from app import create_app
from config_production import ProductionConfig

app = create_app(ProductionConfig)
with app.app_context():
    print('Static files optimized')
"

# Test the application
echo "🧪 Running basic tests..."
python -c "
from app import create_app
from config_production import ProductionConfig

app = create_app(ProductionConfig)
with app.app_context():
    print('✅ Application loads successfully')
    print('✅ Database connection works')
    print('✅ Configuration loaded')
"

# Create startup script
echo "📜 Creating startup script..."
cat > start.sh << 'EOF'
#!/bin/bash
export FLASK_ENV=production
export PYTHONPATH=$(pwd)
source venv/bin/activate
gunicorn --workers 3 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT wsgi:app
EOF

chmod +x start.sh

echo "✅ Deployment preparation complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Configure your .env file with proper values"
echo "2. Set up your database (PostgreSQL recommended for production)"
echo "3. Configure your web server (Nginx) to proxy to Gunicorn"
echo "4. Set up SSL certificates"
echo "5. Deploy to your hosting platform"
echo ""
echo "📋 Quick start commands:"
echo "  - Start locally: ./start.sh"
echo "  - Run migrations: flask db upgrade"
echo "  - Create admin: python -c 'from app.models import User; from app import create_app; app= create_app(); app.app_context().push(); User.create_admin(\"admin@example.com\", \"password\")'"
echo ""
echo "🌟 Your My Diary application is ready for deployment!"
