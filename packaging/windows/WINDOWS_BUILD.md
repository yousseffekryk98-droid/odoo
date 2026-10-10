# TEQ ERP Windows build

This branch is based on `audit/teq-egypt-localization-2026-09-30`. It does **not** merge the other TEQ branches and does not change Odoo `19.0`.

## Build
Open GitHub Actions > **Build TEQ Windows EXE** > **Run workflow** on `build/teq-windows-exe`. Download the `TEQ-ERP-Windows` artifact after a successful run.

## Install and run
1. Extract the complete ZIP to a permanent folder on Windows.
2. Install Python 3.12 and PostgreSQL locally; create a PostgreSQL role/database accessible to Odoo.
3. Open PowerShell in the extracted folder and run `powershell -ExecutionPolicy Bypass -File .\\setup-local.ps1`.
4. Double-click `TEQ-ERP.exe`. Odoo opens at http://127.0.0.1:8069/web.
5. Configure database credentials in `%LOCALAPPDATA%\\TEQ-ERP\\odoo.conf` as needed.

## Important limitations
The EXE is a Windows **launcher**, not a fully standalone offline installer. Python dependencies and PostgreSQL must be installed locally first. Odoo may require additional native tools depending on enabled modules. Data persists in PostgreSQL and Odoo's local data directory; back up **both**. The launcher is not a Windows service. This workflow does not automatically verify end-to-end Odoo startup.
