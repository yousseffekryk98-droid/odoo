"""Launch the locally installed TEQ ERP Odoo server and open the browser.

The packaged EXE is a launcher, not a self-contained Odoo/PostgreSQL runtime.
"""
from __future__ import annotations

import configparser
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "TEQ-ERP"


def ensure_config(config: Path, data: Path) -> None:
    if config.exists():
        # Repair the malformed, literal backslash-n format of the first launcher.
        contents = config.read_text(encoding="utf-8-sig")
        if "\\n" in contents and "\n" not in contents:
            repaired = contents.replace("\\n", "\n")
            backup = config.with_suffix(".conf.old")
            if not backup.exists():
                backup.write_text(contents, encoding="utf-8")
            config.write_text(repaired, encoding="utf-8")
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(config, encoding="utf-8-sig")
            if not parser.has_section("options"):
                raise ValueError("Missing [options] section")
        except (configparser.Error, ValueError) as exc:
            raise SystemExit(f"Invalid Odoo configuration at {config}: {exc}")
        return

    data_dir = data / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "[options]\n"
        "http_interface = 127.0.0.1\n"
        "http_port = 8069\n"
        f"data_dir = {data_dir.as_posix()}\n"
        "db_host = 127.0.0.1\n"
        "db_port = 5432\n"
        "db_user = postgres\n"
        "# Set db_password using setup-local.ps1 before first use.\n",
        encoding="utf-8",
    )


def main() -> int:
    root = app_root()
    python = root / ".venv" / "Scripts" / "python.exe"
    odoo = root / "odoo-bin"
    setup = root / "setup-local.ps1"
    if not odoo.is_file():
        print("ERROR: odoo-bin is missing; extract the COMPLETE Windows build ZIP.")
        return 1
    if not python.is_file():
        print(f"ERROR: Python environment is missing: {python}")
        print(f"Run setup-local.ps1 in PowerShell first: {setup}")
        return 1

    data = data_root()
    data.mkdir(parents=True, exist_ok=True)
    config = data / "odoo.conf"
    ensure_config(config, data)
    logs = data / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logfile = logs / "odoo.log"

    print(f"Using configuration: {config}")
    print(f"Server log: {logfile}")
    print("Starting Odoo on 127.0.0.1:8069 ...")
    log_stream = logfile.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [str(python), str(odoo), "--config", str(config)],
        cwd=str(root),
        stdout=log_stream,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    try:
        ready = False
        for _ in range(90):
            if process.poll() is not None:
                print(f"ERROR: Odoo exited with code {process.returncode}.")
                print(f"Review the last lines of {logfile} for the root cause.")
                return process.returncode or 1
            try:
                with urllib.request.urlopen("http://127.0.0.1:8069/web", timeout=2):
                    ready = True
                    break
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(1)
        if not ready:
            print("ERROR: Odoo did not respond on localhost:8069.")
            print(f"Check PostgreSQL and the log file: {logfile}")
            return 1
        url = "http://127.0.0.1:8069/web"
        print(f"TEQ ERP running at {url}")
        webbrowser.open(url)
        print("Keep this window open while using the app. Press Ctrl+C to stop.")
        return process.wait()
    except KeyboardInterrupt:
        print("Stopping TEQ ERP...")
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
        log_stream.close()


if __name__ == "__main__":
    sys.exit(main())
