import os

from app import create_app, init_database, db

app = create_app()

# Initialize database after app is created
init_database(app)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
