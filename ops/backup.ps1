param(
    [Parameter(Mandatory = $true)][string]$DatabaseHost,
    [Parameter(Mandatory = $true)][string]$DatabaseName,
    [Parameter(Mandatory = $true)][string]$DatabaseUser,
    [Parameter(Mandatory = $true)][string]$BackupDirectory
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$destination = Join-Path $BackupDirectory $timestamp
New-Item -ItemType Directory -Path $destination -Force | Out-Null

$dumpPath = Join-Path $destination "$DatabaseName.sql"
& mysqldump --host=$DatabaseHost --user=$DatabaseUser --single-transaction --routines --triggers --databases $DatabaseName --result-file=$dumpPath
if ($LASTEXITCODE -ne 0) {
    throw "mysqldump failed with exit code $LASTEXITCODE"
}

$artifactPath = Join-Path $destination "ml-artifacts.zip"
$modelDirectory = Join-Path $PSScriptRoot "..\backend\app\ml\models"
if (Test-Path -LiteralPath $modelDirectory) {
    Compress-Archive -Path (Join-Path $modelDirectory "*") -DestinationPath $artifactPath -Force
}

Write-Output "Backup created at $destination"
