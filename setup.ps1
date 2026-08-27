# One-step setup for the Family Stock Tracker (Windows / PowerShell).
# Creates a virtual environment, installs dependencies, and prepares a .env file.

$ErrorActionPreference = "Stop"

Write-Host "Creating virtual environment (.venv)..."
python -m venv .venv

Write-Host "Installing dependencies..."
& ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "Created .env from .env.example."
    Write-Host "Edit .env and add your ANTHROPIC_API_KEY to enable the chat assistant."
} else {
    Write-Host ".env already exists -- leaving it as is."
}

Write-Host ""
Write-Host "Setup complete. To run the dashboard:"
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host "  streamlit run app.py"
