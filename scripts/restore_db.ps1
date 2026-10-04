# Job Operating System - Local Database Restore Script
# STRICT SAFETY: Requires explicit confirmation before restoring data.
[CmdletBinding()]
param (
    [Parameter(Mandatory=$false)]
    [string]$BackupFile,

    [string]$Database = "job_agent_db",
    [string]$Username = "postgres",
    [string]$Password = "",
    [string]$HostName = "localhost",
    [int]$Port = 5432,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host " [Job Operating System] Local Database Restore Procedure  " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Yellow

$backupDir = "F:\job wala project\storage\backups"

# If no file specified, pick latest backup
if (-not $BackupFile) {
    $latest = Get-ChildItem -Path $backupDir -Filter "*.sql" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        Write-Error "No backup files found in $backupDir."
        exit 1
    }
    $BackupFile = $latest.FullName
}

if (-not (Test-Path $BackupFile)) {
    Write-Error "Specified backup file does not exist: $BackupFile"
    exit 1
}

# Locate psql.exe
$psql = Get-Command psql.exe -ErrorAction SilentlyContinue
if (-not $psql) {
    $fallbackPaths = @(
        "F:\All Code installs\PostgreSQL17\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\16\bin\psql.exe"
    )
    foreach ($p in $fallbackPaths) {
        if (Test-Path $p) {
            $psql = $p
            break
        }
    }
} else {
    $psql = $psql.Source
}

if (-not $psql -or -not (Test-Path $psql)) {
    Write-Error "psql.exe not found. Please verify PostgreSQL is installed."
    exit 1
}

Write-Host "Target Database : $Database" -ForegroundColor White
Write-Host "Backup File     : $BackupFile" -ForegroundColor White
Write-Host "psql Path       : $psql" -ForegroundColor White

if (-not $Force) {
    Write-Host "`n[WARNING] Restoring will overwrite existing tables in '$Database' with backup contents." -ForegroundColor Red
    $confirm = Read-Host "Type 'RESTORE' to confirm and proceed"
    if ($confirm -ne "RESTORE") {
        Write-Host "Restore cancelled by user. No changes were made." -ForegroundColor Green
        exit 0
    }
}

Write-Host "`nExecuting restore..." -ForegroundColor Cyan
if ($Password) {
    $env:PGPASSWORD = $Password
}

try {
    & $psql -h $HostName -p $Port -U $Username -d $Database -f $BackupFile
    if ($LASTEXITCODE -ne 0) {
        throw "psql restore failed with exit code $LASTEXITCODE"
    }
    Write-Host "[OK] Database restored successfully from: $BackupFile" -ForegroundColor Green
}
catch {
    Write-Error ("Database restore failed: " + $_.ToString())
    exit 1
}
finally {
    $env:PGPASSWORD = $null
}
