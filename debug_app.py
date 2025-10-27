#!/usr/bin/env python
"""Test script to debug application issues."""
from app import create_app

def test_app():
    """Test application creation and configuration."""
    try:
        print("Creating Flask application...")
        app = create_app()
        print("✅ App created successfully")

        print("Testing blueprint imports...")
        from app.routes.main import main_bp
        print("✅ Main blueprint imported")

        from app.routes.auth import auth_bp
        print("✅ Auth blueprint imported")

        print("Testing template rendering...")
        with app.test_client() as client:
            response = client.get('/')
            print(f"✅ Home route response: {response.status_code}")

        print("🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_app()
