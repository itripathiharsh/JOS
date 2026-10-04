# ==============================================================================
# Job Operating System - Local Restart Script
# ==============================================================================
[CmdletBinding()]
param (
    [switch]$DevFrontend
)

$workspaceRoot = "F:\job wala project"
$scriptsDir = Join-Path $workspaceRoot "scripts"

Write-Host "Restarting Job Operating System..." -ForegroundColor Yellow
& (Join-Path $scriptsDir "stop.ps1")
Start-Sleep -Seconds 2

if ($DevFrontend) {
    & (Join-Path $scriptsDir "start.ps1") -DevFrontend
} else {
    & (Join-Path $scriptsDir "start.ps1")
}
