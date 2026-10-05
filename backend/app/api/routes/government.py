from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.db.session import get_db
from app.models.government import (
    GovernmentSource,
    GovernmentVacancy,
    GovernmentDiscoveryRun,
    GovernmentChangeEvent,
    GovernmentUnresolvedTarget,
)
from app.models.job import Job
from app.models.matching import MatchResult
from app.models.decision import ApplicationDecision
from app.schemas.government import (
    GovernmentSourceResponse,
    GovernmentSourceListResponse,
    GovernmentVacancyResponse,
    GovernmentVacancyListResponse,
    GovernmentCoverageResponse,
    GovernmentDiscoveryTriggerRequest,
    GovernmentCrawlRequest,
    GovernmentDiscoveryRunResponse,
    GovernmentChangeEventResponse,
    GovernmentMonitoringStatsResponse,
    GovernmentMonitoringTickResponse,
    GovernmentUnresolvedTargetResponse,
    GovernmentUnresolvedTargetListResponse,
    GovernmentUniverseMissionRequest,
    GovernmentUniverseMissionResponse,
)
from app.services.government.engine import GovernmentDiscoveryEngine
from app.services.government.scheduler import GovernmentContinuousScheduler
from app.services.government.universe_parser import GovernmentUniverseParser

router = APIRouter()


@router.get("/government/sources", response_model=GovernmentSourceListResponse)
def list_government_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    state: Optional[str] = Query(None, description="Filter by state or UT name"),
    government_level: Optional[str] = Query(None, description="Filter by level: central, state, ut, district"),
    organisation_type: Optional[str] = Query(None, description="Filter by type: ministry, psu, university, etc."),
    source_status: Optional[str] = Query(None, description="Filter by status: DISCOVERED, VERIFIED, ACTIVE, REQUIRES_MANUAL_ACCESS"),
    search: Optional[str] = Query(None, description="Text search in organisation name or domain"),
    db: Session = Depends(get_db)
):
    """
    Lists registered Indian government employment sources with comprehensive filtering.
    """
    # Ensure seed sources are in DB
    GovernmentDiscoveryEngine.seed_initial_sources(db)

    query = db.query(GovernmentSource)
    if state:
        query = query.filter(GovernmentSource.state.ilike(f"%{state}%"))
    if government_level:
        query = query.filter(GovernmentSource.government_level == government_level.lower())
    if organisation_type:
        query = query.filter(GovernmentSource.organisation_type == organisation_type.lower())
    if source_status:
        query = query.filter(GovernmentSource.source_status == source_status.upper())
    if search:
        query = query.filter(
            or_(
                GovernmentSource.organisation_name.ilike(f"%{search}%"),
                GovernmentSource.official_domain.ilike(f"%{search}%")
            )
        )

    total = query.count()
    items = query.order_by(desc(GovernmentSource.vacancies_found), GovernmentSource.organisation_name.asc()).offset(skip).limit(limit).all()

    return GovernmentSourceListResponse(
        total=total,
        items=[GovernmentSourceResponse.model_validate(it) for it in items]
    )


@router.get("/government/sources/{source_id}", response_model=GovernmentSourceResponse)
def get_government_source(source_id: str, db: Session = Depends(get_db)):
    """Retrieves an individual government source record."""
    src = db.query(GovernmentSource).filter(GovernmentSource.id == source_id).first()
    if not src:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Government source '{source_id}' not found."
        )
    return GovernmentSourceResponse.model_validate(src)


@router.post("/government/sources/seed")
def seed_government_sources(db: Session = Depends(get_db)):
    """Idempotently populates the initial seed directory of government sources."""
    created = GovernmentDiscoveryEngine.seed_initial_sources(db)
    total = db.query(GovernmentSource).count()
    return {"message": "Seed sources checked/initialized.", "new_created": created, "total_sources": total}


