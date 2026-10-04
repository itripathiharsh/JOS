# Job Operating System (JOS)

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React_19_%2B_TypeScript-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_17-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Playwright](https://img.shields.io/badge/Automation-Playwright-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An intelligent, self-hosted, human-in-the-loop autonomous platform for career opportunity discovery, multi-dimensional job matching, deterministic application preparation, and auditable lifecycle tracking.

---

## Overview

**Job Operating System (JOS)** transforms the chaotic job search process into a structured, reliable, and auditable pipeline. Rather than acting as a blind "auto-apply bot" that floods job portals with low-quality submissions, JOS implements **Controlled Autonomy**: an engineering framework that automates data aggregation, deduplication, requirement extraction, and content preparation while reserving external application submission for verified, explicit human approval.

---

## Core Philosophy & Design Principles

* **Controlled Autonomy**: `Preparation ≠ Approval ≠ Submission`. Automated decision engines can analyze, rank, and prepare tailored application materials, but real external submissions strictly require an unexpired, version-locked human approval token.
* **Deterministic & Explainable Matching**: No hallucinations or opaque black-box scoring. Vacancy evaluations are grounded strictly in defensible candidate evidence across 8 structured dimensions with explicit penalties for seniority or mandatory skill gaps.
* **Anti-Automation & Compliance First**: Automated workflows immediately yield control (`AWAITING_USER` / `BLOCKED`) upon encountering CAPTCHA challenges, bot detection, or login walls. Anti-bot protections are respected, never circumvented.
* **Complete Memory & Auditability**: Every candidate interaction, requirement extraction, tailored resume recommendation, interview update, and outcome event is recorded into immutable, queryable snapshots.
* **100% Self-Hosted & Privacy-Preserving**: All candidate data, resumes, session cookies, database records, and logs remain strictly under your local control.

---

## Architectural Progression Pipeline

JOS manages the entire application lifecycle through an interconnected, multi-stage pipeline:

```text
  ┌───────────────────────┐
  │   Candidate Profile   │  <── Single source of truth (skills, experience, preferences)
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │     Job Discovery     │  <── Multi-strategy query expansion & connector ingestion
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │ Anti-Duplicate Engine │  <── Canonical identity clustering, URL & requisition dedup
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │ Job Intelligence (AI) │  <── 8-dimension matching, skill aliases, hard requirement caps
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │    Decision Engine    │  <── Deterministic classification: APPLY / REVIEW / SKIP
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  Preparation Engine   │  <── Evidence mapping, tailored content, screening Q&A
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │ Human Approval Gate   │  <── Cryptographic, version-bound submission token
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │ Safe Execution Engine │  <── Supervised browser automation (Playwright)
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐
  │  Application Memory   │  <── Immutable snapshots, event timelines, outcome feedback
  └───────────────────────┘
```

---

## Key Subsystems & Capabilities

### 1. Candidate Profile Engine
* **Structured Data Graph**: Models personal information, work experiences, academic education, skills catalog (with categorized proficiencies), projects, certifications, links, and documents.
* **Resume Parser & Ingestion**: Local text and section extractor (`pypdf`) with magic-byte validation and provenance categorization (`CONFIRMED`, `USER_PROVIDED`, `INFERRED`).
* **Rule-Based Completeness**: Transparent scoring system tracking required criteria (target roles, work mode, location preferences) and optional profile enrichment.

### 2. Job Discovery & Connectors
* **Extensible Connector Abstraction**: Plug-and-play architecture for ATS and job sources (`JobSource` interface).
* **Automated Ingestion**: Ingests structured JSON job feeds, sanitizes HTML descriptions, extracts compensation ranges, and handles rate limits.
* **Search Expansion**: Generates optimized multi-query search strategies based on candidate target roles and priority rankings.

### 3. Anti-Duplicate & Identity Clustering
* **Layered Identity Resolution**: Matches vacancies across portals using canonical URL extraction, requisition ID parsing, and normalized company/title/location comparison.
* **Candidate Blocking**: Uses indexed database predicates to perform duplicate checks in milliseconds without expensive full-table scans.
* **Occurrence History**: Maintains audit links between duplicate portal listings while consolidating intelligence onto a single canonical job entity.

### 4. Deterministic Matching & Intelligence
* **8-Dimensional Scoring**: Evaluates Role (30%), Skills (35%), Experience (15%), Location (8%), Work Mode (4%), Salary (3%), Education (3%), and Employment Type (2%).
* **Skill Normalization**: Defensible canonical aliasing (e.g. `RAG` ↔ `Retrieval-Augmented Generation`, `PyTorch` ↔ `Torch`).
* **Hard Requirement Layer**: Evaluates minimum experience thresholds and mandatory certifications. Imposes explicit score caps and classification demotions on seniority gaps.

### 5. Application Decision & Preparation
* **Decision Classification**: Deterministically assigns `APPLY`, `REVIEW`, or `SKIP` with confidence metrics and structured rationale lists.
* **Evidence Mapping & Claim Safety**: Maps candidate profile achievements directly to job requirements. Prohibits unsupported claims or hallucinated capabilities.
* **Tailored Content Generation**: Generates targeted resume bullet suggestions, key skill highlights, cover messages, and answers to application screening questions.
* **Readiness Assessment**: Evaluates package readiness (`READY`, `READY_WITH_REVIEW`, `NEEDS_WORK`) with strict version tracking.

### 6. Controlled Execution & Safety Boundaries
* **State Machine Governance**: Tracks applications through discrete lifecycle stages (`NOT_STARTED` → `PREPARING` → `READY` → `AWAITING_APPROVAL` → `SUBMITTING` → `SUBMITTED`).
* **Approval Version Binding**: Human approvals are bound to an exact preparation package version. Any subsequent profile edit or job update immediately invalidates prior approvals.
* **Anti-Automation Detection**: Automatically halts execution upon encountering CAPTCHA, Cloudflare challenges, login requirements, or unconfirmed form fields.
* **Idempotency & Observable Evidence**: Captures DOM confirmation and browser screenshots before declaring success. Unknown outcomes transition to `SUBMISSION_STATUS_UNKNOWN` to strictly prevent blind retry loops.

### 7. Application Memory & Analytics
* **Immutable State Snapshots**: Captures complete point-in-time snapshots of the vacancy, candidate profile, match evaluation, and preparation package.
* **Audit Timeline**: Event-driven history tracking status transitions, candidate notes, and manual overrides.
* **Outcome Tracking**: Records interview milestones, rejection feedback, and offer details to power conversion rate analytics.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Backend API** | Python 3.11, FastAPI, Pydantic v2, Uvicorn, HTTPX |
| **ORM & Database** | PostgreSQL 17, SQLAlchemy 2.0, Alembic (transactional DDL) |
| **Task Queue & Daemons** | PostgreSQL-backed Queue (`SELECT FOR UPDATE SKIP LOCKED`), Background Worker & Scheduler Daemons |
| **Browser Engine** | Playwright (Headless / Headed Chromium), Persistent Storage States |
| **Frontend UI** | React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons |
| **Security & Hardening** | SSRF URL filtering, path traversal validation, PDF magic-byte checks, secret-masking logging filters, SCRAM-SHA-256 database authentication |

---

## Project Structure

```text
├── .agents/                      # Autonomous coding agent configuration & guidelines
├── applications/                 # Application tracking and workflow interfaces
├── backend/
│   ├── alembic/                  # Database migration versions and environment
│   ├── app/
│   │   ├── api/routes/           # FastAPI REST route endpoints
│   │   ├── core/                 # App configuration, logging filter, security validators
│   │   ├── db/                   # Database session and base models
│   │   ├── models/               # SQLAlchemy relational entities (12 primary models)
│   │   ├── schemas/              # Pydantic validation and serialization schemas
│   │   └── services/             # Core engines (Matching, Decision, Prep, Memory, Queue)
│   └── requirements.txt          # Python dependencies
├── browser/                      # Sandboxed Playwright browser automation engine
├── connectors/                   # Job source connectors and normalization models
├── database/                     # Database provisioning and health check scripts
├── frontend/
│   ├── src/
│   │   ├── api/                  # Typed REST API client
│   │   ├── components/           # UI components, modals, and metric dashboards
│   │   └── pages/                # ApplicationsPage, DashboardPage, JobsPage, ProfilePage
│   └── package.json              # Frontend dependencies and build configuration
├── intelligence/                 # Normalization models, extractors, and matching engine
├── scripts/                      # Supervisor, process management, backup & restore utilities
├── storage/                      # Documents, screenshots, and database backups
├── workers/                      # Autonomous background worker and scheduler daemons
├── AGENTS.md                     # Operational rules & workspace governance
├── context.md                    # Comprehensive iteration history & architectural log
├── start.cmd / stop.cmd          # One-command lifecycle control shortcuts
└── README.md
```

---

## Getting Started

### Prerequisites

* **Operating System**: Windows 10/11, macOS, or Linux
* **Python**: 3.11+
* **Node.js**: v20+ and `npm`
* **Database**: PostgreSQL 17

### 1. Environment Configuration

Copy the example environment template and configure your local settings:

```bash
cp .env.example .env
```

Review `.env` to verify your local database connection parameters:

```ini
DATABASE_URL=postgresql://job_agent_user:your_secure_password@localhost:5432/job_agent_db
HOST=127.0.0.1
PORT=8000
FRONTEND_URL=http://localhost:5173
```

### 2. Backend & Database Setup

Create a virtual environment and install backend dependencies:

```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r backend/requirements.txt
```

Initialize the database and apply all Alembic migrations:

```bash
python database/init_db.py
```

### 3. Frontend Setup

Install frontend dependencies and verify the production build:

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Install Browser Engine

Install the sandboxed Playwright Chromium browser:

```bash
playwright install chromium
```

---

## Operational Control

JOS includes unified lifecycle scripts and quick Windows shortcuts:

| Command | Shortcut | Description |
|---|---|---|
| `powershell scripts\start.ps1` | `.\start.cmd` | Runs pre-flight checks, verifies migrations, and launches backend, worker, scheduler, and frontend in the background. |
| `powershell scripts\start.ps1 -Foreground` | — | Starts the process supervisor in the foreground with live console logs. Stop with `Ctrl+C`. |
| `powershell scripts\status.ps1` | `.\status.cmd` | Displays real-time status of PIDs, ports, memory footprint, task queue depth, and browser readiness. |
| `powershell scripts\stop.ps1` | `.\stop.cmd` | Gracefully shuts down all components in reverse order and releases network ports. |
| `powershell scripts\restart.ps1` | `.\restart.cmd` | Cleanly stops all services, waits for port release, and restarts the full stack. |
| `powershell scripts\backup_db.ps1` | — | Generates an automated, timestamped PostgreSQL backup in `storage/backups/`. |
| `powershell scripts\restore_db.ps1` | — | Safe database restore utility with interactive safety confirmation. |

---

## End-to-End Workflow

1. **Profile Setup**: Open the dashboard at `http://localhost:5173/profile`. Populate your skills, experiences, and preferences, or import your resume with one click.
2. **Opportunity Discovery**: Open `http://localhost:5173/jobs` and click **Fetch Real Jobs** to discover and ingest fresh market opportunities.
3. **Automated Matching & Decisions**: The engine evaluates each job across 8 dimensions, flags hard mismatches, and suggests an `APPLY`, `REVIEW`, or `SKIP` action with detailed explanations.
4. **Application Preparation**: Click **Prepare Application** on an approved vacancy. JOS tailors bullet points, formulates screening question answers, and assigns a readiness score.
5. **Human Approval**: Inspect the prepared package and click **Approve Application**. An unexpired approval token is minted.
6. **Execution & Submission**: Execute the application in `ASSISTED` or `AUTOMATED` mode. Watch the automated browser complete application fields or review before final submission.
7. **Lifecycle Tracking**: Track active applications on `http://localhost:5173/applications`, log interview rounds, candidate notes, and analyze success rates over time.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
