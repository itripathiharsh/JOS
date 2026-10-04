import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.profile import CandidateProfile, CandidatePreference, Skill
from app.models.discovery import DiscoveryRun
from app.models.job import SearchQuery
from app.schemas.discovery import (
    DiscoveryConfig,
    SearchStrategyQuery,
    DiscoveryPreviewResponse,
    DiscoveryRunSummary,
    DiscoveryQueryExecution,
    DiscoveryRunListResponse,
)
from app.services.search_expansion_service import SearchStrategyEngine
from app.services.job_ingestion_service import (
    ingest_jobs_from_source,
    get_source_connector,
    SOURCE_REGISTRY,
)

logger = logging.getLogger(__name__)


def preview_discovery(
    db: Session,
    config: Optional[DiscoveryConfig] = None,
    source_name: str = "remotive",
) -> DiscoveryPreviewResponse:
    """
    Preview generated search strategies for candidate preferences without executing network ingestion.
    """
    cfg = config or DiscoveryConfig()
    profile = db.query(CandidateProfile).first()
    connector = get_source_connector(source_name)
    caps = connector.capabilities if connector else None

    target_roles: List[str] = []
    preferred_locations: List[str] = []
    work_modes: List[str] = []
    candidate_skills: List[str] = []
    candidate_name = "Candidate"
    candidate_id = None

    if profile:
        candidate_name = profile.name or "Candidate"
        candidate_id = profile.id
        candidate_skills = [s.name for s in profile.skills]
        if profile.preference_record:
            pref = profile.preference_record
            target_roles = pref.target_roles or []
            preferred_locations = pref.preferred_locations or []
            work_modes = pref.work_modes or []

    # Fallback to sensible defaults if preferences are missing/empty
    if not target_roles:
        target_roles = ["AI Engineer", "ML Engineer", "Backend Engineer"]
    if not work_modes:
        work_modes = ["Remote"]

    engine = SearchStrategyEngine()
    strategies = engine.generate_strategies(
        target_roles=target_roles,
        preferred_locations=preferred_locations,
        work_modes=work_modes,
        candidate_skills=candidate_skills,
        capabilities=caps,
        config=cfg,
    )

    priority_breakdown = {
        "HIGH": sum(1 for q in strategies if q.priority == "HIGH"),
        "MEDIUM": sum(1 for q in strategies if q.priority == "MEDIUM"),
        "LOW": sum(1 for q in strategies if q.priority == "LOW"),
    }

    return DiscoveryPreviewResponse(
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        target_roles=target_roles,
        total_strategies=len(strategies),
        priority_breakdown=priority_breakdown,
        queries=strategies,
    )


