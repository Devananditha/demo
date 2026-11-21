# ServiceYield AI - Full Stack + Cloudflare Tunnel Launcher
param(
    [switch]$NoTunnel = $false
)

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting ServiceYield AI Backend, Frontend & Cloud Tunnel" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Terminate any previous processes on ports 8000 or 3000
$ports = @(8000, 3000)
foreach ($p in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($c in $conns) {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

# 2. Start FastAPI Backend (Port 8000)
Write-Host "[1/3] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$backend = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory "$PSScriptRoot\backend" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

# 3. Start Vite Frontend (Port 3000)
Write-Host "[2/3] Starting Vite Frontend on http://127.0.0.1:3000..." -ForegroundColor Yellow
$frontend = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WorkingDirectory "$PSScriptRoot\frontend" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

Write-Host "Local Application Running:" -ForegroundColor Green
Write-Host "  Backend:  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Frontend: http://127.0.0.1:3000" -ForegroundColor White

if ($NoTunnel) {
    Write-Host "`nAll services active locally. Press Ctrl+C to stop." -ForegroundColor Cyan
    while ($true) { Start-Sleep -Seconds 1 }
    exit 0
}

# 4. Start Cloudflare Tunnel
Write-Host "`n[3/3] Initializing Cloudflare Public Tunnel..." -ForegroundColor Yellow
Write-Host "Your shareable HTTPS link will appear below within a few seconds:`n" -ForegroundColor Gray

& "$PSScriptRoot\cloudflared.exe" tunnel --protocol http2 --url http://127.0.0.1:3000
