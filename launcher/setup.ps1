# One-step setup for the Family Stock Tracker (Windows / PowerShell).
# Creates a virtual environment and installs dependencies.

$ErrorActionPreference = "Stop"

Write-Host "Creating virtual environment (.venv)..."
python -m venv .venv

Write-Host "Installing dependencies..."
& ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

Write-Host ""
Write-Host "Setup complete. To run the dashboard:"
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host "  streamlit run app.py"
Write-Host ""
Write-Host "Optional: to enable Today's Briefing (needs Ollama running locally):"
Write-Host "  winget install Ollama.Ollama"
Write-Host "  ollama pull llama3.1:8b"
