param(
    [string]$DatabaseUrl = "",
    [string]$CorsOrigins = "*",
    [string]$AdminUsername = "admin",
    [string]$AdminEmail = "",
    [string]$AdminPassword = ""
)

$ErrorActionPreference = "Stop"

$BackendRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$EnvPath = Join-Path $BackendRoot ".env"

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $DatabaseUrl = Read-Host "Paste Neon DATABASE_URL"
}

if ($DatabaseUrl -notmatch "^postgres(ql)?://") {
    throw "DATABASE_URL must start with postgresql:// or postgres://"
}

if ($DatabaseUrl -notmatch "sslmode=require") {
    if ($DatabaseUrl.Contains("?")) {
        $DatabaseUrl = "$DatabaseUrl&sslmode=require"
    } else {
        $DatabaseUrl = "$DatabaseUrl?sslmode=require"
    }
}

if ([string]::IsNullOrWhiteSpace($AdminEmail)) {
    $AdminEmail = Read-Host "Admin email"
}

if ([string]::IsNullOrWhiteSpace($AdminPassword)) {
    $secure = Read-Host "Admin password" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $AdminPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

$AdminPasswordBytes = [System.Text.Encoding]::UTF8.GetByteCount($AdminPassword)
if ($AdminPasswordBytes -gt 72) {
    throw "Admin password is $AdminPasswordBytes bytes. Use 72 bytes or fewer because bcrypt has a 72-byte limit."
}

$SecretChars = (48..57) + (65..90) + (97..122)
$SecretKey = -join ($SecretChars | Get-Random -Count 72 | ForEach-Object { [char]$_ })

$EnvContent = @"
DATABASE_URL=$DatabaseUrl
SECRET_KEY=$SecretKey
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ADMIN_USERNAME=$AdminUsername
ADMIN_EMAIL=$AdminEmail
ADMIN_PASSWORD=$AdminPassword
QUIZ_PASSING_SCORE=80
CORS_ORIGINS=$CorsOrigins
"@

$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($EnvPath, $EnvContent, $Utf8NoBom)

Write-Host "Created $EnvPath"
Write-Host "Next:"
Write-Host "  cd `"$BackendRoot`""
Write-Host "  .\.venv\Scripts\alembic.exe upgrade head"
Write-Host "  .\.venv\Scripts\python.exe scripts\db_status.py"
