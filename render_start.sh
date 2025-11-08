#!/bin/bash
set -e

# Apply database migrations before starting the app
flask db upgrade

# Launch the application (Render provides $PORT)
exec gunicorn "app:create_app()" --bind "0.0.0.0:${PORT:-10000}"
