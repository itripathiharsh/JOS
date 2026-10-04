# Connectors Module (Phase 1 Placeholder)

Future job sources (LinkedIn, Indeed, Naukri, direct careers pages) will be implemented here.

## Intended Architecture:
```
JobSource (Interface)
  ├── fetch_jobs(search_criteria)
  └── normalize_job(raw_data) -> Canonical Job
```
*Note: Connectors are not active in Phase 1 (Foundation only).*
