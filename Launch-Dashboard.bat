@echo off
REM Opens the Family Stock Dashboard with a visible terminal window -- useful
REM for troubleshooting. The Desktop shortcut normally uses
REM Launch-Dashboard.vbs instead, which does the same thing with no visible
REM window. Keep this window open while you use the dashboard via this path;
REM closing it stops the app.
cd /d "%~dp0"

echo Starting your Family Stock Dashboard...
echo Your browser will open in a few seconds. Keep this window open while you use it.
echo.

start "" /min ollama serve

".venv\Scripts\python.exe" -m streamlit run app.py
