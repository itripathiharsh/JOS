# ==============================================================================
# Job Operating System - Real-Time Local Status Inspector
# ==============================================================================
[CmdletBinding()]
param ()

$ErrorActionPreference = "Continue"

$workspaceRoot = "F:\job wala project"
$pythonExe = Join-Path $workspaceRoot ".venv\Scripts\python.exe"
$tmpDir = Join-Path $workspaceRoot "tmp"
$pidsFile = Join-Path $tmpDir "pids.json"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "         JOB OPERATING SYSTEM - SYSTEM STATUS INSPECTOR                 " -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

function Test-ProcessAlive([int]$procId) {
    if ($procId -le 0) { return $false }
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    return ($null -ne $p)
}

function Get-ProcessMetrics([int]$procId) {
    if ($procId -le 0) { return "-" }
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if (-not $p) { return "-" }
    $memMb = [math]::Round($p.WorkingSet64 / 1MB, 1)
    return "${memMb} MB"
}

# 1. Process Status Table
Write-Host "`n[1] PROCESS STATUS" -ForegroundColor Yellow
Write-Host "------------------------------------------------------------------------" -ForegroundColor DarkGray
"{0,-12} {1,-8} {2,-10} {3,-12} {4,-12} {5,-12}" -f "COMPONENT", "PID", "PORT", "STATUS", "MEMORY", "PORT LISTEN"
Write-Host "------------------------------------------------------------------------" -ForegroundColor DarkGray

$pids = @{}
if (Test-Path $pidsFile) {
    try {
        $raw = Get-Content $pidsFile -Raw | ConvertFrom-Json
        foreach ($prop in $raw.PSObject.Properties) {
            $pids[$prop.Name] = $prop.Value
        }
    } catch {}
}

foreach ($comp in @("backend", "worker", "scheduler", "frontend")) {
    $info = $pids[$comp]
    $pidVal = if ($info) { [int]$info.pid } else { 0 }
    $portVal = if ($info -and $info.port) { $info.port } else { "-" }
    $isAlive = Test-ProcessAlive $pidVal
    $memStr = Get-ProcessMetrics $pidVal
    $statusText = if ($isAlive) { "RUNNING" } else { "STOPPED" }
    $statusColor = if ($isAlive) { "Green" } else { "Red" }

    $portListen = "-"
    if ($info -and $info.port) {
        $conn = Get-NetTCPConnection -LocalPort ([int]$info.port) -State Listen -ErrorAction SilentlyContinue
        $portListen = if ($conn) { "YES" } else { "NO" }
    }

    $displayPid = if ($pidVal -gt 0) { $pidVal } else { "-" }
    Write-Host ("{0,-12} {1,-8} {2,-10} " -f $comp, $displayPid, $portVal) -NoNewline
    Write-Host ("{0,-12} " -f $statusText) -ForegroundColor $statusColor -NoNewline
    Write-Host ("{0,-12} {1,-12}" -f $memStr, $portListen)
}
Write-Host "------------------------------------------------------------------------" -ForegroundColor DarkGray

# 2. Database & Queue Telemetry
Write-Host "`n[2] DATABASE & STEP 12 QUEUE TELEMETRY" -ForegroundColor Yellow
$telemetryScript = @"
import sys
from pathlib import Path
root = Path(r'$workspaceRoot')
sys.path.insert(0, str(root / 'backend'))
sys.path.insert(0, str(root))
from app.db.session import SessionLocal, check_db_connection
from app.models.automation import AutomationTask, AutomationSettings
from sqlalchemy import func

if not check_db_connection():
    print('DB_CONN: FAILED')
    sys.exit(0)

print('DB_CONN: OK')
db = SessionLocal()
try:
    pending = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == 'PENDING').scalar() or 0
    running = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == 'RUNNING').scalar() or 0
    succeeded = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == 'SUCCEEDED').scalar() or 0
    blocked = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == 'BLOCKED').scalar() or 0
    failed = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == 'FAILED').scalar() or 0
    retry_wait = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == 'RETRY_WAIT').scalar() or 0
    
    settings_rec = db.query(AutomationSettings).first()
    mode = settings_rec.mode if settings_rec else 'UNKNOWN'
    
    print(f'QUEUE: Pending={pending} | Running={running} | Succeeded={succeeded} | Blocked={blocked} | RetryWait={retry_wait} | Failed={failed}')
    print(f'AUTOMATION_MODE: {mode}')
finally:
    db.close()
"@

$tmpTelemetry = Join-Path $tmpDir "telemetry_check.py"
$telemetryScript | Set-Content $tmpTelemetry -Encoding UTF8
$telemetryOut = & $pythonExe $tmpTelemetry 2>&1
Remove-Item $tmpTelemetry -Force -ErrorAction SilentlyContinue

foreach ($line in $telemetryOut) {
    if ($line -like "*DB_CONN: OK*") {
        Write-Host "  Database Connection : " -NoNewline
        Write-Host "HEALTHY (PostgreSQL localhost:5432)" -ForegroundColor Green
    } elseif ($line -like "*QUEUE:*") {
        Write-Host "  Task Queue Status   : $line" -ForegroundColor White
    } elseif ($line -like "*AUTOMATION_MODE:*") {
        Write-Host "  Candidate Mode      : $line" -ForegroundColor Cyan
    }
}

# 3. Playwright Chromium Readiness
Write-Host "`n[3] PLAYWRIGHT / BROWSER ENGINE" -ForegroundColor Yellow
$browserCheckScript = @"
import sys, os
from pathlib import Path
root = Path(r'$workspaceRoot')
sys.path.insert(0, str(root / 'backend'))
sys.path.insert(0, str(root))
from browser.local_browser import check_browser_readiness
ok, msg = check_browser_readiness()
print(f'BROWSER_STATUS: {ok}|{msg}')
"@
$tmpBrowser = Join-Path $tmpDir "browser_check.py"
$browserCheckScript | Set-Content $tmpBrowser -Encoding UTF8
$browserOut = & $pythonExe $tmpBrowser 2>&1
Remove-Item $tmpBrowser -Force -ErrorAction SilentlyContinue

foreach ($line in $browserOut) {
    if ($line -like "*BROWSER_STATUS:*") {
        $parts = $line.Substring("BROWSER_STATUS: ".Length).Split("|")
        $isOk = $parts[0].Trim() -eq "True"
        $msg = $parts[1].Trim()
        Write-Host "  Chromium Engine     : " -NoNewline
        if ($isOk) {
            Write-Host "READY (Isolated on F: drive)" -ForegroundColor Green
        } else {
            Write-Host "FAILED ($msg)" -ForegroundColor Red
        }
    }
}

Write-Host ""
