# Job Operating System (JOS)

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React_19_%2B_TypeScript-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_17-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Playwright](https://img.shields.io/badge/Automation-Playwright-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An intelligent, self-hosted, human-in-the-loop autonomous platform for career opportunity discovery, multi-dimensional job matching, deterministic application preparation, and auditable lifecycle tracking.

---

## What This Is

The **Job Operating System (JOS)** is a personal, self-hosted system that transforms the chaotic job search into a structured, reliable, and auditable operating pipeline. Rather than acting as a blind "auto-apply bot" that floods job portals with low-quality, generic spam, JOS implements **Controlled Autonomy**: an engineering framework that automates data aggregation, deduplication, requirement extraction, and content preparation while reserving external application submission for verified, explicit human approval.

---

## Architecture

The system operates across a 5-tier architecture:

```text
React / Vite (Frontend UI - port 5173)
        ↓
FastAPI / Uvicorn (REST API - port 8000)
        ↓
PostgreSQL 17 (Relational Store & Queue - port 5432)
        ↓
Worker + Scheduler Daemons (Autonomous Polling & Ingestion)
        ↓
Playwright Chromium (Sandboxed Local Browser Engine)
```

### Major Intelligence Layers
1. **Normalization & Canonical Layer**: Normalizes job titles, seniority levels, work modes, and compensation ranges. Implements canonical clustering to group multi-portal duplicates into a single vacancy record.
2. **Deterministic Matching Engine**: Evaluates candidate fit across 8 independent weighted dimensions (Role 30%, Skills 35%, Experience 15%, Location 8%, Work Mode 4%, Salary 3%, Education 3%, Employment Type 2%). Hard seniority mismatches or missing mandatory qualifications impose score caps and demotions.
3. **Application Decision Engine**: Classifies each vacancy deterministically into `APPLY`, `REVIEW`, or `SKIP` with explicit confidence scores and structured rationale lists.
4. **Application Preparation Engine**: Maps candidate profile achievements directly to job requirements. Produces tailored resume highlights, personalized cover letters, and screening question answers without hallucinating capabilities.
5. **Controlled Execution Engine**: Supervised browser automation (Playwright) that validates field mapping, checks anti-automation barriers, captures screenshots, and requires version-locked approval tokens before submission.
6. **Application Memory & Feedback**: Maintains immutable snapshots of vacancies, candidate profiles, and preparation packages, recording an append-only timeline and outcome tracking (interviews, assessments, offers).

---

## Features

- **Profile Engine**: Comprehensive graph of candidate experiences, educations, categorized skills, certifications, and documents. Local PDF resume parser with magic-byte validation and provenance classification.
- **Job Discovery**: Multi-strategy search query expansion generating tailored keyword queries based on candidate target roles and preferences.
- **Ingestion**: Automated ingestion of job feeds with HTML sanitization, salary normalization, and rate-limit compliance.
- **Normalization**: Defensible canonical aliasing (e.g. `RAG` ↔ `Retrieval-Augmented Generation`, `PyTorch` ↔ `Torch`).
- **Deduplication**: Multi-attribute identity resolution (canonical URL, requisition ID, normalized company + title) with database-indexed candidate blocking.
- **Matching**: 8-dimension transparent scoring model with hard requirement gating.
- **Decisions**: Deterministic classification (`APPLY`, `REVIEW`, `SKIP`) with defensible evidence.
- **Preparation**: Tailored resume bullets, cover letters, and screening Q&A with claim safety rules (prohibiting ungrounded claims).
- **Execution**: State machine governance (`NOT_STARTED` → `PREPARING` → `READY` → `AWAITING_APPROVAL` → `SUBMITTING` → `SUBMITTED`) with screenshot evidence.
- **Memory**: Point-in-time state snapshots, append-only notes, decision overrides, and full lifecycle timeline.
- **Dashboard**: Central control dashboard providing funnel analytics, pipeline stages, top matches, attention queues, and source health metrics.
- **Automation**: Controlled background worker and scheduler daemons operating on database-backed queues with concurrency leasing and exponential backoff retry.
- **Security**: SSRF protection, strict localhost binding, path traversal prevention, PDF magic-byte checks, and secret-masking logging filters.

---

## Safety: The Human Approval Boundary

Safety in JOS is non-negotiable and strictly enforced:

```text
APPLICATION != SUBMISSION
APPLY != SUBMISSION
READY != SUBMISSION
Preparation != Approval
```

1. **Explicit Human Approval**: Real external submission strictly requires an explicit, human-issued approval token.
2. **Version-Bound Approvals**: Each approval is bound to an exact preparation version. Any edit to the candidate profile or application material invalidates prior approvals.
3. **Anti-Automation Boundaries**: The browser engine immediately halts (`AWAITING_USER` / `BLOCKED`) upon encountering CAPTCHA challenges, Cloudflare checks, or login/MFA barriers.
4. **No Blind Retries**: Submission timeouts yield `SUBMISSION_STATUS_UNKNOWN`. Blind retries are strictly prohibited to prevent duplicate submissions.
5. **Decisions Enforced**: `SKIP` jobs cannot be submitted. `REVIEW` jobs require explicit human resolution.

---

## Local Setup

### Prerequisites
- Windows 10/11, macOS, or Linux
- Python 3.11+
- Node.js v20+ and npm
- PostgreSQL 17 (running locally on port 5432)

### 1. Clone & Environment Configuration
```bash
git clone https://github.com/itripathiharsh/JOS.git
cd JOS
cp .env.example .env
```
Ensure your database connection string is properly configured in `.env`.

### 2. Backend & Database Initialization
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r backend/requirements.txt
python database/init_db.py
```

### 3. Frontend Build
```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Browser Engine Installation
```bash
playwright install chromium
```

---

## Daily Usage

The system is designed for a simple, daily 10-step routine:

```text
1. start.cmd                  # Launch supervisor, backend, worker, scheduler, frontend
2. Open dashboard             # Browse to http://localhost:5173
3. Review new opportunities   # Check newly discovered vacancies
4. Inspect APPLY/REVIEW jobs  # Check match scores and rationale
5. Prepare applications       # Generate tailored materials
6. Review generated material  # Inspect tailored bullets and screening Q&A
7. Approve manually           # Mint approval token (Approval Gate)
8. Execute                    # Run supervised browser submission
9. Track outcomes             # Record interview stages, notes, and milestones
10. stop.cmd when finished    # Clean shutdown of all daemons and release ports
```

---

## Backup

To create a complete, timestamped database backup:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\backup_db.ps1
```
Backups are saved to `storage\backups\job_agent_db_backup_<timestamp>.sql`. Backups do not contain plain-text credentials or API secrets.

---

## Recovery

To restore from a backup:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore_db.ps1
```
The script will prompt for safety confirmation (`RESTORE`) before applying changes. You can specify a specific backup file using the `-BackupFile` parameter.

---

## Limitations

The Job Operating System is fully functional for its design requirements, with the following real-world boundaries:

1. **Local & Single-User**: Designed for self-hosted, single-user operation on local infrastructure. Does not implement multi-tenant auth or remote cloud deployment.
2. **Current Connectors**: The Remotive remote job feed connector is active and configured. Additional custom ATS connectors (Greenhouse, Lever) can be added via the extensible `JobSource` interface.
3. **Anti-Automation Walls Require User Intervention**: CAPTCHA challenges, Cloudflare turnaround checks, and login/MFA walls intentionally halt automated execution and require human interaction.
4. **Platform-Specific Scripts**: Lifecycle shortcuts (`start.cmd`, `stop.cmd`, `status.cmd`, `restart.cmd`) are tailored for Windows PowerShell environments. On Linux/macOS, use the equivalent shell commands or python supervisor directly (`python scripts/supervisor.py`).

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
