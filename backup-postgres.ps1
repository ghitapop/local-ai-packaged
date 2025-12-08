# PostgreSQL Backup Script for Windows (PowerShell)
# This script creates full database backups of all databases in the PostgreSQL container

param(
    [int]$RetentionDays = 7
)

# Configuration
$BackupDir = ".\backups\postgres"
$ContainerName = "postgres"
$Date = Get-Date -Format "yyyyMMdd_HHmmss"

# Create backup directory if it doesn't exist
if (!(Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

Write-Host "Starting PostgreSQL backup at $(Get-Date)" -ForegroundColor Green

# Check if container is running
$ContainerRunning = docker ps --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$"
if (!$ContainerRunning) {
    Write-Host "Error: PostgreSQL container '$ContainerName' is not running" -ForegroundColor Red
    exit 1
}

# Backup all databases using pg_dumpall
Write-Host "Creating full backup of all databases..."
$BackupFile = "$BackupDir\full_backup_$Date.sql"
docker exec $ContainerName pg_dumpall -U postgres | Out-File -FilePath $BackupFile -Encoding utf8

if ($LASTEXITCODE -eq 0) {
    # Compress the backup
    Compress-Archive -Path $BackupFile -DestinationPath "$BackupFile.zip" -Force
    Remove-Item $BackupFile

    $BackupSize = (Get-Item "$BackupFile.zip").Length / 1MB
    Write-Host "[SUCCESS] Full backup created: $BackupFile.zip" -ForegroundColor Green
    Write-Host "  Backup size: $([math]::Round($BackupSize, 2)) MB"
} else {
    Write-Host "[FAILED] Backup failed!" -ForegroundColor Red
    exit 1
}

# Clean up old backups
Write-Host "Cleaning up backups older than $RetentionDays days..."
$CutoffDate = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -Path $BackupDir -Filter "*.zip" | Where-Object { $_.LastWriteTime -lt $CutoffDate } | Remove-Item
Write-Host "[SUCCESS] Cleanup complete" -ForegroundColor Green

# List recent backups
Write-Host ""
Write-Host "Recent backups:"
Get-ChildItem -Path $BackupDir -Filter "*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | Format-Table Name, Length, LastWriteTime

Write-Host ""
Write-Host "Backup completed successfully at $(Get-Date)" -ForegroundColor Green
