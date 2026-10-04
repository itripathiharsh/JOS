import sys
import os

workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.job import Job, Company, SourceStatus, SearchQuery
from connectors.base import JobSource
from connectors.remotive import RemotiveSource
from connectors.models import NormalizedJob, IngestionStats
from connectors.validation import validate_normalized_job
from connectors.exceptions import SourceException
from app.services.deduplication import normalize_url, AntiDuplicateEngine

logger = logging.getLogger(__name__)

# Registry of supported source connectors
SOURCE_REGISTRY: Dict[str, JobSource] = {
    "remotive": RemotiveSource(),
}


def get_source_connector(source_name: str) -> Optional[JobSource]:
    """Retrieve connector instance from registry by source name."""
    return SOURCE_REGISTRY.get(source_name.strip().lower())


def get_all_source_statuses(db: Session) -> List[Dict[str, Any]]:
    """Retrieve status of all registered sources from database and health check."""
    results = []
    for name, connector in SOURCE_REGISTRY.items():
        status_rec = db.query(SourceStatus).filter(SourceStatus.source == name).first()
        if not status_rec:
            status_rec = SourceStatus(
                source=name,
                status="idle",
                jobs_fetched=0,
                jobs_created=0,
                jobs_updated=0,
            )
            db.add(status_rec)
            db.commit()
            db.refresh(status_rec)

        results.append({
            "id": status_rec.id,
            "source": status_rec.source,
            "status": status_rec.status,
            "last_checked": status_rec.last_checked,
            "last_success": status_rec.last_success,
            "last_failure_at": status_rec.last_failure_at,
            "jobs_fetched": status_rec.jobs_fetched,
            "jobs_created": status_rec.jobs_created,
            "jobs_updated": status_rec.jobs_updated,
            "error_message": status_rec.error_message,
        })
    return results


def check_source_health(source_name: str, db: Session) -> Dict[str, Any]:
    """Execute live health check on a connector and update SourceStatus in DB."""
    connector = get_source_connector(source_name)
    if not connector:
        return {"healthy": False, "message": f"Source '{source_name}' not registered."}

    health = connector.health_check()
    now = datetime.now(timezone.utc)

    status_rec = db.query(SourceStatus).filter(SourceStatus.source == connector.name).first()
    if not status_rec:
        status_rec = SourceStatus(source=connector.name)
        db.add(status_rec)

    status_rec.last_checked = now
    if health.healthy:
        status_rec.status = "healthy"
        status_rec.last_success = now
        status_rec.error_message = None
    else:
        status_rec.status = "error"
        status_rec.last_failure_at = now
        status_rec.error_message = health.message

    db.commit()
    return health.model_dump()


