from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.dashboard import DashboardStatsResponse
from app.schemas.dashboard_os import JobOperatingSystemResponse
from app.services.dashboard_service import get_dashboard_statistics
from app.services.dashboard_os_service import DashboardOperatingSystemService

router = APIRouter()


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Backward-compatible basic metrics endpoint."""
    return get_dashboard_statistics(db)


@router.get("/dashboard/operating-system", response_model=JobOperatingSystemResponse)
def get_job_operating_system(
    target_role: Optional[str] = Query(None, description="Filter metrics and opportunities by role keyword"),
    work_mode: Optional[str] = Query(None, description="Filter metrics and opportunities by work mode (e.g. remote, hybrid, onsite)"),
    source: Optional[str] = Query(None, description="Filter metrics and opportunities by job source"),
    candidate_id: Optional[str] = Query(None, description="Filter metrics by specific candidate ID"),
    db: Session = Depends(get_db)
):
    """
    Step 11: The Job Operating System Dashboard Central Control Center.
    Single-pass aggregated payload delivering:
    - Core Health KPIs
    - Actionable 'Today / Attention Queue'
    - Multi-stage Job Search Funnel
    - 14-Stage Application Pipeline
    - Match Quality Distribution
    - Curated Top Opportunities
    - Job Source Operational Health
    - Candidate Profile Health & Readiness
    - Recent Activity Chronological Feed
    - Performance & Feedback Conversion Summary
    """
    return DashboardOperatingSystemService.get_dashboard_data(
        db=db,
        target_role=target_role,
        work_mode=work_mode,
        source=source,
        candidate_id=candidate_id,
    )

