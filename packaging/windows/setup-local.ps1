# Run once in PowerShell after extracting the complete Windows artifact.
# Requires Python 3.12, PostgreSQL, and Internet access for pip dependencies.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
    if (-not (Test-Path ".\odoo-bin")) {
        throw "odoo-bin is missing. Extract the entire TEQ-ERP-Windows artifact first."
    }

    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw "Install Python 3.12 for Windows from python.org (enable the Python launcher)."
    }

    & py -3.12 -c "import sys; print(sys.version)"
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.12 was not found. Install it and try again."
    }

    if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create the Python virtual environment." }
    }

    $python = Join-Path $root ".venv\Scripts\python.exe"
    & $python -m pip install --upgrade pip wheel setuptools
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
    & $python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Odoo Python dependencies failed to install. See pip error above; some native prerequisites may be needed on Windows."
    }

    $data = Join-Path $env:LOCALAPPDATA "TEQ-ERP"
    $dataDir = Join-Path $data "data"
    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
    $config = Join-Path $data "odoo.conf"
    if (-not (Test-Path $config)) {
        Write-Host ""
        Write-Host "Enter your LOCAL PostgreSQL superuser password (for the 'postgres' role)."
        Write-Host "PostgreSQL must already be installed and running on port 5432."
        $securePassword = Read-Host "PostgreSQL password" -AsSecureString
        $credential = New-Object System.Management.Automation.PSCredential("postgres", $securePassword)
        $password = $credential.GetNetworkCredential().Password

        $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        $bytes = New-Object byte[] 24
        $random.GetBytes($bytes)
        $random.Dispose()
        $masterPassword = [System.BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
        $normalizedDataDir = $dataDir.Replace("\", "/")

        $configLines = @(
            "[options]"
            "http_interface = 127.0.0.1"
            "http_port = 8069"
            "data_dir = $normalizedDataDir"
            "db_host = 127.0.0.1"
            "db_port = 5432"
            "db_user = postgres"
            "db_password = $password"
            "admin_passwd = $masterPassword"
        )
        $configLines | Set-Content -Path $config -Encoding UTF8
        Write-Host ""
        Write-Host "IMPORTANT: Your Odoo database manager master password is:"
        Write-Host $masterPassword
        Write-Host "Keep it private. It is also stored in: $config"
        $password = $null
        $securePassword = $null
    }
    else {
        Write-Host "Reusing existing Odoo configuration: $config"
        Write-Host "If it was created with the old broken launcher, the updated EXE will repair the newline formatting."
    }

    Write-Host ""
    Write-Host "Setup complete. Start TEQ-ERP.exe."
    Write-Host "All Odoo business data stays in local PostgreSQL and the local Odoo data directory."
}
finally {
    Pop-Location
}
