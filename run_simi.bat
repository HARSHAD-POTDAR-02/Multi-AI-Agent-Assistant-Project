@echo off
echo ================================================
echo Starting Simi.ai Multi-Agent Assistant
echo ================================================
echo.

echo [1/2] Starting Backend Server...
start "Simi.ai Backend" cmd /k "python backend.py"

echo [2/2] Waiting for backend to initialize...
timeout /t 5 /nobreak > nul

echo [3/3] Starting Frontend...
cd frontend
start "Simi.ai Frontend" cmd /k "npm start"

echo.
echo ================================================
echo Simi.ai is starting up!
echo Backend: http://localhost:8001
echo Frontend: http://localhost:3000
echo ================================================
echo.
echo Press any key to continue...
pause > nul