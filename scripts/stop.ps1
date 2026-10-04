# ==============================================================================
# Job Operating System - Graceful Local Shutdown Script
# ==============================================================================
[CmdletBinding()]
param ()

$ErrorActionPreference = "Continue"

$workspaceRoot = "F:\job wala project"
$tmpDir = Join-Path $workspaceRoot "tmp"
$pidsFile = Join-Path $tmpDir "pids.json"

Write-Host "========================================================================" -ForegroundColor Yellow
Write-Host "         JOB OPERATING SYSTEM - GRACEFUL LOCAL SHUTDOWN                 " -ForegroundColor Yellow
Write-Host "========================================================================" -ForegroundColor Yellow

if (Test-Path $pidsFile) {
    try {
        $pids = Get-Content $pidsFile -Raw | ConvertFrom-Json
        
        # 1. Stop supervisor first so it does not auto-restart child daemons
        if ($pids.supervisor -and $pids.supervisor.pid) {
            $supPid = [int]$pids.supervisor.pid
            $supProc = Get-Process -Id $supPid -ErrorAction SilentlyContinue
            if ($supProc) {
                Write-Host "Stopping supervisor (PID: $supPid)..." -ForegroundColor Gray
                Stop-Process -Id $supPid -Force -ErrorAction SilentlyContinue
                Start-Sleep -Milliseconds 500
                Write-Host "  [OK] Supervisor terminated." -ForegroundColor Green
            }
        }

        # 2. Stop remaining components
        foreach ($prop in $pids.PSObject.Properties) {
            $name = $prop.Name
            if ($name -eq "supervisor") { continue }
            $info = $prop.Value
            $procId = [int]$info.pid

            if ($procId -gt 0) {
                $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "Stopping component [$name] (PID: $procId)..." -ForegroundColor Gray
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                    Write-Host "  [OK] [$name] terminated." -ForegroundColor Green
                } else {
                    Write-Host "  [$name] (PID $procId) was already stopped." -ForegroundColor DarkGray
                }
            }
        }
    } catch {
        Write-Host "Warning reading PID file: $_" -ForegroundColor DarkYellow
    }
}

# Ensure any lingering listeners on port 8000 or 5173 are released
foreach ($port in @(8000, 5173)) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        if ($conn.OwningProcess -gt 0) {
            Write-Host "Releasing listener on port $port (PID: $($conn.OwningProcess))..." -ForegroundColor DarkYellow
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

# Remove PID file
if (Test-Path $pidsFile) {
    Remove-Item $pidsFile -Force -ErrorAction SilentlyContinue
}

# Verify ports
$bePort = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
$fePort = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

if (-not $bePort -and -not $fePort) {
    Write-Host "`n[OK] All ports released. All Job Operating System components are STOPPED." -ForegroundColor Green
} else {
    Write-Host "`nWarning: Some ports may still be bound. Port 8000: $($null -ne $bePort), Port 5173: $($null -ne $fePort)" -ForegroundColor Yellow
}
