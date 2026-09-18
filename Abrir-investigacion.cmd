@echo off
cd /d "%~dp0"
python -c "import sys; sys.exit(sys.version_info < (3,10))" >nul 2>&1
if not errorlevel 1 (
  python scripts\frontend.py
  if errorlevel 1 pause
  exit /b
)
py -3 -c "import sys; sys.exit(sys.version_info < (3,10))" >nul 2>&1
if not errorlevel 1 (
  py -3 scripts\frontend.py
  if errorlevel 1 pause
  exit /b
)
echo Instala Python 3.10 o posterior y activa su acceso desde la terminal.
pause
