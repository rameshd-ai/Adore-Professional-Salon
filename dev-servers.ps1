# Glamr dev: stop and/or start servers.
#
# Default: build frontend + API only on 8001 (public site + API + admin same origin).
# Use -WithVite for the old two-window workflow (Vite 5173 + API 8001).
#
# Usage (from repo sal\ folder):
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\dev-servers.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\dev-servers.ps1 -Action stop
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\dev-servers.ps1 -WithVite
#
# Requires: Python on PATH, npm on PATH; see CLAUDE.md if ports are stuck after stop.
#
# Why ports sometimes "won't stop":
# - uvicorn --reload = parent + worker; we kill by process tree and by port.
# - Windows can show ghost LISTEN rows until you close the terminal that started the server (or reboot / WinNAT reset as admin).

param(
    [ValidateSet('restart', 'stop', 'start')]
    [string] $Action = 'restart',
    [switch] $WithVite
)

$ErrorActionPreference = 'SilentlyContinue'
$SalRoot = $PSScriptRoot
$BackendRoot = Join-Path $SalRoot 'backend'
$FrontendRoot = Join-Path $SalRoot 'frontend'

function Stop-ProcessTree {
    param([int] $ProcessId)
    if ($ProcessId -le 0) { return }
    $null = & taskkill.exe /F /T /PID $ProcessId 2>&1
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Stop-GlamrDevServers {
    Write-Host 'Stopping Python/py processes running this API (uvicorn / app.main:app)...'
    Get-CimInstance Win32_Process |
        Where-Object {
            $n = if ($_.Name) { $_.Name.ToLowerInvariant() } else { '' }
            $cl = $_.CommandLine
            if (-not $cl) { return $false }
            $isPyLauncher = ($n -eq 'python.exe' -or $n -eq 'pythonw.exe' -or $n -eq 'py.exe' -or $n -like 'python*.exe')
            if (-not $isPyLauncher) { return $false }
            return ($cl -match 'uvicorn' -or $cl -match 'app\.main:app')
        } |
        ForEach-Object {
            Write-Host "  taskkill /T /PID $($_.ProcessId) ($($_.Name))"
            Stop-ProcessTree -ProcessId $_.ProcessId
        }

    Write-Host 'Stopping Node processes running Vite...'
    Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" |
        Where-Object { $_.CommandLine -match 'vite' } |
        ForEach-Object {
            Write-Host "  taskkill /T /PID $($_.ProcessId) (vite)"
            Stop-ProcessTree -ProcessId $_.ProcessId
        }

    Start-Sleep -Milliseconds 500

    Write-Host 'Stopping any remaining listeners on ports 8000, 8001, 5173...'
    for ($round = 1; $round -le 3; $round++) {
        foreach ($port in 8000, 8001, 5173) {
            $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($procId in $pids) {
                if (-not $procId) { continue }
                Write-Host "  Port $port -> taskkill /F /T /PID $procId"
                Stop-ProcessTree -ProcessId $procId
            }
        }
        Start-Sleep -Milliseconds 600
    }

    Start-Sleep -Milliseconds 400
    $busy = @()
    foreach ($port in 8001, 5173) {
        $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($c) { $busy += "Port $port still in use (PID(s): $($c.OwningProcess -join ', '))" }
    }
    if ($busy) {
        Write-Host 'Warning:'
        $busy | ForEach-Object { Write-Host "  $_" }
        Write-Host 'If ports stay stuck, close the terminals that started the servers or run fix-stuck-port-8000-admin.bat as Administrator.'
    } else {
        Write-Host 'Ports 8001 and 5173 are free.'
    }
}

function Start-GlamrDevServers {
    if (-not (Test-Path -LiteralPath $BackendRoot)) {
        Write-Error "Backend folder not found: $BackendRoot"
        exit 1
    }
    if (-not (Test-Path -LiteralPath $FrontendRoot)) {
        Write-Error "Frontend folder not found: $FrontendRoot"
        exit 1
    }

    $apiCmd = "if (-not `$env:DATABASE_URL) { `$env:DATABASE_URL = 'sqlite:///./glamr.db' }; Write-Host 'API + site http://127.0.0.1:8001' -ForegroundColor Green; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001"
    $viteCmd = "Write-Host 'Vite http://127.0.0.1:5173' -ForegroundColor Green; npm run dev"

    if (-not $WithVite) {
        Write-Host 'Building frontend (Vite production bundle for single-server mode)...'
        Push-Location $FrontendRoot
        try {
            npm run build
            if ($LASTEXITCODE -ne 0) {
                Write-Error 'npm run build failed.'
                exit $LASTEXITCODE
            }
        }
        finally {
            Pop-Location
        }
        Write-Host 'Opening API window (8001 serves site, /api, /admin)...'
        Start-Process powershell.exe -WorkingDirectory $BackendRoot -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $apiCmd
        )
        Write-Host 'Done. Site + API + admin: http://127.0.0.1:8001/  |  Admin: http://127.0.0.1:8001/admin/'
        return
    }

    Write-Host 'Opening new windows: API (8001) and Vite (5173)...'
    Start-Process powershell.exe -WorkingDirectory $BackendRoot -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $apiCmd
    )
    Start-Process powershell.exe -WorkingDirectory $FrontendRoot -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $viteCmd
    )
    Write-Host 'Done. Site (dev): http://127.0.0.1:5173  |  Admin (proxied): http://127.0.0.1:5173/admin/'
}

switch ($Action) {
    'stop' {
        Stop-GlamrDevServers
    }
    'start' {
        Start-GlamrDevServers
    }
    'restart' {
        Stop-GlamrDevServers
        Write-Host ''
        Start-GlamrDevServers
    }
}
