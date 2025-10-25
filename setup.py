import os
import sys
import subprocess

def install_packages():
    """Install required Python packages."""
    print("Installing required packages...")
    packages = [
        'markdown',
        'bleach',
        'python-dotenv',
        'flask',
        'flask-sqlalchemy',
        'flask-login',
        'flask-wtf',
        'email-validator',
        'flask-migrate'
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def setup_environment():
    """Set up the environment variables."""
    print("Setting up environment...")
    env_file = '.env'
    if not os.path.exists(env_file):
        with open(env_file, 'w') as f:
            f.write('''FLASK_APP=wsgi.py
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///diary.db
''')
        print(f"Created {env_file} file with default settings.")
    else:
        print(f"{env_file} already exists. Skipping creation.")

def main():
    print("Setting up My Diary application...")
    install_packages()
    setup_environment()
    print("\nSetup complete! Now you can run the application with:")
    print("1. flask db init")
    print("2. flask db migrate -m 'Initial migration'")
    print("3. flask db upgrade")
    print("4. flask run")

if __name__ == "__main__":
    main()