def execute_discovery_run(
    db: Session,
    source_name: str = "remotive",
    config: Optional[DiscoveryConfig] = None,
    dry_run: bool = False,
) -> DiscoveryRunSummary:
    """
    Execute a controlled discovery run:
    1. Load candidate preferences.
    2. Generate prioritized, bounded, deduplicated search strategies.
    3. Execute each query via the existing source ingestion pipeline with failure isolation.
    4. Aggregate and persist discovery statistics in DB.
    """
    cfg = config or DiscoveryConfig()
    start_time = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)

    # 1. Load candidate profile and preferences
    profile = db.query(CandidateProfile).first()
    connector = get_source_connector(source_name)
    if not connector:
        raise ValueError(f"Unknown job source: '{source_name}'. Registered: {list(SOURCE_REGISTRY.keys())}")

    target_roles: List[str] = []
    preferred_locations: List[str] = []
    work_modes: List[str] = []
    candidate_skills: List[str] = []
    candidate_id = profile.id if profile else None

    if profile:
        candidate_skills = [s.name for s in profile.skills]
        if profile.preference_record:
            pref = profile.preference_record
            target_roles = pref.target_roles or []
            preferred_locations = pref.preferred_locations or []
            work_modes = pref.work_modes or []

    if not target_roles:
        target_roles = ["AI Engineer", "ML Engineer", "Backend Engineer"]
    if not work_modes:
        work_modes = ["Remote"]

    # 2. Generate strategies
    engine = SearchStrategyEngine()
    strategies = engine.generate_strategies(
        target_roles=target_roles,
        preferred_locations=preferred_locations,
        work_modes=work_modes,
        candidate_skills=candidate_skills,
        capabilities=connector.capabilities,
        config=cfg,
    )

    if dry_run:
        # Dry-run returns generated strategies without network calls or DB mutations
        return DiscoveryRunSummary(
            id="dry-run",
            source=connector.name,
            status="completed",
            queries_generated=len(strategies),
            queries_executed=0,
            successful_queries=0,
            failed_queries=0,
            jobs_fetched=0,
            jobs_created=0,
            jobs_updated=0,
            jobs_skipped=0,
            duration_ms=0.0,
            created_at=now,
            completed_at=now,
            executed_queries=[
                DiscoveryQueryExecution(
                    query=s.query,
                    canonical_role=s.canonical_role,
                    strategy=s.strategy,
                    priority=s.priority,
                    status="dry_run",
                )
                for s in strategies
            ],
            errors=[],
        )

    # 3. Create persistent DiscoveryRun record
    run_record = DiscoveryRun(
        candidate_id=candidate_id,
        source=connector.name,
        status="in_progress",
        queries_generated=len(strategies),
        parameters=json.dumps(cfg.model_dump()),
        created_at=now,
    )
    db.add(run_record)
    db.commit()
    db.refresh(run_record)

    executed_queries: List[DiscoveryQueryExecution] = []
    successful_count = 0
    failed_count = 0
    total_fetched = 0
    total_created = 0
    total_updated = 0
    total_skipped = 0
    run_errors: List[str] = []

    # 4. Execute queries sequentially with FAILURE ISOLATION
    for strategy in strategies:
        q_start = time.perf_counter()
        query_text = strategy.query
        try:
            stats = ingest_jobs_from_source(
                db=db,
                source_name=connector.name,
                keyword=query_text,
                location=strategy.location_filter,
                remote=strategy.remote_filter,
                limit=strategy.limit,
                extra_telemetry={
                    "discovery_run_id": run_record.id,
                    "canonical_role": strategy.canonical_role,
                    "strategy": strategy.strategy,
                    "priority": strategy.priority,
                    "reason": strategy.reason,
                },
            )
            q_duration_ms = round((time.perf_counter() - q_start) * 1000, 2)

            has_error = stats.jobs_fetched == 0 and len(stats.errors) > 0
            if has_error:
                failed_count += 1
                err_text = stats.errors[0] if stats.errors else "Unknown connector error"
                run_errors.append(f"Query '{query_text}' failed: {err_text}")
                executed_queries.append(
                    DiscoveryQueryExecution(
                        query=query_text,
                        canonical_role=strategy.canonical_role,
                        strategy=strategy.strategy,
                        priority=strategy.priority,
                        status="failed",
                        jobs_fetched=0,
                        jobs_created=0,
                        jobs_updated=0,
                        jobs_skipped=stats.jobs_skipped,
                        duration_ms=q_duration_ms,
                        error=err_text,
                    )
                )
            else:
                successful_count += 1
                total_fetched += stats.jobs_fetched
                total_created += stats.jobs_created
                total_updated += stats.jobs_updated
                total_skipped += stats.jobs_skipped
                executed_queries.append(
                    DiscoveryQueryExecution(
                        query=query_text,
                        canonical_role=strategy.canonical_role,
                        strategy=strategy.strategy,
                        priority=strategy.priority,
                        status="completed",
                        jobs_fetched=stats.jobs_fetched,
                        jobs_created=stats.jobs_created,
                        jobs_updated=stats.jobs_updated,
                        jobs_skipped=stats.jobs_skipped,
                        duration_ms=q_duration_ms,
                    )
                )

        except Exception as exc:
            # Complete isolation: an unhandled query exception does NOT abort the run
            q_duration_ms = round((time.perf_counter() - q_start) * 1000, 2)
            failed_count += 1
            err_msg = f"Unexpected query error for '{query_text}': {str(exc)}"
            logger.error(err_msg, exc_info=True)
            run_errors.append(err_msg)
            executed_queries.append(
                DiscoveryQueryExecution(
                    query=query_text,
                    canonical_role=strategy.canonical_role,
                    strategy=strategy.strategy,
                    priority=strategy.priority,
                    status="failed",
                    duration_ms=q_duration_ms,
                    error=str(exc),
                )
            )

    # 5. Finalize DiscoveryRun record
    completed_time = datetime.now(timezone.utc)
    total_duration_ms = round((completed_time - start_time).total_seconds() * 1000, 2)

    run_record.queries_executed = len(executed_queries)
    run_record.successful_queries = successful_count
    run_record.failed_queries = failed_count
    run_record.jobs_fetched = total_fetched
    run_record.jobs_created = total_created
    run_record.jobs_updated = total_updated
    run_record.jobs_skipped = total_skipped
    run_record.duration_ms = total_duration_ms
    run_record.completed_at = completed_time
    run_record.status = "completed" if successful_count > 0 or len(strategies) == 0 else "failed"
    if run_errors:
        run_record.error_message = "; ".join(run_errors[:3])

    try:
        db.commit()
        db.refresh(run_record)
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to commit DiscoveryRun {run_record.id}: {exc}")

    logger.info(
        f"Discovery Run {run_record.id} finished: "
        f"Generated={len(strategies)}, Executed={len(executed_queries)}, "
        f"Success={successful_count}, Failed={failed_count}, "
        f"Fetched={total_fetched}, Created={total_created}, Updated={total_updated}, "
        f"Duration={total_duration_ms}ms"
    )

    return DiscoveryRunSummary(
        id=run_record.id,
        source=run_record.source,
        status=run_record.status,
        queries_generated=run_record.queries_generated,
        queries_executed=run_record.queries_executed,
        successful_queries=run_record.successful_queries,
        failed_queries=run_record.failed_queries,
        jobs_fetched=run_record.jobs_fetched,
        jobs_created=run_record.jobs_created,
        jobs_updated=run_record.jobs_updated,
        jobs_skipped=run_record.jobs_skipped,
        duration_ms=float(run_record.duration_ms) if run_record.duration_ms else None,
        created_at=run_record.created_at,
        completed_at=run_record.completed_at,
        executed_queries=executed_queries,
        errors=run_errors,
    )


