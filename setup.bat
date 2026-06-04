@echo off
REM Social Intelligence Platform - Setup Script for Windows

echo =======================================
echo Social Intelligence Platform - Setup
echo =======================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo Python found!
echo.

echo Installing backend dependencies...
cd backend
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Downloading NLTK data...
python -c "import nltk; nltk.download('vader_lexicon', quiet=True)"

cd ..

echo.
echo =======================================
echo Setup complete!
echo =======================================
echo.
echo Next steps:
echo.
echo 1. Start the backend:
echo    cd backend
echo    python main.py
echo.
echo 2. In a new terminal, start the frontend:
echo    cd frontend
echo    python -m http.server 3000
echo.
echo 3. Open your browser to:
echo    http://localhost:3000
echo.
echo See README.md for detailed instructions
echo.
pause
