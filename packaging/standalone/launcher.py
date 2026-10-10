"""One-click offline TEQ ERP launcher with bundled PostgreSQL and Python."""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import traceback
import urllib.request
import urllib.error
import webbrowser

PORT = 55439
ODOO_PORT = 8069
ADMIN = "teq_admin"
ROLE = "teq_odoo"
DB = "teq_erp"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def installation() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]


def storage() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or str(Path.home())) / "TEQ-ERP-Standalone"


def run(args, env=None, timeout=120):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True, errors="replace", env=env, timeout=timeout, creationflags=CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed ({result.returncode}):\n{(result.stderr or result.stdout)[-2400:]}")
    return result.stdout.strip()


def pg_env(credentials, admin=False):
    env = os.environ.copy()
    env["PGPASSWORD"] = credentials["admin_password" if admin else "odoo_password"]
    env["PGCONNECT_TIMEOUT"] = "5"
    return env


def get_credentials(state):
    path = state / "credentials.json"
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        for key in ("admin_password", "odoo_password", "manager_password"):
            if not value.get(key):
                raise RuntimeError(f"Missing {key} in saved database credentials. Existing data was not changed.")
        return value
    value = {k: secrets.token_hex(24) for k in ("admin_password", "odoo_password", "manager_password")}
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return value


def get_components(root):
    python = root / "runtime" / "python" / "python.exe"
    pg = root / "runtime" / "postgres" / "bin"
    executables = {x: pg / f"{x}.exe" for x in ("initdb", "pg_ctl", "psql", "pg_isready", "createdb")}
    needed = [python, root / "odoo-bin", *(executables.values())]
    missing = [str(p) for p in needed if not p.is_file()]
    if missing:
        raise RuntimeError("Required bundled runtime files are missing:\n" + "\n".join(missing))
    return python, executables


