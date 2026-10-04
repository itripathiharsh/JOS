# ==============================================================================
# Job Operating System - Local Production One-Command Startup
# 100% Local, Strict F: Drive Architecture
# ==============================================================================
[CmdletBinding()]
param (
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "F:\job wala project"
$pythonExe = Join-Path $workspaceRoot ".venv\Scripts\python.exe"
$scriptsDir = Join-Path $workspaceRoot "scripts"
$supervisorPy = Join-Path $scriptsDir "supervisor.py"
$tmpDir = Join-Path $workspaceRoot "tmp"
$logsDir = Join-Path $workspaceRoot "logs"
$pidsFile = Join-Path $tmpDir "pids.json"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "         JOB OPERATING SYSTEM - LOCAL PRODUCTION STARTUP                " -ForegroundColor Cyan
Write-Host "         100% Local | Zero-Cost Infrastructure | F: Drive Isolated      " -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

function Test-PortListening([int]$port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $conn)
}

# 1. Check if already running
if (Test-Path $pidsFile) {
    try {
        $pids = Get-Content $pidsFile -Raw | ConvertFrom-Json
        $bePid = if ($pids.backend) { [int]$pids.backend.pid } else { 0 }
        if ($bePid -gt 0) {
            $p = Get-Process -Id $bePid -ErrorAction SilentlyContinue
            if ($p) {
                Write-Host "`nJob Operating System is ALREADY running (Backend PID: $bePid)." -ForegroundColor Cyan
                & (Join-Path $scriptsDir "status.ps1")
                exit 0
            }
        }
    } catch {}
}

# Check if ports 8000 or 5173 are already bound
if ((Test-PortListening 8000) -or (Test-PortListening 5173)) {
    Write-Host "`nPorts 8000 or 5173 are already bound. Showing status..." -ForegroundColor Yellow
    & (Join-Path $scriptsDir "status.ps1")
    exit 0
}

# 2. Launch Supervisor
if ($Foreground) {
    Write-Host "`nLaunching Job Operating System Supervisor in foreground (Ctrl+C to stop)..." -ForegroundColor Green
    & $pythonExe $supervisorPy
    exit $LASTEXITCODE
} else {
    Write-Host "`nLaunching Job Operating System Supervisor in background..." -ForegroundColor Green
    $proc = Start-Process -FilePath $pythonExe -ArgumentList "`"$supervisorPy`"" -WorkingDirectory $workspaceRoot -WindowStyle Hidden -PassThru
    Write-Host "Supervisor launched (PID: $($proc.Id))." -ForegroundColor Gray

    # 3. Wait for Port Readiness
    Write-Host "Awaiting system startup..." -ForegroundColor Yellow
    $retries = 15
    while ($retries -gt 0) {
        Start-Sleep -Seconds 1
        $beReady = Test-PortListening 8000
        $feReady = Test-PortListening 5173
        if ($beReady -and $feReady) {
            Write-Host "Ports 8000 and 5173 are active." -ForegroundColor Green
            break
        }
        $retries--
    }

    # 4. Display Status
    Start-Sleep -Milliseconds 500
    & (Join-Path $scriptsDir "status.ps1")
}
