@echo off
echo Setting up My Diary application...

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

:: Activate virtual environment and install packages
call venv\Scripts\activate
python -m pip install --upgrade pip
python setup.py

:: Set FLASK_APP environment variable
set FLASK_APP=wsgi.py

:: Initialize and upgrade the database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

echo.
echo Setup complete! To run the application, use:
echo   venv\Scripts\activate
echo   flask run

pause