def ingest_jobs_from_source(
    db: Session,
    source_name: str = "remotive",
    keyword: str = "",
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    limit: int = 20,
    extra_telemetry: Optional[Dict[str, Any]] = None,
) -> IngestionStats:
    """
    Execute full ingestion pipeline:
    FETCH -> NORMALIZE -> VALIDATE -> DEDUPLICATE / UPSERT -> STORE -> UPDATE SOURCE STATUS & SEARCH QUERY
    Supports optional extra_telemetry dictionary to link queries to discovery runs, strategies, and roles.
    """
    now = datetime.now(timezone.utc)
    connector = get_source_connector(source_name)
    if not connector:
        raise ValueError(f"Unknown job source connector: '{source_name}'. Registered: {list(SOURCE_REGISTRY.keys())}")

    stats = IngestionStats(source=connector.name, query=keyword)
    start_time = datetime.now(timezone.utc)

    # 1. Fetch normalized jobs from connector
    try:
        normalized_jobs = connector.search(
            query=keyword,
            location=location,
            remote=remote,
            limit=limit,
        )
        stats.jobs_fetched = len(normalized_jobs)
    except (SourceException, Exception) as exc:
        duration_ms = round((datetime.now(timezone.utc) - start_time).total_seconds() * 1000, 2)
        err_msg = f"Connector fetch failed for {connector.name}: {str(exc)}"
        logger.error(err_msg, exc_info=True)
        stats.errors.append(err_msg)
        fail_params = {"limit": limit, "remote": remote, "duration_ms": duration_ms, "error": err_msg}
        if extra_telemetry:
            fail_params.update(extra_telemetry)
        _record_search_query(
            db=db,
            source=connector.name,
            keyword=keyword,
            location=location,
            parameters=fail_params,
            result_count=0,
            status="failed",
        )
        _update_source_status_failure(db, connector.name, err_msg)
        return stats

    # 2. Track intra-batch and database records to prevent duplicate key collisions
    seen_in_batch: Dict[Tuple[str, str], Job] = {}

    for norm in normalized_jobs:
        try:
            # Rigorous validation before persistence
            is_valid, validation_err = validate_normalized_job(norm)
            if not is_valid:
                stats.jobs_skipped += 1
                stats.errors.append(f"Job {norm.external_job_id}: {validation_err}")
                logger.warning(f"Skipping invalid job {norm.external_job_id} from {norm.source}: {validation_err}")
                continue

            # Ensure company record exists in companies table
            comp_name = norm.company.strip()
            existing_company = db.query(Company).filter(Company.name == comp_name).first()
            if not existing_company:
                try:
                    new_company = Company(name=comp_name)
                    db.add(new_company)
                    db.flush()
                except Exception as comp_exc:
                    # Ignore unique constraint race condition on company name
                    logger.debug(f"Company '{comp_name}' already registered: {comp_exc}")
                    db.rollback()

            batch_key = (norm.source, norm.external_job_id)

            # Check if already processed in this batch
            if batch_key in seen_in_batch:
                existing = seen_in_batch[batch_key]
                existing.title = norm.title
                existing.company = norm.company
                if norm.location is not None:
                    existing.location = norm.location
                if norm.work_mode is not None:
                    existing.work_mode = norm.work_mode
                if norm.description is not None:
                    existing.description = norm.description
                if norm.requirements is not None:
                    existing.requirements = norm.requirements
                if norm.responsibilities is not None:
                    existing.responsibilities = norm.responsibilities
                if norm.salary_min is not None:
                    existing.salary_min = norm.salary_min
                if norm.salary_max is not None:
                    existing.salary_max = norm.salary_max
                if norm.currency is not None:
                    existing.currency = norm.currency
                if norm.url is not None:
                    existing.application_url = norm.url
                if norm.posted_at is not None:
                    existing.posted_at = norm.posted_at
                if norm.expires_at is not None:
                    existing.expires_at = norm.expires_at
                if norm.raw_payload is not None:
                    existing.raw_payload = json.dumps(norm.raw_payload)

                existing.last_seen_at = now
                existing.updated_at = now
                stats.jobs_updated += 1
                continue

            # Check if existing in PostgreSQL
            existing = db.query(Job).filter(
                Job.source == norm.source,
                Job.external_job_id == norm.external_job_id
            ).first()

            if existing:
                # Update changed fields & refresh last_seen_at
                existing.title = norm.title
                existing.company = norm.company
                if norm.location is not None:
                    existing.location = norm.location
                if norm.work_mode is not None:
                    existing.work_mode = norm.work_mode
                if norm.description is not None:
                    existing.description = norm.description
                if norm.requirements is not None:
                    existing.requirements = norm.requirements
                if norm.responsibilities is not None:
                    existing.responsibilities = norm.responsibilities
                if norm.salary_min is not None:
                    existing.salary_min = norm.salary_min
                if norm.salary_max is not None:
                    existing.salary_max = norm.salary_max
                if norm.currency is not None:
                    existing.currency = norm.currency
                if norm.url is not None:
                    existing.application_url = norm.url
                    existing.canonical_url = normalize_url(norm.url)
                if norm.posted_at is not None:
                    existing.posted_at = norm.posted_at
                if norm.expires_at is not None:
                    existing.expires_at = norm.expires_at
                if norm.raw_payload is not None:
                    existing.raw_payload = json.dumps(norm.raw_payload)

                existing.last_seen_at = now
                existing.updated_at = now
                seen_in_batch[batch_key] = existing
                stats.jobs_updated += 1
            else:
                # Insert new Job record
                canonical_url = normalize_url(norm.url) if norm.url else None
                new_job = Job(
                    source=norm.source,
                    external_job_id=norm.external_job_id,
                    application_url=norm.url,
                    canonical_url=canonical_url,
                    title=norm.title,
                    company=norm.company,
                    location=norm.location,
                    work_mode=norm.work_mode,
                    description=norm.description,
                    requirements=norm.requirements,
                    responsibilities=norm.responsibilities,
                    salary_min=norm.salary_min,
                    salary_max=norm.salary_max,
                    currency=norm.currency,
                    posted_at=norm.posted_at,
                    expires_at=norm.expires_at,
                    discovered_at=now,
                    last_seen_at=now,
                    status="discovered",
                    is_canonical=True,
                    duplicate_status="canonical",
                    raw_payload=json.dumps(norm.raw_payload) if norm.raw_payload else None,
                )
                db.add(new_job)
                db.flush()
                # Run Step 6 Cross-Source Anti-Duplicate Evaluation
                AntiDuplicateEngine.evaluate_and_link(db, new_job)
                seen_in_batch[batch_key] = new_job
                stats.jobs_created += 1

        except Exception as exc:
            db.rollback()
            logger.error(f"Error persisting job {norm.external_job_id}: {exc}", exc_info=True)
            stats.errors.append(f"Job {norm.external_job_id}: {str(exc)}")
            stats.jobs_skipped += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        err_msg = f"Database commit failed during ingestion: {exc}"
        logger.error(err_msg, exc_info=True)
        stats.errors.append(err_msg)
        _update_source_status_failure(db, connector.name, err_msg)
        return stats

    duration_ms = round((datetime.now(timezone.utc) - start_time).total_seconds() * 1000, 2)
    duration_sec = round(duration_ms / 1000.0, 2)

    # 3. Record SearchQuery with rich telemetry
    success_params = {
        "limit": limit,
        "remote": remote,
        "duration_ms": duration_ms,
        "jobs_fetched": stats.jobs_fetched,
        "jobs_created": stats.jobs_created,
        "jobs_updated": stats.jobs_updated,
        "jobs_skipped": stats.jobs_skipped,
    }
    if extra_telemetry:
        success_params.update(extra_telemetry)

    _record_search_query(
        db=db,
        source=connector.name,
        keyword=keyword,
        location=location,
        parameters=success_params,
        result_count=stats.jobs_fetched,
        status="completed"
    )

    # 4. Update SourceStatus
    _update_source_status_success(
        db=db,
        source=connector.name,
        fetched=stats.jobs_fetched,
        created=stats.jobs_created,
        updated=stats.jobs_updated,
    )

    logger.info(
        f"Ingestion completed for [{connector.name}]: "
        f"Fetched={stats.jobs_fetched}, Created={stats.jobs_created}, "
        f"Updated={stats.jobs_updated}, Skipped={stats.jobs_skipped}, "
        f"Duration={duration_sec}s"
    )

    return stats


