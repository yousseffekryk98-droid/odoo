"""TEQ ERP local Windows launcher. Requires Python dependencies and local PostgreSQL."""
from pathlib import Path
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser

def main():
    root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
    odoo = root / "odoo-bin"
    if not odoo.exists():
        sys.exit("odoo-bin missing. Extract the entire TEQ-ERP-Windows ZIP before running.")
    python = root / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        sys.exit("Python environment missing. Run setup-local.ps1 first (see WINDOWS_BUILD.md).")
    data = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "TEQ-ERP"
    data.mkdir(parents=True, exist_ok=True)
    config = data / "odoo.conf"
    if not config.exists():
        config.write_text("[options]\\nhttp_interface = 127.0.0.1\\nhttp_port = 8069\\ndata_dir = " + str(data / "filestore").replace("\\\\", "/") + "\\n", encoding="utf-8")
    process = subprocess.Popen([str(python), str(odoo), "-c", str(config)], cwd=str(root))
    try:
        for _ in range(60):
            if process.poll() is not None:
                sys.exit("Odoo stopped during startup. Check Python and PostgreSQL configuration.")
            try:
                urllib.request.urlopen("http://127.0.0.1:8069/web", timeout=1)
                break
            except Exception:
                time.sleep(2)
        webbrowser.open("http://127.0.0.1:8069/web")
        print("TEQ ERP running locally at http://127.0.0.1:8069/web")
        print("Press Ctrl+C to stop the server.")
        process.wait()
    except KeyboardInterrupt:
        process.terminate()

if __name__ == "__main__":
    main()