@router.post("/government/sources/discover")
def discover_sources_open_ended(
    payload: Optional[GovernmentDiscoveryTriggerRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Executes open-ended search engine discovery across public search endpoints
    to find previously unknown Indian government employment sources.
    """
    req = payload or GovernmentDiscoveryTriggerRequest()
    result = GovernmentDiscoveryEngine.discover_sources_open_ended(
        db=db,
        scope=req.scope,
        state_filter=req.state_filter,
        max_queries=req.max_search_queries,
    )
    return result


@router.post("/government/sources/{source_id}/crawl")
def crawl_individual_source(source_id: str, db: Session = Depends(get_db)):
    """Crawls a specific government portal, extracting notices and PDFs."""
    src = db.query(GovernmentSource).filter(GovernmentSource.id == source_id).first()
    if not src:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Government source '{source_id}' not found."
        )
    return GovernmentDiscoveryEngine.crawl_source(db, src)


@router.post("/government/crawl-all")
def crawl_all_eligible_sources(
    payload: Optional[GovernmentCrawlRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Crawls a batch of eligible sources without artificial limits,
    progressively processing the entire source universe over time.
    """
    req = payload or GovernmentCrawlRequest()
    return GovernmentDiscoveryEngine.crawl_batch(
        db=db,
        batch_size=req.batch_size,
        state_filter=req.state_filter,
        org_type_filter=req.organisation_type_filter,
        force_recheck=req.force_recheck,
    )


@router.get("/government/coverage", response_model=GovernmentCoverageResponse)
def get_government_coverage(db: Session = Depends(get_db)):
    """
    Returns full coverage telemetry:
    - All 28 States + 8 UTs coverage matrix
    - Sector breakdown (Central, State, PSU, Research, University, Healthcare, Regulators)
    - Active vs Discovered vs Blocked sources
    """
    return GovernmentDiscoveryEngine.get_coverage(db)


@router.get("/government/vacancies", response_model=GovernmentVacancyListResponse)
def list_government_vacancies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    state: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    change_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Lists discovered government vacancies with enriched public-sector metadata
    (contract duration, pay scale, official PDF, corrigendum status, match score, decision).
    """
    query = db.query(GovernmentVacancy)
    if state:
        query = query.filter(GovernmentVacancy.state.ilike(f"%{state}%"))
    if employment_type:
        query = query.filter(GovernmentVacancy.employment_type == employment_type)
    if change_type:
        query = query.filter(GovernmentVacancy.change_type == change_type)

    total = query.count()
    items = query.order_by(desc(GovernmentVacancy.created_at)).offset(skip).limit(limit).all()

    results: List[GovernmentVacancyResponse] = []
    for it in items:
        # Load associated job & match/decision info
        job = db.query(Job).filter(Job.id == it.job_id).first()
        match = db.query(MatchResult).filter(MatchResult.job_id == it.job_id).first()
        decision = db.query(ApplicationDecision).filter(ApplicationDecision.job_id == it.job_id).first()

        res = GovernmentVacancyResponse(
            id=it.id,
            job_id=it.job_id,
            source_id=it.source_id,
            organisation_name=it.source.organisation_name if it.source else (job.company if job else None),
            title=job.title if job else None,
            government_level=it.government_level,
            organisation_type=it.organisation_type,
            state=it.state,
            department=it.department,
            ministry=it.ministry,
            scheme_or_project=it.scheme_or_project,
            advertisement_number=it.advertisement_number,
            employment_type=it.employment_type,
            contract_duration=it.contract_duration,
            pay_scale=it.pay_scale,
            number_of_positions=it.number_of_positions,
            age_limit=it.age_limit,
            selection_process=it.selection_process,
            official_notification_url=it.official_notification_url,
            official_application_url=it.official_application_url,
            application_mode=it.application_mode,
            application_email=it.application_email,
            pdf_url=it.pdf_url,
            pdf_sha256=it.pdf_sha256,
            extraction_status=it.extraction_status,
            change_type=it.change_type,
            corrigendum_details=it.corrigendum_details,
            published_at=it.published_at,
            application_deadline=it.application_deadline,
            deadline_status=it.deadline_status,
            last_verified_at=it.last_verified_at,
            created_at=it.created_at,
            updated_at=it.updated_at,
            job_title=job.title if job else None,
            job_company=job.company if job else None,
            job_location=job.location if job else None,
            match_score=match.overall_score if match else None,
            fit_category=match.fit_category if match else None,
            decision=decision.decision if decision else None,
        )
        results.append(res)

    return GovernmentVacancyListResponse(total=total, items=results)


@router.get("/government/runs", response_model=List[GovernmentDiscoveryRunResponse])
def list_government_discovery_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Returns historical discovery runs and crawl metrics."""
    runs = db.query(GovernmentDiscoveryRun).order_by(desc(GovernmentDiscoveryRun.created_at)).limit(limit).all()
    return [GovernmentDiscoveryRunResponse.model_validate(r) for r in runs]


@router.get("/government/monitoring/stats", response_model=GovernmentMonitoringStatsResponse)
def get_government_monitoring_stats(db: Session = Depends(get_db)):
    """
    Returns full continuous monitoring and freshness telemetry:
    - Registered, scheduled, never crawled, due, overdue, and crawling sources
    - Today's crawls, successes, failures, blocked, manual access
    - Vacancy change counters (corrigenda, extensions, expired)
    - Freshness SLA compliance metrics
    """
    metrics = GovernmentContinuousScheduler.get_monitoring_metrics(db)
    return GovernmentMonitoringStatsResponse(**metrics)


@router.post("/government/monitoring/tick", response_model=GovernmentMonitoringTickResponse)
def run_continuous_monitoring_tick(
    batch_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Triggers an autonomous continuous monitoring scheduler cycle:
    1. Initializes unscheduled sources (fixing 71-pending issue).
    2. Revalidates vacancy deadlines.
    3. Enqueues catch-up crawls for overdue sources with idempotency.
    4. Evaluates 24h search engine rediscovery.
    """
    res = GovernmentContinuousScheduler.enqueue_monitoring_tasks(db=db, batch_size=batch_size)
    return GovernmentMonitoringTickResponse(**res)


@router.post("/government/deadlines/recheck")
def recheck_vacancy_deadlines(db: Session = Depends(get_db)):
    """
    Re-evaluates application deadlines across all active vacancies,
    updating states to OPEN, DEADLINE_APPROACHING, DEADLINE_TODAY, EXPIRED, EXTENDED.
    """
    return GovernmentContinuousScheduler.revalidate_vacancy_deadlines(db)


@router.get("/government/changes", response_model=List[GovernmentChangeEventResponse])
def list_government_changes(
    limit: int = Query(50, ge=1, le=200),
    change_type: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns audit trail of detected changes across government sources and vacancies
    (NEW, UPDATED, EXTENDED, CORRIGENDUM, CLOSED).
    """
    query = db.query(GovernmentChangeEvent)
    if change_type:
        query = query.filter(GovernmentChangeEvent.change_type == change_type.upper())
    if source_id:
        query = query.filter(GovernmentChangeEvent.source_id == source_id)

    items = query.order_by(desc(GovernmentChangeEvent.detected_at)).limit(limit).all()
    return [GovernmentChangeEventResponse.model_validate(it) for it in items]


@router.post("/government/universe/execute", response_model=GovernmentUniverseMissionResponse)
def execute_government_universe_mission(
    payload: GovernmentUniverseMissionRequest = GovernmentUniverseMissionRequest(),
    db: Session = Depends(get_db)
):
    """
    Executes the comprehensive 10-pass Indian Government Job Source Discovery mission:
    1. MD universe ingestion & authoritative resolution
    2. Parent -> child recursive linking
    3. 28 States + 8 UTs exhaustive expansion
    4. District & Municipal local-government expansion
    5. Recruitment endpoint verification
    6. PDF discovery, SHA-256 hashing, and vacancy extraction
    7. Rotated search engine discovery
    8. Recursive child organisation feedback
    9. Anti-duplicate reconciliation & candidate matching
    10. Continuous monitoring queue scheduling & deadline protection
    """
    res = GovernmentDiscoveryEngine.execute_universe_discovery_mission(
        db=db,
        max_passes=payload.max_passes,
        run_search=payload.run_search,
        batch_size=payload.batch_size,
    )
    return GovernmentUniverseMissionResponse(**res)


@router.get("/government/universe/stats")
def get_universe_discovery_stats(db: Session = Depends(get_db)):
    """
    Returns telemetry on universe targets, verified sources, and unresolved backlogs.
    """
    parsed = GovernmentUniverseParser.parse_universe_files()
    total_sources = db.query(GovernmentSource).count()
    unresolved_count = db.query(GovernmentUnresolvedTarget).count()
    unresolved_by_type = {}
    for r in db.query(GovernmentUnresolvedTarget.target_type).all():
        unresolved_by_type[r[0]] = unresolved_by_type.get(r[0], 0) + 1

    return {
        "total_raw_targets": parsed["total_raw_targets"],
        "total_deduplicated_targets": parsed["total_deduplicated_targets"],
        "target_counts_by_type": parsed["counts_by_type"],
        "target_counts_by_phase": parsed["counts_by_phase"],
        "verified_registered_sources": total_sources,
        "unresolved_backlog_targets": unresolved_count,
        "unresolved_by_type": unresolved_by_type,
    }


@router.get("/government/unresolved", response_model=GovernmentUnresolvedTargetListResponse)
def list_unresolved_targets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    target_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns paginated targets from the persistent Unresolved Source Backlog (Phase 15).
    """
    query = db.query(GovernmentUnresolvedTarget)
    if target_type:
        query = query.filter(GovernmentUnresolvedTarget.target_type == target_type.upper())
    if state:
        query = query.filter(GovernmentUnresolvedTarget.state.ilike(f"%{state}%"))

    total = query.count()
    items = query.order_by(desc(GovernmentUnresolvedTarget.last_attempted_at)).offset(skip).limit(limit).all()
    return GovernmentUnresolvedTargetListResponse(
        total=total,
        items=[GovernmentUnresolvedTargetResponse.model_validate(it) for it in items]
    )


@router.get("/government/sources/hierarchy")
def get_sources_hierarchy(db: Session = Depends(get_db)):
    """
    Returns the discovery graph hierarchy of parent organisations and child sources (Phase 16).
    """
    parents = db.query(GovernmentSource).filter(GovernmentSource.parent_source_id.is_(None)).all()
    hierarchy = []
    for p in parents:
        children = db.query(GovernmentSource).filter(GovernmentSource.parent_source_id == p.id).all()
        hierarchy.append({
            "parent_id": p.id,
            "organisation_name": p.organisation_name,
            "domain": p.official_domain,
            "level": p.government_level,
            "type": p.organisation_type,
            "children_count": len(children),
            "children": [
                {
                    "child_id": c.id,
                    "organisation_name": c.organisation_name,
                    "domain": c.official_domain,
                    "type": c.organisation_type,
                }
                for c in children
            ]
        })
    return {"total_parents": len(parents), "hierarchy": hierarchy}

