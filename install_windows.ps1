# NSFW Guard Pro - Windows Deployment Script (PowerShell)

Write-Host "------------------------------------------------" -ForegroundColor Cyan
Write-Host "NSFW Guard Pro - Windows Installer" -ForegroundColor Cyan
Write-Host "------------------------------------------------" -ForegroundColor Cyan

# 1. Check Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found! Please install Python 3.10+ from python.org"
    exit
}

# 2. Setup Virtual Environment
Write-Host "[1/4] Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install Dependencies
$title = "Hardware Selection"
$message = "Do you have an NVIDIA GPU and want to use CUDA acceleration?"
$gpu = New-Object System.Management.Automation.Host.ChoiceDescription "&Yes", "Install GPU version (Fastest)"
$cpu = New-Object System.Management.Automation.Host.ChoiceDescription "&No", "Install CPU version (Server/Generic)"
$options = [System.Management.Automation.Host.ChoiceDescription[]]($gpu, $cpu)
$result = $host.ui.PromptForChoice($title, $message, $options, 1)

if ($result -eq 0) {
    Write-Host ">> Installing GPU version..." -ForegroundColor Green
    pip install -r requirements-gpu.txt
} else {
    Write-Host ">> Installing CPU version..." -ForegroundColor Green
    pip install -r requirements.txt
}

# 4. Setup API Key
if (-not $env:NSFW_API_KEY) {
    $newKey = "NSFW_PRO_" + [System.IO.Path]::GetRandomFileName().Replace(".", "")
    Write-Host "[3/4] Generating API Key..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("NSFW_API_KEY", $newKey, "User")
    $env:NSFW_API_KEY = $newKey
    Write-Host ">> Your API Key is: $newKey (Saved to User Environment Variables)" -ForegroundColor Green
}

# 5. Done
Write-Host "------------------------------------------------" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Cyan
Write-Host "To start the server, run:" -ForegroundColor White
Write-Host ".\venv\Scripts\python.exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000" -ForegroundColor Green
Write-Host "------------------------------------------------" -ForegroundColor Cyan
