@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python is not on PATH.
  pause
  exit /b 1
)
pythonw "%~dp0smelt_gui.py" 2>nul
if errorlevel 1 python "%~dp0smelt_gui.py"
endlocal