def ensure_postgres(state, commands, credentials):
    data = state / "postgresql"
    if not (data / "PG_VERSION").is_file():
        if data.exists() and any(data.iterdir()):
            raise RuntimeError("The existing database folder is incomplete. Nothing was deleted: " + str(data))
        print("Setting up TEQ ERP's private local database (one time)...", flush=True)
        password_file = state / ".initdb-password"
        try:
            password_file.write_text(credentials["admin_password"] + "\n", encoding="ascii")
            run([commands["initdb"], "-D", data, "-U", ADMIN, "--encoding=UTF8",
                 "--auth-local=scram-sha-256", "--auth-host=scram-sha-256",
                 "--pwfile", password_file, "--no-instructions"], timeout=240)
        finally:
            password_file.unlink(missing_ok=True)
    ping = subprocess.run([str(commands["pg_isready"]), "-h", "127.0.0.1", "-p", str(PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
    started = False
    if ping.returncode:
        print("Starting bundled PostgreSQL...", flush=True)
        run([commands["pg_ctl"], "-D", data, "-l", state / "logs" / "postgres.log",
             "-o", f"-h 127.0.0.1 -p {PORT}", "-w", "start"])
        started = True
    options = ["-h", "127.0.0.1", "-p", str(PORT), "-U", ADMIN, "-d", "postgres"]
    exists = run([commands["psql"], *options, "-tAc", f"SELECT count(*) FROM pg_roles WHERE rolname='{ROLE}'"], env=pg_env(credentials, True))
    if exists == "0":
        print("Creating a safe, non-superuser database account...", flush=True)
        run([commands["psql"], *options, "-v", "ON_ERROR_STOP=1", "-c",
             f"CREATE ROLE {ROLE} LOGIN CREATEDB PASSWORD '{credentials['odoo_password']}'"],
            env=pg_env(credentials, True))
    return started


def write_config(root, state, passwords):
    paths = [root / "addons", root / "odoo" / "addons"]
    if (root / "custom_addons").exists():
        paths.append(root / "custom_addons")
    files = state / "files"
    files.mkdir(exist_ok=True)
    config = state / "odoo.conf"
    config.write_text(
        "[options]\n"
        "http_interface = 127.0.0.1\n"
        f"http_port = {ODOO_PORT}\n"
        f"db_host = 127.0.0.1\n"
        f"db_port = {PORT}\n"
        f"db_user = {ROLE}\n"
        f"db_password = {passwords['odoo_password']}\n"
        f"admin_passwd = {passwords['manager_password']}\n"
        f"db_name = {DB}\n"
        f"data_dir = {files.as_posix()}\n"
        f"addons_path = {','.join(x.as_posix() for x in paths)}\n"
        "list_db = False\n"
        "workers = 0\n",
        encoding="utf-8",
    )
    return config


def init_odoo(root, state, python, postgres, config, passwords):
    conn = ["-h", "127.0.0.1", "-p", str(PORT), "-U", ROLE]
    env = pg_env(passwords)
    found = run([postgres["psql"], *conn, "-d", "postgres", "-tAc",
                 f"SELECT count(*) FROM pg_database WHERE datname='{DB}'"], env=env)
    if found == "0":
        print("Creating the local TEQ ERP database...", flush=True)
        run([postgres["createdb"], *conn, DB], env=env)
    else:
        check = run([postgres["psql"], *conn, "-d", DB, "-tAc",
                     "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='ir_module_module'"], env=env)
        if check == "1":
            return
    print("Initializing Odoo for the first time (this may take a few minutes)...", flush=True)
    logfile = state / "logs" / "initialize.log"
    with logfile.open("w", encoding="utf-8") as stream:
        proc = subprocess.run([str(python), str(root / "odoo-bin"), "-c", str(config),
                               "-d", DB, "-i", "base", "--stop-after-init"],
                              cwd=str(root), stdout=stream, stderr=subprocess.STDOUT,
                              timeout=1200, creationflags=CREATE_NO_WINDOW)
    if proc.returncode:
        raise RuntimeError(f"Odoo database initialization failed (exit {proc.returncode}); see {logfile}")
    print("Database initialization complete.", flush=True)


def show_error(state, exception):
    message = str(exception)
    for name in ("logs/initialize.log", "logs/odoo.log", "logs/postgres.log"):
        filename = state / name
        if filename.is_file():
            lines = filename.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                message += "\n\n" + name + ":\n" + "\n".join(lines[-9:])[-1600:]
    message += f"\n\nDiagnostic logs: {state / 'logs'}"
    print(message, file=sys.stderr, flush=True)
    try:
        ctypes.windll.user32.MessageBoxW(None, message[-5000:], "TEQ ERP startup error", 0x10)
    except Exception:
        pass


def main():
    root = installation()
    state = storage()
    state.mkdir(parents=True, exist_ok=True)
    (state / "logs").mkdir(parents=True, exist_ok=True)
    print("TEQ ERP - offline Windows installation", flush=True)
    print(f"Saved data: {state}", flush=True)
    postgres = None
    started = False
    server = None
    try:
        python, postgres = get_components(root)
        creds = get_credentials(state)
        started = ensure_postgres(state, postgres, creds)
        config = write_config(root, state, creds)
        init_odoo(root, state, python, postgres, config, creds)
        print("Starting local TEQ ERP...", flush=True)
        logfile = state / "logs" / "odoo.log"
        with logfile.open("a", encoding="utf-8") as stream:
            server = subprocess.Popen([str(python), str(root / "odoo-bin"), "-c", str(config),
                                       "-d", DB], cwd=str(root), stdout=stream, stderr=subprocess.STDOUT,
                                      creationflags=CREATE_NO_WINDOW)
            ready = False
            for _ in range(180):
                if server.poll() is not None:
                    raise RuntimeError(f"Odoo stopped unexpectedly (exit {server.returncode})")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{ODOO_PORT}/web", timeout=2):
                        ready = True
                        break
                except (urllib.error.URLError, TimeoutError, OSError):
                    time.sleep(1)
            if not ready:
                raise RuntimeError("Odoo did not respond on localhost")
            url = f"http://127.0.0.1:{ODOO_PORT}/web"
            print(f"TEQ ERP is ready: {url}", flush=True)
            webbrowser.open(url)
            print("Keep this console open while using TEQ ERP.", flush=True)
            return server.wait()
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        traceback.print_exc()
        show_error(state, error)
        return 1
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=12)
            except subprocess.TimeoutExpired:
                server.kill()
        if started and postgres:
            try:
                run([postgres["pg_ctl"], "-D", state / "postgresql", "-m", "fast", "-w", "stop"], timeout=60)
            except Exception as error:
                print(f"Warning: PostgreSQL shutdown failed: {error}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
