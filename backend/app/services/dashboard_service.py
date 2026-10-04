from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.job import Job
from app.models.matching import MatchResult
from app.models.application import Application
from app.schemas.dashboard import DashboardStatsResponse


def get_dashboard_statistics(db: Session) -> DashboardStatsResponse:
    """Retrieve actual aggregate metrics from the database reflecting real ingestion and matching."""
    jobs_discovered = db.query(func.count(Job.id)).scalar() or 0

    # Real match intelligence metrics
    matched_strong = db.query(func.count(MatchResult.id)).filter(MatchResult.fit_category == "HIGH_RELEVANCE").scalar() or 0
    job_strong = db.query(func.count(Job.id)).filter(Job.status == "strong_match").scalar() or 0
    strong_matches = max(matched_strong, job_strong)

    matched_relevant = db.query(func.count(MatchResult.id)).filter(
        MatchResult.fit_category.in_(["HIGH_RELEVANCE", "GOOD_RELEVANCE", "PARTIAL_RELEVANCE"])
    ).scalar() or 0
    job_relevant = db.query(func.count(Job.id)).filter(Job.status.in_(["relevant", "strong_match"])).scalar() or 0
    relevant_jobs = max(matched_relevant, job_relevant)

    applications = db.query(func.count(Application.id)).scalar() or 0
    needs_attention = db.query(func.count(Application.id)).filter(Application.status == "human_action_required").scalar() or 0

    return DashboardStatsResponse(
        jobs_discovered=jobs_discovered,
        relevant_jobs=relevant_jobs,
        strong_matches=strong_matches,
        applications=applications,
        needs_attention=needs_attention,
    )
