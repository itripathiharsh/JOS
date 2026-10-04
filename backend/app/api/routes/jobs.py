from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
import time

from app.db.session import get_db
from app.schemas.job import (
    JobListResponse,
    JobResponse,
    JobDetailResponse,
    JobCreate,
    JobOccurrenceResponse,
    BatchDeduplicationRequest,
    BatchDeduplicationResponse,
    FetchJobsRequest,
    IngestionResponse,
    SourceStatusResponse,
)
from app.services.job_service import (
    get_jobs,
    get_job_by_id,
    get_job_detail_with_occurrences,
    create_job,
)
from app.services.job_ingestion_service import (
    ingest_jobs_from_source,
    get_all_source_statuses,
    check_source_health,
)
from app.services.deduplication import AntiDuplicateEngine
from app.models.job import Job
from app.models.application import Application
from app.schemas.preparation import (
    PreparationRequest,
    PreparationUpdateRequest,
    ApplicationPreparationResponse,
)
from app.schemas.execution import ExecutionStartRequest, ApplicationExecutionResponse
from app.services.preparation_engine.engine import ApplicationPreparationEngine
from app.services.execution_layer.engine import ApplicationExecutionEngine

router = APIRouter()


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search keyword across title, company, or location"),
    work_mode: Optional[str] = Query(None, description="Filter by work mode (e.g. remote, hybrid, onsite)"),
    source: Optional[str] = Query(None, description="Filter by job source (e.g. remotive)"),
    duplicate_status: Optional[str] = Query(None, description="Filter by duplicate status (canonical, duplicate, possible_duplicate)"),
    decision: Optional[str] = Query(None, description="Filter by application decision (APPLY, REVIEW, SKIP)"),
    only_canonical: bool = Query(False, description="Filter only canonical records"),
    db: Session = Depends(get_db)
):
    """List jobs with pagination, filtering, search, deduplication, and decision capabilities."""
    return get_jobs(
        db,
        skip=skip,
        limit=limit,
        status_filter=status,
        search=search,
        work_mode=work_mode,
        source=source,
        duplicate_status=duplicate_status,
        decision=decision,
        only_canonical=only_canonical,
    )



@router.get("/jobs/sources/status", response_model=List[SourceStatusResponse])
def get_sources_status(db: Session = Depends(get_db)):
    """Retrieve operational status and statistics for all registered job source connectors."""
    return get_all_source_statuses(db)


@router.post("/jobs/sources/{source_name}/health")
def verify_source_health(source_name: str, db: Session = Depends(get_db)):
    """Trigger a live connectivity and responsiveness check on a specific source."""
    return check_source_health(source_name, db)


@router.post("/jobs/fetch", response_model=IngestionResponse)
def fetch_jobs_manually(request: FetchJobsRequest, db: Session = Depends(get_db)):
    """
    Trigger a real manual job fetch from the selected source connector.
    Fetches, normalizes, validates, deduplicates, and stores jobs in PostgreSQL.
    """
    try:
        stats = ingest_jobs_from_source(
            db=db,
            source_name=request.source,
            keyword=request.keyword,
            location=request.location,
            remote=request.remote,
            limit=request.limit,
        )

        has_source_failure = stats.jobs_fetched == 0 and len(stats.errors) > 0
        if has_source_failure:
            success = False
            message = f"Ingestion failed for {request.source.upper()}: {'; '.join(stats.errors[:2])}"
        else:
            success = True
            message = (
                f"Successfully fetched {stats.jobs_fetched} jobs from {request.source.upper()}. "
                f"Created {stats.jobs_created} new, updated {stats.jobs_updated}, skipped {stats.jobs_skipped}."
            )

        return IngestionResponse(
            success=success,
            source=stats.source,
            query=stats.query,
            jobs_fetched=stats.jobs_fetched,
            jobs_created=stats.jobs_created,
            jobs_updated=stats.jobs_updated,
            jobs_skipped=stats.jobs_skipped,
            errors=stats.errors,
            message=message,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job ingestion error: {str(exc)}"
        )


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job_detail(job_id: str, db: Session = Depends(get_db)):
    """Retrieve full details of a specific job by ID, including cross-source occurrences and duplicate link evidence."""
    job_detail = get_job_detail_with_occurrences(db, job_id)
    if not job_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found."
        )
    return job_detail


@router.get("/jobs/{job_id}/occurrences", response_model=List[JobOccurrenceResponse])
def get_job_occurrences(job_id: str, db: Session = Depends(get_db)):
    """Retrieve all cross-source occurrences associated with a canonical job."""
    occurrences = AntiDuplicateEngine.get_source_occurrences(db, job_id)
    if not occurrences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found."
        )
    return [JobOccurrenceResponse(**occ) for occ in occurrences]


@router.post("/jobs/deduplicate/batch", response_model=BatchDeduplicationResponse)
def run_batch_deduplication(
    request: BatchDeduplicationRequest,
    db: Session = Depends(get_db)
):
    """
    Run an on-demand deduplication pass over stored vacancies in PostgreSQL.
    Evaluates unlinked or existing jobs, detects cross-source duplicates, and links them.
    """
    start_time = time.perf_counter()
    jobs_to_eval = db.query(Job).order_by(Job.created_at.asc()).limit(request.limit).all()

    duplicates_found = 0
    possible_duplicates_found = 0

    for job in jobs_to_eval:
        link = AntiDuplicateEngine.evaluate_and_link(db, job, auto_commit=not request.dry_run)
        if link:
            if link.confidence in ("VERY_HIGH", "HIGH"):
                duplicates_found += 1
            elif link.confidence == "MEDIUM":
                possible_duplicates_found += 1

    if not request.dry_run:
        db.commit()

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    message = (
        f"Evaluated {len(jobs_to_eval)} jobs in {duration_ms}ms. "
        f"Found {duplicates_found} duplicates, {possible_duplicates_found} possible duplicates."
    )

    return BatchDeduplicationResponse(
        jobs_evaluated=len(jobs_to_eval),
        duplicates_found=duplicates_found,
        possible_duplicates_found=possible_duplicates_found,
        duration_ms=duration_ms,
        message=message,
    )


