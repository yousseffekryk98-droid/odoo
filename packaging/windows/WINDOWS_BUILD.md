# TEQ ERP Windows launcher and offline data

**Branch:** build/teq-windows-exe (based on audit/teq-egypt-localization-2026-09-30). The original Odoo 19.0 branch is unchanged. This build does **not** merge other TEQ branches.

## How to download

This repository's default branch is 19.0. The new workflow is on this build branch, so **do not depend on the "Run workflow" button**; manual dispatch can be unavailable until a workflow exists on the default branch.

1. Open https://github.com/yousseffekryk98-droid/odoo/actions
2. In **All workflows**, find the latest **Build TEQ Windows EXE** run on branch **build/teq-windows-exe**. Pushes to this branch automatically trigger the workflow.
3. The run must be green/successful before artifacts are downloadable.
4. Download **TEQ-ERP-Windows** for the complete app-source package. GitHub downloads this artifact as a ZIP.
5. There is also **TEQ-ERP-Launcher-EXE**, containing only the executable. **That EXE alone cannot run Odoo** without the rest of the package and local prerequisites.

If no run appears, check whether GitHub Actions is enabled for the repository. If a run is red, open the failing step and use its logs to diagnose the build failure.

## Windows setup (first launch)

1. Extract the **entire** TEQ-ERP-Windows artifact to a permanent directory such as C:\TEQ-ERP. Do not run TEQ-ERP.exe from inside the ZIP.
2. Install **Python 3.12 (Windows)** including the Python Launcher (py), and install **PostgreSQL locally**. Remember the password for the postgres database role. Start the PostgreSQL Windows service on port 5432.
3. Open PowerShell in the extracted directory and run:

    powershell -ExecutionPolicy Bypass -File .\setup-local.ps1

4. During setup, enter the local PostgreSQL postgres password. The setup saves a local configuration and prints the Odoo database-manager master password; keep it safe.
5. Double-click TEQ-ERP.exe. The local Odoo server starts and your browser opens at http://127.0.0.1:8069/web. Keep the launcher window open during use.

The first setup requires internet access to download Python packages. After a successful setup, normal use can operate locally, subject to Odoo features that depend on external services.

## Local storage and backups

- **Database:** local PostgreSQL server. This contains the important business records.
- **Odoo files:** %LOCALAPPDATA%\TEQ-ERP\data.
- **Odoo configuration:** %LOCALAPPDATA%\TEQ-ERP\odoo.conf.
- **Odoo startup log:** %LOCALAPPDATA%\TEQ-ERP\logs\odoo.log.

Closing the app does not erase these. **Back up both the PostgreSQL database and Odoo data directory.** Do not store only a copy of the executable and assume it contains the data.

## Troubleshooting

- **Workflow not found / no Run workflow button:** This workflow is only on the build branch. Open the repository's main Actions page and look for the automatic push run.
- **EXE says "odoo-bin missing":** Extract the full TEQ-ERP-Windows artifact, not the launcher-only artifact.
- **EXE says ".venv" missing:** Run setup-local.ps1 after installing Python 3.12.
- **The server stops or browser cannot connect:** Check logs\odoo.log, confirm PostgreSQL is running, and check credentials in odoo.conf.
- **Could not install requirements:** Some Python/Odoo native dependencies may need additional Windows build prerequisites. Read the pip error; an EXE launcher cannot solve broken Python dependencies by itself.
- **Database connection failed:** Verify db_host, db_port, db_user and db_password in odoo.conf. The default local PostgreSQL role is postgres.
- **The old launcher corrupted the config:** The updated launcher converts the original malformed literal backslash-n sequences into real newlines and saves a .conf.old backup.

## Limitations

This is **not yet a standalone Windows installer**. The .exe is a Windows launcher for the Odoo Python process; PostgreSQL and Python dependencies must be set up locally. The GitHub build compiles the launcher but does not run end-to-end ERP acceptance tests. Only claim the application works once it has been started and tested on a real Windows machine.
