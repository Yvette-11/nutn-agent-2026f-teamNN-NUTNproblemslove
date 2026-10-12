@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or newer, then try again.
  pause
  exit /b 1
)
py -3 main.py
if errorlevel 1 (
  echo.
  echo The program stopped with an error. Please copy the error text and send it for help.
  pause
)
