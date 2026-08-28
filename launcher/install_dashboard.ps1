# One-time installer for a family member's own PC (Windows).
# Double-clicking Install.bat in the repo root runs this. Installs Python and
# Ollama if missing, sets up the virtual environment, pulls the local AI
# model, creates a Desktop shortcut, and registers the daily briefing job.
# Safe to re-run -- every step either checks first or overwrites cleanly.

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Update-SessionPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

Write-Host "=== Family Stock Dashboard -- one-time setup ===" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Python ---
if (Test-Command "python") {
    Write-Host "[1/5] Python found." -ForegroundColor Green
} else {
    if (Test-Command "winget") {
        Write-Host "[1/5] Installing Python (this can take a minute)..."
        winget install --id Python.Python.3.11 -e --silent --accept-package-agreements --accept-source-agreements
        Update-SessionPath
        if (-not (Test-Command "python")) {
            Write-Host "Python installed but isn't on PATH yet in this window." -ForegroundColor Yellow
            Write-Host "Please close this window, double-click Install.bat again, and it will pick up from here." -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "Python isn't installed and winget isn't available on this PC." -ForegroundColor Red
        Write-Host "Please install Python from https://python.org (check 'Add to PATH' during install), then run Install.bat again." -ForegroundColor Red
        exit 1
    }
}

# --- Step 2: virtual environment + dependencies (reuse setup.ps1) ---
Write-Host "[2/5] Setting up the app's Python environment..."
try {
    & "$RepoRoot\launcher\setup.ps1"
} catch {
    Write-Host "Failed to set up the Python environment: $_" -ForegroundColor Red
    exit 1
}

# --- Step 3: Ollama (local AI model for Today's Briefing) ---
if (Test-Command "ollama") {
    Write-Host "[3/5] Ollama found." -ForegroundColor Green
} else {
    if (Test-Command "winget") {
        Write-Host "[3/5] Installing Ollama (this can take a minute)..."
        winget install --id Ollama.Ollama -e --silent --accept-package-agreements --accept-source-agreements
        Update-SessionPath
    } else {
        Write-Host "[3/5] Skipping Ollama -- winget isn't available." -ForegroundColor Yellow
        Write-Host "You can install it later from https://ollama.com; everything except Today's Briefing works without it." -ForegroundColor Yellow
    }
}

if (Test-Command "ollama") {
    Write-Host "Downloading the local AI model (about 5 GB, one-time -- this is the slow part)..."
    try { Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue } catch {}
    Start-Sleep -Seconds 3
    try {
        & ollama pull llama3.1:8b
    } catch {
        Write-Host "Couldn't download the AI model right now: $_" -ForegroundColor Yellow
        Write-Host "The dashboard still works -- Today's Briefing will just show a setup reminder until this succeeds." -ForegroundColor Yellow
    }
}

# --- Step 4: Desktop shortcut ---
Write-Host "[4/5] Creating a Desktop shortcut..."
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Family Stock Dashboard.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $RepoRoot "launcher\Launch-Dashboard.vbs"
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.Description = "Open the Family Stock Dashboard"
$Shortcut.IconLocation = Join-Path $RepoRoot "assets\dashboard.ico"
$Shortcut.Save()
Write-Host "Shortcut created: $ShortcutPath" -ForegroundColor Green

# --- Step 5: daily briefing job (7am) ---
Write-Host "[5/5] Scheduling the daily briefing to prepare itself each morning..."
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$BriefingScript = Join-Path $RepoRoot "jobs\run_daily_briefing.py"
schtasks /create /tn "StockTrackerBriefing" /tr "'$PythonExe' '$BriefingScript'" /sc daily /st 07:00 /f | Out-Null

Write-Host ""
Write-Host "=== All set! ===" -ForegroundColor Cyan
Write-Host "Look for 'Family Stock Dashboard' on the Desktop -- double-click it any time to open the dashboard."
