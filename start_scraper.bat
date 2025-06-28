@echo off
echo =============================================
echo   Wellfound Job Scraper System Startup
echo =============================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ and add it to your PATH
    pause
    exit /b 1
)

echo Python found!
echo.

echo Installing required packages...
pip install -r requirements.txt

echo.
echo Starting Flask application...
echo =============================================
echo   Open your browser and go to:
echo   http://localhost:5000
echo =============================================
echo.

python app.py
pause
