# Glamr API on port 8001 (avoids a stuck Windows listener on 8000).
# Usage: from backend folder, .\start-api.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "sqlite:///./glamr.db"
}
Write-Host "Starting API at http://127.0.0.1:8001 (DATABASE_URL=$($env:DATABASE_URL))"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
