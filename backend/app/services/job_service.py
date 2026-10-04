from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, or_, and_
from fastapi import HTTPException, status
from app.models.job import Job, JobDuplicate
from app.models.decision import ApplicationDecision
from app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobResponse,
    JobDetailResponse,
    JobOccurrenceResponse,
    JobDuplicateLinkResponse,
)
from app.schemas.decision import ApplicationDecisionResponse
from app.services.deduplication import normalize_url, AntiDuplicateEngine
from typing import Optional, List, Dict, Any
import json


def get_jobs(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    work_mode: Optional[str] = None,
    source: Optional[str] = None,
    duplicate_status: Optional[str] = None,
    decision: Optional[str] = None,
    only_canonical: bool = False,
) -> JobListResponse:
    query = db.query(Job)

    if status_filter:
        query = query.filter(Job.status == status_filter)

    if source:
        query = query.filter(Job.source == source)

    if work_mode and work_mode.lower() != "all":
        query = query.filter(Job.work_mode.ilike(f"%{work_mode}%"))

    if duplicate_status and duplicate_status.lower() != "all":
        query = query.filter(Job.duplicate_status == duplicate_status)
    elif only_canonical:
        query = query.filter(Job.is_canonical == True)

    if decision and decision.lower() != "all":
        query = query.join(ApplicationDecision, ApplicationDecision.job_id == Job.id).filter(
            ApplicationDecision.decision == decision.upper()
        )

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Job.title.ilike(term),
                Job.company.ilike(term),
                Job.location.ilike(term),
            )
        )

    total = query.count()
    items = query.order_by(desc(Job.discovered_at)).offset(skip).limit(limit).all()

    # Pre-aggregate occurrences counts for canonical jobs in this batch
    canonical_ids = [item.id for item in items if item.is_canonical]
    dup_counts_by_canonical: Dict[str, List[str]] = {}
    if canonical_ids:
        dup_rows = db.query(Job.canonical_job_id, Job.source).filter(
            Job.canonical_job_id.in_(canonical_ids),
            Job.duplicate_status == "duplicate",
        ).all()
        for c_id, src in dup_rows:
            if c_id not in dup_counts_by_canonical:
                dup_counts_by_canonical[c_id] = []
            dup_counts_by_canonical[c_id].append(src)

    response_items = []
    for item in items:
        resp = JobResponse.model_validate(item)
        if item.match_results:
            latest_match = item.match_results[0]
            resp.match_score = latest_match.overall_score
            resp.fit_category = latest_match.fit_category

        if item.decisions:
            latest_dec = item.decisions[0]
            resp.application_decision = latest_dec.decision
            resp.decision_reason = latest_dec.reasons[0] if latest_dec.reasons else None
            resp.decision_risk_level = latest_dec.risk_level

        # Add cross-source occurrence counts and sources
        if item.is_canonical:
            linked_sources = dup_counts_by_canonical.get(item.id, [])
            resp.occurrences_count = 1 + len(linked_sources)
            resp.sources = sorted(list(set([item.source] + linked_sources)))
        else:
            resp.occurrences_count = 1
            resp.sources = [item.source]

        response_items.append(resp)

    # Global counts for dashboard metrics
    canonical_count = db.query(Job).filter(Job.is_canonical == True, Job.duplicate_status == "canonical").count()
    duplicate_count = db.query(Job).filter(Job.duplicate_status == "duplicate").count()
    possible_dup_count = db.query(Job).filter(Job.duplicate_status == "possible_duplicate").count()

    apply_count = db.query(ApplicationDecision).filter(ApplicationDecision.decision == "APPLY").count()
    review_count = db.query(ApplicationDecision).filter(ApplicationDecision.decision == "REVIEW").count()
    skip_count = db.query(ApplicationDecision).filter(ApplicationDecision.decision == "SKIP").count()

    return JobListResponse(
        items=response_items,
        total=total,
        skip=skip,
        limit=limit,
        canonical_count=canonical_count,
        duplicate_count=duplicate_count,
        possible_duplicate_count=possible_dup_count,
        apply_count=apply_count,
        review_count=review_count,
        skip_count=skip_count,
    )



def get_job_by_id(db: Session, job_id: str) -> Optional[Job]:
    return db.query(Job).filter(Job.id == job_id).first()


def get_job_detail_with_occurrences(db: Session, job_id: str) -> Optional[JobDetailResponse]:
    """Retrieve full job detail including cross-source occurrences and duplicate link evidence."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return None

    # Base response
    resp = JobDetailResponse.model_validate(job)
    if job.match_results:
        latest_match = job.match_results[0]
        resp.match_score = latest_match.overall_score
        resp.fit_category = latest_match.fit_category

    # 1. Fetch all source occurrences
    raw_occurrences = AntiDuplicateEngine.get_source_occurrences(db, job_id)
    resp.occurrences = [
        JobOccurrenceResponse(
            job_id=occ["job_id"],
            source=occ["source"],
            external_job_id=occ["external_job_id"],
            application_url=occ["application_url"],
            canonical_url=occ["canonical_url"],
            discovered_at=occ["discovered_at"],
            last_seen_at=occ["last_seen_at"],
            is_canonical=occ["is_canonical"],
            duplicate_status=occ["duplicate_status"],
            duplicate_confidence=occ["duplicate_confidence"],
        )
        for occ in raw_occurrences
    ]
    resp.occurrences_count = len(resp.occurrences)
    resp.sources = sorted(list(set(occ["source"] for occ in raw_occurrences)))

    # 2. Fetch duplicate link records (evidence)
    dup_links = db.query(JobDuplicate).filter(
        or_(
            JobDuplicate.canonical_job_id == job.id,
            JobDuplicate.duplicate_job_id == job.id,
        )
    ).all()

    formatted_links = []
    for link in dup_links:
        parsed_evidence = None
        if link.evidence:
            try:
                parsed_evidence = json.loads(link.evidence)
            except Exception:
                parsed_evidence = {"raw": link.evidence}
        formatted_links.append(
            JobDuplicateLinkResponse(
                id=link.id,
                canonical_job_id=link.canonical_job_id,
                duplicate_job_id=link.duplicate_job_id,
                confidence=link.confidence,
                confidence_score=float(link.confidence_score),
                match_method=link.match_method,
                status=link.status,
                evidence=parsed_evidence,
                created_at=link.created_at,
            )
        )
    resp.duplicate_links = formatted_links


    if job.decisions:
        latest_dec = job.decisions[0]
        resp.decision_details = ApplicationDecisionResponse.model_validate(latest_dec)
        resp.application_decision = latest_dec.decision
        resp.decision_reason = latest_dec.reasons[0] if latest_dec.reasons else None
        resp.decision_risk_level = latest_dec.risk_level

    return resp



def create_job(db: Session, data: JobCreate) -> Job:
    # Explicit check for duplicate external job from same source
    if data.external_job_id:
        existing = db.query(Job).filter(
            Job.source == data.source,
            Job.external_job_id == data.external_job_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job from source '{data.source}' with external ID '{data.external_job_id}' already exists."
            )

    job_payload = data.model_dump()
    if data.application_url:
        job_payload["canonical_url"] = normalize_url(data.application_url)

    job = Job(**job_payload)
    db.add(job)
    try:
        db.flush()
        AntiDuplicateEngine.evaluate_and_link(db, job)
        db.commit()
        db.refresh(job)
        return job
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job from source '{data.source}' with external ID '{data.external_job_id}' already exists."
        )
