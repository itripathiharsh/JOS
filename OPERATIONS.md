# Job Operating System — Operations Guide

A short, practical guide for managing the daily operation of the Job Operating System.

---

## 1. System Control Commands

The system is managed through one-command Windows shortcuts in the project root:

### Start the System
```cmd
start.cmd
```
*Launches the Supervisor in the background, verifies database connection and migrations, and starts the FastAPI backend, Background Worker, Background Scheduler, and React/Vite Frontend.*

### Check System Status
```cmd
status.cmd
```
*Displays real-time process PIDs, listening ports, memory consumption, PostgreSQL health, Step 12 automation task queue counts, and Playwright Chromium engine availability.*

### Restart the System
```cmd
restart.cmd
```
*Terminates all running components gracefully, verifies network port release, and restarts the complete stack.*

### Stop the System
```cmd
stop.cmd
```
*Terminates the supervisor and child components in reverse dependency order (Frontend → Scheduler → Worker → Backend) and releases ports 8000 and 5173.*

---

## 2. Daily Usage Workflow

Recommended daily operating routine:

1. **Start System**: Run `start.cmd` from the project directory.
2. **Open Dashboard**: Navigate to `http://localhost:5173` in your browser.
3. **Review Opportunities**: Inspect newly discovered jobs on the Jobs page (`http://localhost:5173/jobs`).
4. **Evaluate Decisions**: Review automated `APPLY`, `REVIEW`, and `SKIP` classifications with explainable fit scores.
5. **Prepare Applications**: Generate tailored resume recommendations, cover letters, and screening answers for high-fit opportunities.
6. **Review Generated Material**: Validate accuracy and alignment in the Application Preparation modal.
7. **Approve Manually**: Issue an explicit human approval token (`Approval Gate`). Real external submission is strictly blocked without this step.
8. **Execute Submission**: Run the supervised browser executor in Assisted or Automated mode.
9. **Track Outcomes**: Log interview invitations, assessments, notes, and final outcomes on the Applications page (`http://localhost:5173/applications`).
10. **Stop System**: Run `stop.cmd` when daily work is complete.

---

## 3. Database Backup & Recovery

### Create a Backup
To create a complete, timestamped PostgreSQL backup:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\backup_db.ps1
```
* Backups are saved strictly under: `storage\backups\job_agent_db_backup_<YYYYMMDD_HHMMSS>.sql` on the `F:` drive.
* Backups contain zero plain-text application passwords or secrets.

### Restore from Backup
To restore a backup into the database:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore_db.ps1
```
* For safety, the script interactively prompts you to type `RESTORE` before making changes.
* You can also specify an exact backup file:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore_db.ps1 -BackupFile "storage\backups\job_agent_db_backup_20261005_185109.sql"
```

---

## 4. Troubleshooting Sequence ("If Something Breaks")

If a component is unresponsive, follow this sequence:

1. **Check Status**:
   Run `status.cmd`. Verify which component is marked `STOPPED` or if ports `8000` / `5173` are not listening.
2. **Restart**:
   Run `restart.cmd` to clean lingering processes and restart the stack.
3. **Check Backend Health**:
   Open `http://localhost:8000/api/health` in your browser. Expected response:
   ```json
   {"status": "ok", "database": "connected", "environment": "local_production", "version": "1.0.0"}
   ```
4. **Check Logs**:
   Inspect the relevant log files in `logs/`:
   * Backend: `logs\backend.log` and `logs\backend_stderr.log`
   * Worker: `logs\worker.log` and `logs\worker_stdout.log`
   * Scheduler: `logs\scheduler.log`
   * Frontend: `logs\frontend_stdout.log`
   * Supervisor: `logs\supervisor.log`
5. **Check PostgreSQL**:
   Verify PostgreSQL service is running locally on port `5432`:
   ```powershell
   Get-Service -Name postgresql*
   ```
6. **Restore Backup**:
   Only as a last resort in case of irreversible database corruption, restore the latest verified backup using `scripts\restore_db.ps1`.

---

## 5. Important Safety Rule

> [!CAUTION]
> **Never manually modify production database records directly with raw SQL updates unless absolutely necessary.**
> 
> The Job Operating System enforces relational integrity, immutable memory snapshots, and strict lifecycle state machines (`NOT_STARTED` → `PREPARING` → `AWAITING_APPROVAL` → `SUBMITTING` → `SUBMITTED`). Manual row edits can invalidate provenance chains and corrupt state machine transitions.
