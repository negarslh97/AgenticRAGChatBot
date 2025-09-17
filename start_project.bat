@echo off
echo =======================================
echo    SallyChatBot Project Launcher
echo =======================================
echo.

REM Check if virtual environment exists
if not exist "sally-backend\venv" (
    echo Creating virtual environment...
    cd sally-backend
    python -m venv venv
    cd ..
    echo Virtual environment created.
)

REM Activate virtual environment and start backend
echo Starting Backend Server...
start "Backend Server" cmd /k "cd sally-backend && call venv\Scripts\activate && python main.py"

timeout /t 5 /nobreak > nul

REM Start frontend
echo Starting Frontend Server...
start "Frontend Server" cmd /k "cd sally-frontend && npm start"

echo.
echo =======================================
echo    Servers are starting...
echo =======================================
echo Backend API: http://127.0.0.1:8000
echo Frontend App: http://localhost:3000
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo Default Admin Login:
echo Email: admin@sally.com
echo Password: admin123
echo =======================================
echo.
pause
