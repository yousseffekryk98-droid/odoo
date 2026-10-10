$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Install Python 3.12 and PostgreSQL locally first." }
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip wheel setuptools
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Write-Host "Dependencies installed. Ensure PostgreSQL is running and configure your local Odoo database."
