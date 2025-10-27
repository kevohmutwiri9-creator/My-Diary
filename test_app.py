#!/usr/bin/env python
"""Test script to verify application functionality."""
import requests
import sys

def test_application():
    """Test basic application functionality."""
    base_url = 'http://localhost:5000'

    try:
        # Test home page
        print("Testing home page...")
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✅ Home page loads successfully")
        else:
            print(f"❌ Home page failed: {response.status_code}")
            return False

        # Test static files
        print("Testing static files...")
        response = requests.get(f"{base_url}/static/css/bootstrap.min.css", timeout=5)
        if response.status_code == 200:
            print("✅ Static files accessible")
        else:
            print(f"❌ Static files failed: {response.status_code}")

        print("🎉 Basic application tests passed!")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        print("Make sure the application is running on http://localhost:5000")
        return False

if __name__ == '__main__':
    success = test_application()
    sys.exit(0 if success else 1)
