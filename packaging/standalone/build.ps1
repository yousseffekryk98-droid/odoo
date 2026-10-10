# Build a single offline Windows installer containing Odoo, Python and PostgreSQL.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repo
$work = Join-Path $repo '.teq-standalone-build'
$payload = Join-Path $work 'payload'
$pythonRuntime = Join-Path $payload 'runtime\python'
$postgresRuntime = Join-Path $payload 'runtime\postgres'
$dist = Join-Path $repo 'dist\standalone'
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory -Force $work, $payload, $pythonRuntime, $postgresRuntime, $dist | Out-Null

function Run-Checked([string]$exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $exe" }
}

Write-Host "1/5 Copying TEQ Odoo source and addons..."
foreach ($file in @('odoo-bin', 'requirements.txt', 'LICENSE', 'COPYRIGHT')) {
    Copy-Item (Join-Path $repo $file) (Join-Path $payload $file) -Force
}
foreach ($directory in @('odoo', 'addons')) {
    Copy-Item -Recurse -Force (Join-Path $repo $directory) (Join-Path $payload $directory)
}
if (Test-Path (Join-Path $repo 'custom_addons')) {
    Copy-Item -Recurse -Force (Join-Path $repo 'custom_addons') (Join-Path $payload 'custom_addons')
}
$upgrade = Join-Path $payload 'odoo\upgrade'
New-Item -ItemType Directory -Force $upgrade | Out-Null
'Keep this namespace directory in the Windows package.' | Set-Content (Join-Path $upgrade 'README.txt') -Encoding ascii

Write-Host "2/5 Bundling the official Python 3.12 Windows embedded runtime..."
$pythonUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
$pythonZip = Join-Path $work 'python-embed.zip'
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip
Expand-Archive -Path $pythonZip -DestinationPath $pythonRuntime -Force
$pth = Join-Path $pythonRuntime 'python312._pth'
if (!(Test-Path $pth)) { throw 'Missing python312._pth in embedded runtime.' }
@('python312.zip', '.', 'Lib\site-packages', '..\..', 'import site') | Set-Content -Path $pth -Encoding ascii
$site = Join-Path $pythonRuntime 'Lib\site-packages'
New-Item -ItemType Directory -Force $site | Out-Null
$hostPython = (Get-Command python).Source
Run-Checked $hostPython @('-m', 'pip', 'install', '--disable-pip-version-check', '--target', $site, '-r', (Join-Path $repo 'requirements.txt'))
Run-Checked $hostPython @('-m', 'pip', 'install', '--disable-pip-version-check', '--only-binary=:all:', '--target', $site, 'packaging')
Run-Checked (Join-Path $pythonRuntime 'python.exe') @('-c', 'import psycopg2, lxml, werkzeug, packaging; print("Embedded Python OK")')
Push-Location $payload
try {
    Run-Checked (Join-Path $pythonRuntime 'python.exe') @('odoo-bin', '--help')
} finally {
    Pop-Location
}

Write-Host "3/5 Downloading PostgreSQL Windows binaries and verifying vendor hash..."
$pgUrl = 'https://get.enterprisedb.com/postgresql/postgresql-17.11-3-windows-x64-binaries.zip'
$pgSha256 = '4b8db0930c38f6ef845db919551dedda3b6b845aeb0927b3d79a6e8e9e4537cf'
$pgZip = Join-Path $work 'postgres-windows.zip'
Invoke-WebRequest -Uri $pgUrl -OutFile $pgZip
$hash = (Get-FileHash -Algorithm SHA256 $pgZip).Hash.ToLowerInvariant()
if ($hash -ne $pgSha256) { throw "Vendor PostgreSQL checksum mismatch: $hash" }
$extracted = Join-Path $work 'postgres-extracted'
Expand-Archive -Path $pgZip -DestinationPath $extracted -Force
$initdb = Get-ChildItem $extracted -Filter 'initdb.exe' -File -Recurse | Select-Object -First 1
if (!$initdb) { throw 'No initdb.exe in downloaded PostgreSQL archive.' }
$source = $initdb.Directory.Parent.FullName
foreach ($directory in @('bin', 'lib', 'share')) {
    $from = Join-Path $source $directory
    if (!(Test-Path $from)) { throw "PostgreSQL archive missing $directory" }
    Copy-Item -Recurse -Force $from (Join-Path $postgresRuntime $directory)
}
Run-Checked (Join-Path $postgresRuntime 'bin\postgres.exe') @('--version')
Run-Checked (Join-Path $postgresRuntime 'bin\initdb.exe') @('--version')

Write-Host "4/5 Compiling TEQ-ERP.exe (launcher)..."
Run-Checked $hostPython @('-m', 'pip', 'install', '--disable-pip-version-check', 'pyinstaller')
Run-Checked $hostPython @('-m', 'PyInstaller', '--clean', '--onefile', '--console', '--name', 'TEQ-ERP', '--distpath', $payload, '--workpath', (Join-Path $work 'pyinstaller'), '--specpath', $work, (Join-Path $repo 'packaging\standalone\launcher.py'))
if (!(Test-Path (Join-Path $payload 'TEQ-ERP.exe'))) { throw 'TEQ-ERP.exe not generated.' }

Write-Host "5/5 Compressing standalone TEQ-ERP-Setup.exe..."
$iscc = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (!(Test-Path $iscc)) {
    Run-Checked 'choco' @('install', 'innosetup', '-y', '--no-progress')
}
if (!(Test-Path $iscc)) { throw 'Inno Setup compiler missing after Chocolatey install.' }
Run-Checked $iscc @('/Qp', "/DSourceDir=$payload", "/DOutputDir=$dist", (Join-Path $repo 'packaging\standalone\installer.iss'))
$exe = Join-Path $dist 'TEQ-ERP-Setup.exe'
if (!(Test-Path $exe)) { throw 'Standalone installer not generated.' }
Write-Host ("TEQ standalone installer produced: {0:N0} bytes" -f (Get-Item $exe).Length)
