@echo off
REM HomeServe Pro - Quick Start Script for Windows
REM This script automates the initial setup process

echo.
echo 🏠 HomeServe Pro - Quick Start Setup
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo ✅ Python found
python --version
echo.

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Check if .env exists
if not exist .env (
    echo ⚙️  Creating .env file from template...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANT: Please edit .env file with your MongoDB URI and secret keys
    echo    Minimum required:
    echo    - MONGO_URI (get from MongoDB Atlas^)
    echo    - SECRET_KEY (generate random string^)
    echo    - JWT_SECRET_KEY (generate random string^)
    echo.
    pause
)

REM Create necessary directories
echo 📁 Creating directories...
if not exist uploads mkdir uploads
if not exist models mkdir models
if not exist logs mkdir logs

REM Initialize database
echo 🗄️  Initializing database...
flask init-db

REM Ask if user wants to seed data
echo.
set /p SEED="Do you want to seed sample data? (y/n): "
if /i "%SEED%"=="y" (
    echo 🌱 Seeding sample data...
    flask seed-data
    echo.
    echo ✅ Sample accounts created:
    echo    Customer: customer@test.com / password123
    echo    Vendor: vendor@test.com / password123
    echo    Onboard Manager: onboard@test.com / password123
    echo    Ops Manager: ops@test.com / password123
)

REM Ask if user wants to create admin
echo.
set /p ADMIN="Do you want to create a super admin account? (y/n): "
if /i "%ADMIN%"=="y" (
    echo 👤 Creating super admin...
    flask create-admin
)

echo.
echo ✅ Setup complete!
echo.
echo 🚀 To start the application, run:
echo    python run.py
echo.
echo 📚 Documentation:
echo    - README.md - Overview and features
echo    - SETUP_GUIDE.md - Detailed setup instructions
echo    - API_DOCUMENTATION.md - Complete API reference
echo.
echo 🌐 The application will be available at:
echo    http://localhost:5000
echo.
echo Happy coding! 🎉
echo.
pause

