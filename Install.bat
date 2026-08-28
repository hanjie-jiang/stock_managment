@echo off
REM One-time setup: installs Python/Ollama if needed, sets up the app, and
REM creates a Desktop shortcut. Double-click this file to run it.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\install_dashboard.ps1"
echo.
pause
