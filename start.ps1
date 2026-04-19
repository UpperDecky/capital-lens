# start.ps1 — Run Capital Lens locally on Windows
# Usage: cd capital-lens; .\start.ps1

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

# --- .env setup ---
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "⚠️  Created .env from .env.example" -ForegroundColor Yellow
    Write-Host "    Open capital-lens\.env and add your ANTHROPIC_API_KEY" -ForegroundColor Yellow
    Write-Host ""
}

# --- Python deps ---
$FastAPICheck = python -c "import fastapi" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[setup] Installing Python dependencies..." -ForegroundColor Cyan
    pip install -r requirements.txt
}

# --- Frontend deps ---
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "[setup] Installing frontend dependencies..." -ForegroundColor Cyan
    Set-Location frontend
    npm install --legacy-peer-deps
    Set-Location $Root
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Capital Lens starting..." -ForegroundColor Blue
Write-Host "  Backend  → http://localhost:8000" -ForegroundColor Green
Write-Host "  Frontend → http://localhost:5173" -ForegroundColor Green
Write-Host "  API Docs → http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Press Ctrl+C in each window to stop." -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Start backend in a new PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root'; python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

# Start frontend in a new PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\frontend'; npm run dev"

Write-Host "Both windows opened. Visit http://localhost:5173" -ForegroundColor Green
