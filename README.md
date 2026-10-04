# Personal Job Operating System — Local Production Deployment (₹0, 100% Local)

> **CURRENT STATUS: STEP 13 COMPLETE & PRODUCTION READY**
> 
> *Scope*: Complete end-to-end Job Operating System operating 100% locally on Windows, zero cloud compute costs, zero paid APIs, strictly isolated to the **`F:` drive** (`F:\job wala project`).

---

## 1. Local Production Architecture

```text
Windows 11 Workstation (F: Drive Only)
│
├── Frontend (React 19 + TypeScript + Vite) ──> http://localhost:5173
├── Backend API (FastAPI + Uvicorn)          ──> http://localhost:8000
├── Local Database (PostgreSQL 17)            ──> localhost:5432 (job_agent_db)
├── Autonomous Worker Daemon                  ──> workers/worker_daemon.py
├── Autonomous Scheduler Daemon               ──> workers/scheduler_daemon.py
├── Sandboxed Browser Engine (Playwright)     ──> browser/local_browser.py
├── Local Documents & Resumes                 ──> storage/documents/
├── Local Screenshots & Evidence              ──> storage/screenshots/
├── Automated Database Backups                ──> storage/backups/
└── Production Logs                           ──> logs/
```

---

## 2. One-Command Operational Control

The system provides unified Windows scripts and shortcuts for complete lifecycle management:

| Operation | Command Line (PowerShell) | Quick Batch Shortcut | Description |
|---|---|---|---|
| **Start System** | `powershell scripts\start.ps1` | `.\start.cmd` | Pre-flight check, migration check, starts all 4 components in background, displays status. |
| **Start Foreground** | `powershell scripts\start.ps1 -Foreground` | — | Starts process supervisor in foreground with live console logs. Stop with `Ctrl+C`. |
| **Check Status** | `powershell scripts\status.ps1` | `.\status.cmd` | Inspects live PIDs, ports, memory usage, database telemetry, queue counts, browser engine. |
| **Stop System** | `powershell scripts\stop.ps1` | `.\stop.cmd` | Gracefully terminates supervisor, backend, worker, scheduler, frontend, and frees ports. |
| **Restart System** | `powershell scripts\restart.ps1` | `.\restart.cmd` | Cleanly stops all components and restarts them with fresh health checks. |
| **Backup DB** | `powershell scripts\backup_db.ps1` | — | Creates timestamped SQL dump in `storage/backups/` using `pg_dump` on `F:`. |
| **Restore DB** | `powershell scripts\restore_db.ps1` | — | Safe database restore with mandatory explicit confirmation prompt. |

---

## 3. Strict F: Drive Isolation & Zero-Cost Architecture

In strict compliance with project policy, no application data, caches, or browser binaries spill onto `C:` or other drives:
1. **Virtual Environment**: Isolated in `F:\job wala project\.venv`.
2. **Playwright Chromium**: Downloaded and cached exclusively in `F:\job wala project\.cache\ms-playwright`.
3. **npm Cache**: Configured via `npm_config_cache` to `F:\job wala project\.cache\npm`.
4. **pip Cache**: Configured via `PIP_CACHE_DIR` to `F:\job wala project\.cache\pip`.
5. **Temporary Files**: Directed via `TMPDIR`, `TEMP`, `TMP` to `F:\job wala project\tmp`.
6. **Logs**: Rotating file handlers writing to `F:\job wala project\logs\`.
7. **PostgreSQL**: Local service `postgresql-x64-17` with binaries on `F:\All Code installs\PostgreSQL17\17\bin\`. Dedicated application user `job_agent_user`.

---

## 4. Safety Architecture & Controlled Autonomy (Step 12 Invariants)

The background worker and scheduler operate under strict safety constraints:
- **`APPLICATION != PERMISSION TO SUBMIT`**: An application record in `NOT_STARTED` is NEVER auto-submitted.
- **`APPLY != SUBMIT`**: An automated decision of `APPLY` initiates preparation, not submission.
- **`READY != SUBMIT`**: A preparation marked `READY` requires an explicit, unexpired, cryptographic `APPROVED` human approval token.
- **Strict Halt at Barriers**: Automated execution halts immediately at CAPTCHAs, bot verification, login walls, or unconfirmed sensitive profile fields.
- **Durable Queue**: Managed in PostgreSQL using `SELECT ... FOR UPDATE SKIP LOCKED` with automatic lease recovery (>300s timeout) and exponential backoff retry.
- **Conservative Scheduling**: Scheduler runs every 60s, discovery runs default to every 6 hours, and daily maintenance checks handle staleness and follow-ups.

---

## 5. System Verification & Regression Suite

To run the complete automated test suite (225 passing tests):
```powershell
& "F:\job wala project\.venv\Scripts\python.exe" -m pytest backend/tests -v
```

To run Step 13 local deployment verification tests:
```powershell
& "F:\job wala project\.venv\Scripts\python.exe" -m pytest backend/tests/test_local_deployment_step13.py -v
```
