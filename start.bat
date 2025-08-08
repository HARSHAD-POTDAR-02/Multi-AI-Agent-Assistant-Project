@echo off
echo Starting Simi.ai Multi-Agent Assistant...
echo.

echo Starting Backend Server...
start "Simi.ai Backend" cmd /k "python backend.py"

echo Waiting for backend to start...
timeout /t 3 /nobreak > nul

echo Starting React Frontend...
cd frontend
start "Simi.ai Frontend" cmd /k "npm start"

echo.
echo Simi.ai is starting up!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
pause