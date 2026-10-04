# Job Operating System - Local Database Backup Script
# ₹0, 100% Local, Strict F: Drive Storage
[CmdletBinding()]
param (
    [string]$Database = "job_agent_db",
    [string]$Username = "job_agent_user",
    [string]$Password = "",
    [string]$HostName = "localhost",
    [int]$Port = 5432,
    [string]$BackupDir = "F:\job wala project\storage\backups"
)

$ErrorActionPreference = "Stop"

if (-not $Password) {
    if ($env:PGPASSWORD) {
        $Password = $env:PGPASSWORD
    } elseif (Test-Path "F:\job wala project\.env") {
        $envMatch = Select-String -Path "F:\job wala project\.env" -Pattern "DATABASE_URL=postgresql://[^:]+:([^@]+)@"
        if ($envMatch -and $envMatch.Matches.Groups.Count -gt 1) {
            $Password = $envMatch.Matches.Groups[1].Value
        }
    }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " [Job Operating System] Local Database Backup Procedure   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# Locate pg_dump.exe
$pgDump = Get-Command pg_dump.exe -ErrorAction SilentlyContinue
if (-not $pgDump) {
    $fallbackPaths = @(
        "F:\All Code installs\PostgreSQL17\17\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
    )
    foreach ($p in $fallbackPaths) {
        if (Test-Path $p) {
            $pgDump = $p
            break
        }
    }
} else {
    $pgDump = $pgDump.Source
}

if (-not $pgDump -or -not (Test-Path $pgDump)) {
    Write-Error "pg_dump.exe not found. Please verify PostgreSQL is installed and in PATH."
    exit 1
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $BackupDir "${Database}_backup_${timestamp}.sql"

Write-Host "Database  : $Database"
Write-Host "User      : $Username"
Write-Host "Target    : $backupFile"
Write-Host "pg_dump   : $pgDump"

$env:PGPASSWORD = $Password
try {
    & $pgDump -h $HostName -p $Port -U $Username -d $Database --clean --if-exists --no-owner --no-privileges -f $backupFile
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump failed with exit code $LASTEXITCODE"
    }

    $fileItem = Get-Item $backupFile
    $sizeKb = [math]::Round($fileItem.Length / 1KB, 2)
    Write-Host "[OK] Backup completed successfully!" -ForegroundColor Green
    Write-Host "  File: $($fileItem.FullName)" -ForegroundColor Gray
    Write-Host "  Size: $sizeKb KB" -ForegroundColor Gray
}
catch {
    Write-Error ("Database backup failed: " + $_.ToString())
    exit 1
}
finally {
    $env:PGPASSWORD = $null
}