@router.post("/jobs", response_model=JobResponse)
def add_job(data: JobCreate, db: Session = Depends(get_db)):
    """Manual job creation endpoint."""
    return create_job(db, data)


# --- Step 8: Job Application Preparation Endpoints ---

@router.post("/jobs/{id}/prepare", response_model=ApplicationPreparationResponse)
def prepare_job_application(
    id: str,
    payload: Optional[PreparationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Step 8: Prepares an application package for a job.
    Transforms Candidate Profile + Resume + Job + Match Intelligence + Decision into Application Package.
    Boundary: Preparation only. Never auto-submits.
    """
    req_data = payload or PreparationRequest()
    prep = ApplicationPreparationEngine.prepare_application_for_job(
        db=db,
        job_id=id,
        candidate_id=req_data.candidate_id,
        force_regenerate=req_data.force_regenerate,
        allow_skip=req_data.allow_skip,
        user_overrides=req_data.user_overrides,
        user_notes=req_data.user_notes,
    )
    return prep


@router.get("/jobs/{id}/preparation", response_model=ApplicationPreparationResponse)
def get_job_application_preparation(
    id: str,
    candidate_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retrieves the persisted preparation package for a job.
    """
    prep = ApplicationPreparationEngine.get_preparation_for_job(db, id, candidate_id)
    if not prep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No preparation package found for job ID '{id}'. Please run prepare first."
        )
    return prep


@router.post("/jobs/{id}/preparation/regenerate", response_model=ApplicationPreparationResponse)
def regenerate_job_application_preparation(
    id: str,
    payload: Optional[PreparationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Regenerates preparation package for a job, incrementing the version counter.
    Avoids creating uncontrolled duplicate records.
    """
    req_data = payload or PreparationRequest()
    prep = ApplicationPreparationEngine.prepare_application_for_job(
        db=db,
        job_id=id,
        candidate_id=req_data.candidate_id,
        force_regenerate=True,
        allow_skip=req_data.allow_skip,
        user_overrides=req_data.user_overrides,
        user_notes=req_data.user_notes,
    )
    return prep


@router.patch("/jobs/{id}/preparation", response_model=ApplicationPreparationResponse)
def update_job_application_preparation(
    id: str,
    payload: PreparationUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Updates human confirmations and user notes on a job's preparation package.
    """
    prep = ApplicationPreparationEngine.update_user_overrides(
        db=db,
        job_id=id,
        user_overrides=payload.user_overrides,
        user_notes=payload.user_notes,
        candidate_id=payload.candidate_id,
    )
    return prep


# --- Step 9: Job Application Execution Endpoints ---

@router.post("/jobs/{id}/execute", response_model=ApplicationExecutionResponse)
def execute_job_application(
    id: str,
    payload: Optional[ExecutionStartRequest] = None,
    candidate_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Step 9: Initiates execution directly for a job.
    Ensures an application record and preparation package exist, then launches the controlled execution.
    """
    job = db.query(Job).filter(Job.id == id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{id}' not found."
        )

    # Resolve candidate
    cand_id = candidate_id
    if not cand_id:
        from app.models.profile import CandidateProfile
        cand = db.query(CandidateProfile).first()
        cand_id = cand.id if cand else None

    if not cand_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidate profile found. Please create candidate profile first."
        )

    # Ensure application record exists
    app_record = db.query(Application).filter(
        Application.job_id == id,
        Application.candidate_id == cand_id,
    ).first()

    if not app_record:
        app_record = Application(
            job_id=id,
            candidate_id=cand_id,
            status="draft",
            source=job.source,
            application_url=job.application_url,
        )
        db.add(app_record)
        db.flush()

    # Ensure preparation package exists
    prep = ApplicationPreparationEngine.get_preparation_by_job_id(db, id, cand_id)
    if not prep:
        prep = ApplicationPreparationEngine.prepare_application_for_job(
            db=db,
            job_id=id,
            candidate_id=cand_id,
            application_id=app_record.id,
            allow_skip=(payload.allow_force if payload else False),
        )

    req_data = payload or ExecutionStartRequest()
    execution = ApplicationExecutionEngine.start_execution(
        db=db,
        application_id=app_record.id,
        mode=req_data.mode or "MANUAL",
        source=req_data.source or "generic_web",
        allow_force=req_data.allow_force or False,
        context=req_data.context,
    )
    return execution


@router.get("/jobs/{id}/execution", response_model=ApplicationExecutionResponse)
def get_latest_job_execution(
    id: str,
    candidate_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retrieves the most recent execution attempt for a job.
    """
    cand_id = candidate_id
    if not cand_id:
        from app.models.profile import CandidateProfile
        cand = db.query(CandidateProfile).first()
        cand_id = cand.id if cand else None

    app_record = db.query(Application).filter(
        Application.job_id == id,
        Application.candidate_id == cand_id,
    ).first()

    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No application found for job ID '{id}'."
        )

    execution = ApplicationExecutionEngine.get_latest_execution_for_application(db, app_record.id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No execution attempt found for job ID '{id}'."
        )
    return execution

