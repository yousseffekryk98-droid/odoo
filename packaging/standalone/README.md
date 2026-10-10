# TEQ ERP standalone Windows installer

## One setup EXE, no separate Python or PostgreSQL installation

The GitHub Actions workflow builds **TEQ-ERP-Setup.exe** with bundled Odoo, Python 3.12 (embedded distribution), PostgreSQL 17 Windows binaries, and required Python packages.

Download the installer artifact from [GitHub Actions](https://github.com/yousseffekryk98-droid/odoo/actions). Extract the artifact ZIP and run **TEQ-ERP-Setup.exe**. On Windows 10/11 64-bit, follow the installer wizard and click **TEQ ERP** on the desktop or Start menu.

At first launch, the program initializes a private local PostgreSQL database and creates a non-superuser database role. Initializing the Odoo database can take several minutes. The application opens in your default browser at **http://127.0.0.1:8069/web**.

No StackBuilder, PowerShell commands, external Python, PostgreSQL install, internet access, or manual passwords are required on the destination Windows computer once the installer has been downloaded.

## Data and compatibility

All records, file attachments, PostgreSQL data, and configuration are saved outside the install directory under **%LOCALAPPDATA%\TEQ-ERP-Standalone**. The installer and uninstaller do not intentionally erase them.

This standalone installation uses private PostgreSQL port 55439 and Odoo web port 8069 bound to localhost. Ports must be free. The previous locally installed Odoo/PostgreSQL data is **not** automatically migrated. Stop old servers listening on port 8069 first.

This is a Windows x64 installer, not a portable executable that runs on macOS or Linux. The application uses a browser for the Odoo interface and a console to control its local server. The installer is currently unsigned and may show a Windows security prompt.

The initial Odoo administrator account may retain a default password set by Odoo's database initialization. **Change this password immediately** after the first login. For any sensitive business data, back up the PostgreSQL data and attachments while the application is stopped, and keep the PC secured.

## Technical implementation and verification

Build source: branch **build/teq-standalone-windows** based on **audit/teq-egypt-localization-2026-09-30** plus packaging fixes. The official Odoo default branch 19.0 is untouched. The TEQ branches were not merged by this packaging work.

The installer bundles PostgreSQL from an EnterpriseDB binary ZIP and verifies the vendor-reported SHA-256. Python is the official embeddable build and dependencies are installed into its vendor site-packages. Build checks include importing Odoo using the packaged Python runtime. An EXE compilation by itself does not guarantee successful operation; check Windows first-run acceptance tests before production use.

Known limitations: printing PDFs and selected Odoo integrations can still require additional external tools or internet access. The app launches a private database when run and stops it when closed; the database is not a shared Windows system service.