def _record_search_query(
    db: Session,
    source: str,
    keyword: str,
    location: Optional[str],
    parameters: Dict[str, Any],
    result_count: int,
    status: str,
) -> None:
    """Record search query execution details."""
    try:
        sq = SearchQuery(
            query=keyword or "ALL",
            source=source,
            location=location,
            parameters=json.dumps(parameters),
            result_count=result_count,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
        db.add(sq)
        db.commit()
    except Exception as exc:
        logger.warning(f"Failed to record SearchQuery: {exc}")
        db.rollback()


def _update_source_status_success(
    db: Session,
    source: str,
    fetched: int,
    created: int,
    updated: int,
) -> None:
    """Update SourceStatus table on successful ingestion."""
    try:
        now = datetime.now(timezone.utc)
        status_rec = db.query(SourceStatus).filter(SourceStatus.source == source).first()
        if not status_rec:
            status_rec = SourceStatus(
                source=source,
                jobs_fetched=0,
                jobs_created=0,
                jobs_updated=0,
            )
            db.add(status_rec)

        status_rec.status = "active"
        status_rec.last_checked = now
        status_rec.last_success = now
        status_rec.jobs_fetched = (status_rec.jobs_fetched or 0) + fetched
        status_rec.jobs_created = (status_rec.jobs_created or 0) + created
        status_rec.jobs_updated = (status_rec.jobs_updated or 0) + updated
        status_rec.error_message = None

        db.commit()
    except Exception as exc:
        logger.warning(f"Failed to update SourceStatus on success: {exc}")
        db.rollback()


def _update_source_status_failure(db: Session, source: str, error_msg: str) -> None:
    """Update SourceStatus table on failed ingestion."""
    try:
        now = datetime.now(timezone.utc)
        status_rec = db.query(SourceStatus).filter(SourceStatus.source == source).first()
        if not status_rec:
            status_rec = SourceStatus(source=source)
            db.add(status_rec)

        status_rec.status = "error"
        status_rec.last_checked = now
        status_rec.last_failure_at = now
        status_rec.error_message = error_msg[:1000]

        db.commit()
    except Exception as exc:
        logger.warning(f"Failed to update SourceStatus on failure: {exc}")
        db.rollback()
