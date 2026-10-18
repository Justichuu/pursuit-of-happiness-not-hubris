@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python is not on PATH.
  pause
  exit /b 1
)
if "%~1"=="" (
  echo Leadsafe only takes one refined bar.
  echo Example: LeadSafe.bat .refined\your-bar.md
  echo Not the miner. Not the smelter.
  pause
  exit /b 1
)
python "%~dp0leadsafe.py" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" pause
endlocal & exit /b %ERR%
