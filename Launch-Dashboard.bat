@echo off
REM Opens the Family Stock Dashboard. This is what the Desktop shortcut runs
REM -- keep this window open while you use the dashboard; closing it stops
REM the app.
cd /d "%~dp0"

echo Starting your Family Stock Dashboard...
echo Your browser will open in a few seconds. Keep this window open while you use it.
echo.

start "" /min ollama serve

".venv\Scripts\python.exe" -m streamlit run app.py
