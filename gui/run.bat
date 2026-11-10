@echo off
title EchoOS GUI
cd /d "%~dp0"

REM Check for EchoOS virtual environment
if exist "..\.venv\Scripts\python.exe" (
    set PYTHON=..\.venv\Scripts\python.exe
) else if exist "..\..\EchoOS\.venv\Scripts\python.exe" (
    set PYTHON=..\..\EchoOS\.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo.
echo   [EchoOS GUI] Verifying dependencies...
%PYTHON% -m pip install -q -r requirements.txt

echo.
echo   [EchoOS GUI] Starting web interface...
echo   Open your browser at: http://localhost:5050
echo.
%PYTHON% app.py
pause
