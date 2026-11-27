@echo off
setlocal
title EchoOS GUI

for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"

rem pythonw.exe بيشغّل التطبيق من غير ما يفتح نافذة terminal
set "PYTHONW=%PROJECT_ROOT%\.venv\Scripts\pythonw.exe"
rem python.exe بنستخدمه بس للتشيك على الـ dependencies
set "PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo.
    echo [EchoOS GUI] ERROR: The project virtual environment was not found.
    echo Create the environment and install dependencies from the repository root:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    echo   .venv\Scripts\python.exe -m pip install -r gui\requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo [EchoOS GUI] Checking GUI and audio dependencies...
"%PYTHON%" -c "import importlib.util,sys; modules=('flask','numpy','sounddevice','faster_whisper','webrtcvad'); missing=[m for m in modules if importlib.util.find_spec(m) is None]; print('Missing modules: '+', '.join(missing)) if missing else print('Dependencies: OK'); sys.exit(1 if missing else 0)"
if errorlevel 1 (
    echo.
    echo [EchoOS GUI] ERROR: Required dependencies are missing.
    echo Install them inside the project virtual environment with:
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    echo   .venv\Scripts\python.exe -m pip install -r gui\requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo [EchoOS GUI] Starting EchoOS GUI (no terminal window)...
echo Browser fallback: http://127.0.0.1:5050
echo.
rem pythonw.exe بيشغّل app.py من غير ما يفتح terminal
start "" "%PYTHONW%" "%~dp0app.py"
exit /b 0