def get_discovery_runs(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> DiscoveryRunListResponse:
    """Retrieve historical discovery runs ordered by newest first."""
    query = db.query(DiscoveryRun).order_by(desc(DiscoveryRun.created_at))
    total = query.count()
    records = query.offset(skip).limit(limit).all()

    items = [
        DiscoveryRunSummary(
            id=r.id,
            source=r.source,
            status=r.status,
            queries_generated=r.queries_generated,
            queries_executed=r.queries_executed,
            successful_queries=r.successful_queries,
            failed_queries=r.failed_queries,
            jobs_fetched=r.jobs_fetched,
            jobs_created=r.jobs_created,
            jobs_updated=r.jobs_updated,
            jobs_skipped=r.jobs_skipped,
            duration_ms=float(r.duration_ms) if r.duration_ms else None,
            created_at=r.created_at,
            completed_at=r.completed_at,
            executed_queries=[],
            errors=[r.error_message] if r.error_message else [],
        )
        for r in records
    ]
    return DiscoveryRunListResponse(items=items, total=total)


def get_discovery_run_by_id(
    db: Session,
    run_id: str,
) -> Optional[DiscoveryRunSummary]:
    """Retrieve detailed discovery run and its associated SearchQuery records."""
    r = db.query(DiscoveryRun).filter(DiscoveryRun.id == run_id).first()
    if not r:
        return None

    # Load associated queries from search_queries table matching discovery_run_id
    executed_queries: List[DiscoveryQueryExecution] = []
    sq_records = db.query(SearchQuery).filter(
        SearchQuery.parameters.like(f"%{run_id}%")
    ).order_by(SearchQuery.created_at.asc()).all()

    for sq in sq_records:
        params: Dict[str, Any] = {}
        if sq.parameters:
            try:
                params = json.loads(sq.parameters)
            except Exception:
                pass

        executed_queries.append(
            DiscoveryQueryExecution(
                query=sq.query,
                canonical_role=params.get("canonical_role", "Unknown"),
                strategy=params.get("strategy", "unknown"),
                priority=params.get("priority", "MEDIUM"),
                status=sq.status,
                jobs_fetched=sq.result_count,
                jobs_created=params.get("jobs_created", 0),
                jobs_updated=params.get("jobs_updated", 0),
                jobs_skipped=params.get("jobs_skipped", 0),
                duration_ms=params.get("duration_ms"),
                error=params.get("error"),
            )
        )

    return DiscoveryRunSummary(
        id=r.id,
        source=r.source,
        status=r.status,
        queries_generated=r.queries_generated,
        queries_executed=r.queries_executed,
        successful_queries=r.successful_queries,
        failed_queries=r.failed_queries,
        jobs_fetched=r.jobs_fetched,
        jobs_created=r.jobs_created,
        jobs_updated=r.jobs_updated,
        jobs_skipped=r.jobs_skipped,
        duration_ms=float(r.duration_ms) if r.duration_ms else None,
        created_at=r.created_at,
        completed_at=r.completed_at,
        executed_queries=executed_queries,
        errors=[r.error_message] if r.error_message else [],
    )
