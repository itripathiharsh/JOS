"""
Job Operating System - Production Process Supervisor
100% Local, Zero-Cost, Strict F: Drive Architecture.
Orchestrates:
  1. PostgreSQL Health & Schema Migration Check
  2. FastAPI Backend (port 8000)
  3. Controlled Background Worker Daemon
  4. Controlled Background Scheduler Daemon
  5. React/Vite Frontend (port 5173)
"""
import sys
import os
import time
import signal
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Workspace Root
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
LOGS_DIR = ROOT_DIR / "logs"
TMP_DIR = ROOT_DIR / "tmp"
PIDS_FILE = TMP_DIR / "pids.json"

# Python and Node executables
VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
NPM_CMD = "npm.cmd" if sys.platform == "win32" else "npm"

# Environment Variables on F: Drive
os.environ["WORKSPACE_ROOT"] = str(ROOT_DIR)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(ROOT_DIR / ".cache" / "ms-playwright")
os.environ["npm_config_cache"] = str(ROOT_DIR / ".cache" / "npm")
os.environ["PIP_CACHE_DIR"] = str(ROOT_DIR / ".cache" / "pip")
os.environ["TMPDIR"] = str(TMP_DIR)
os.environ["TEMP"] = str(TMP_DIR)
os.environ["TMP"] = str(TMP_DIR)
os.environ["PYTHONPATH"] = f"{BACKEND_DIR};{ROOT_DIR}"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

LOGS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

_children: Dict[str, subprocess.Popen] = {}
_stop_requested = False


def log(msg: str, prefix: str = "SUPERVISOR"):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{prefix}] {msg}", flush=True)


def handle_shutdown(signum=None, frame=None):
    global _stop_requested
    if _stop_requested:
        return
    _stop_requested = True
    log("Shutdown signal received. Stopping all components gracefully...", "SHUTDOWN")

    # Stop in reverse order: Frontend -> Scheduler -> Worker -> Backend
    shutdown_order = ["frontend", "scheduler", "worker", "backend"]
    for name in shutdown_order:
        proc = _children.get(name)
        if proc and proc.poll() is None:
            log(f"Stopping [{name}] (PID: {proc.pid})...", "SHUTDOWN")
            try:
                proc.terminate()
            except Exception as e:
                log(f"Could not terminate [{name}]: {e}", "WARNING")

    # Give processes up to 5 seconds to terminate gracefully
    deadline = time.time() + 5.0
    for name in shutdown_order:
        proc = _children.get(name)
        if proc and proc.poll() is None:
            remaining = max(0.1, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
                log(f"Component [{name}] stopped cleanly.", "SHUTDOWN")
            except subprocess.TimeoutExpired:
                log(f"Component [{name}] did not exit in time. Killing forcefully...", "WARNING")
                try:
                    proc.kill()
                except Exception:
                    pass

    # Remove PID file
    if PIDS_FILE.exists():
        try:
            PIDS_FILE.unlink()
        except Exception:
            pass

    log("All components stopped. System shutdown complete.", "SHUTDOWN")
    sys.exit(0)


def preflight_check() -> bool:
    """Verifies PostgreSQL connectivity, schema status, and directories."""
    log("Running pre-flight checks...", "PREFLIGHT")
    try:
        from database.init_db import ensure_database_and_user, run_migrations, verify_database_health
        ensure_database_and_user()
        run_migrations()
        if not verify_database_health():
            log("Database health check failed.", "ERROR")
            return False
        log("Database check passed.", "PREFLIGHT")
    except Exception as e:
        log(f"Pre-flight database check error: {e}", "ERROR")
        return False

    # Check frontend build
    dist_index = FRONTEND_DIR / "dist" / "index.html"
    if not dist_index.exists():
        log("Frontend production build not found. Running 'npm run build'...", "PREFLIGHT")
        res = subprocess.run([NPM_CMD, "run", "build"], cwd=str(FRONTEND_DIR))
        if res.returncode != 0:
            log("Frontend build failed.", "ERROR")
            return False
        log("Frontend production build ready.", "PREFLIGHT")

    return True


def spawn_component(name: str, cmd: List[str], cwd: Path, port: int = None) -> subprocess.Popen:
    stdout_file = open(LOGS_DIR / f"{name}_stdout.log", "a", encoding="utf-8")
    stderr_file = open(LOGS_DIR / f"{name}_stderr.log", "a", encoding="utf-8")

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=stdout_file,
        stderr=stderr_file,
        env=os.environ.copy()
    )
    _children[name] = proc
    log(f"Started [{name}] (PID: {proc.pid})", "LAUNCH")
    return proc


def record_pids(ports: Dict[str, int]):
    pids_data = {
        "supervisor": {
            "pid": os.getpid(),
            "log": str(LOGS_DIR / "supervisor.log"),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    }
    for name, proc in _children.items():
        pids_data[name] = {
            "pid": proc.pid,
            "port": ports.get(name),
            "log": str(LOGS_DIR / f"{name}_stdout.log"),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    with open(PIDS_FILE, "w", encoding="utf-8") as f:
        json.dump(pids_data, f, indent=2)


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    print("=" * 72)
    print("         JOB OPERATING SYSTEM - LOCAL PRODUCTION SUPERVISOR")
    print("         100% Local | Zero-Cost Infrastructure | F: Drive Isolated")
    print("=" * 72)

    if not preflight_check():
        log("Pre-flight checks failed. Aborting startup.", "ERROR")
        sys.exit(1)

    py_exe = str(VENV_PYTHON)

    # 1. FastAPI Backend (port 8000)
    spawn_component(
        name="backend",
        cmd=[py_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR,
        port=8000
    )

    # 2. Worker Daemon
    spawn_component(
        name="worker",
        cmd=[py_exe, "-m", "workers.worker_daemon"],
        cwd=ROOT_DIR
    )

    # 3. Scheduler Daemon
    spawn_component(
        name="scheduler",
        cmd=[py_exe, "-m", "workers.scheduler_daemon"],
        cwd=ROOT_DIR
    )

    # 4. Frontend (port 5173)
    spawn_component(
        name="frontend",
        cmd=[NPM_CMD, "run", "preview", "--", "--port", "5173", "--host", "127.0.0.1"],
        cwd=FRONTEND_DIR,
        port=5173
    )

    ports = {"backend": 8000, "frontend": 5173}
    record_pids(ports)

    log("=" * 55, "STATUS")
    log("All components initialized and supervised.", "STATUS")
    log("  Frontend Dashboard : http://localhost:5173", "STATUS")
    log("  FastAPI Swagger UI : http://localhost:8000/docs", "STATUS")
    log("  Telemetry Status   : http://localhost:8000/api/automation/status", "STATUS")
    log("  Logs Directory     : " + str(LOGS_DIR), "STATUS")
    log("Press Ctrl+C to stop all components cleanly.", "STATUS")
    log("=" * 55, "STATUS")

    # Supervisor Health Monitor Loop
    while not _stop_requested:
        time.sleep(2.0)
        for name, proc in list(_children.items()):
            ret = proc.poll()
            if ret is not None and not _stop_requested:
                log(f"Component [{name}] exited unexpectedly with return code {ret}!", "WARNING")
                # Attempt automatic restart of exited worker or scheduler
                if name in ("worker", "scheduler"):
                    log(f"Restarting [{name}] daemon...", "RECOVERY")
                    cmd = [py_exe, "-m", f"workers.{name}_daemon"]
                    spawn_component(name, cmd, ROOT_DIR)
                    record_pids(ports)


if __name__ == "__main__":
    main()
