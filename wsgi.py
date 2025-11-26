import os
from app import create_app

# Determine configuration based on environment
env = os.environ.get('FLASK_ENV', 'production')
if env == 'production':
    from config_production import ProductionConfig
    app = create_app(ProductionConfig)
else:
    app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
