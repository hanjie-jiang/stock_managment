# Starts the dashboard with no visible window, then opens the browser.
# Invoked hidden by Launch-Dashboard.vbs (the Desktop shortcut's real target).
# Safe to run repeatedly -- if the dashboard is already running, this just
# reopens the browser to it instead of starting a second copy.

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Test-Port($port) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect("localhost", $port)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

if (Test-Port 8501) {
    Start-Process "http://localhost:8501"
    exit
}

try { Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue } catch {}

Start-Process -FilePath ".venv\Scripts\python.exe" `
    -ArgumentList @("-m", "streamlit", "run", "app.py", "--server.headless", "true") `
    -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds(30)
while (-not (Test-Port 8501) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
}

Start-Process "http://localhost:8501"
