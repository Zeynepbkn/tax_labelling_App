param(
    [string]$DatabaseUrl = "",
    [string]$OutputDirectory = "backups"
)

$ErrorActionPreference = "Stop"

$BackendRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$EnvPath = Join-Path $BackendRoot ".env"

if ([string]::IsNullOrWhiteSpace($DatabaseUrl) -and (Test-Path $EnvPath)) {
    $line = Get-Content $EnvPath | Where-Object { $_ -match "^DATABASE_URL=" } | Select-Object -First 1
    if ($line) {
        $DatabaseUrl = $line.Substring("DATABASE_URL=".Length)
    }
}

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $DatabaseUrl = Read-Host "Paste Neon DATABASE_URL"
}

$PgDumpCandidates = @(
    "pg_dump.exe",
    "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
    "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
    "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
    "C:\Program Files\PostgreSQL\14\bin\pg_dump.exe"
)

$PgDump = $null
foreach ($candidate in $PgDumpCandidates) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) {
        $PgDump = $cmd.Source
        break
    }
    if (Test-Path $candidate) {
        $PgDump = $candidate
        break
    }
}

if (-not $PgDump) {
    throw "pg_dump was not found. Install PostgreSQL client tools first."
}

$BackupDir = Join-Path $BackendRoot $OutputDirectory
New-Item -ItemType Directory -Force $BackupDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputPath = Join-Path $BackupDir "taxlabeltr_neon_$Timestamp.dump"

& $PgDump --dbname="$DatabaseUrl" --format=custom --file="$OutputPath"

Write-Host "Backup created: $OutputPath"
