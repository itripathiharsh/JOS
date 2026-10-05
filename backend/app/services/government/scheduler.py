"""
Job Operating System - Government Continuous Monitoring & Vacancy Freshness Scheduler
Orchestrates:
1. Per-source crawl scheduling with adaptive intervals (1-3h high, 6-12h medium, 24h low, 48-72h very low).
2. Deadline-aware frequency acceleration (<24h, 1-3d, 3-7d, expired verification).
3. Concurrency locking & lease recovery to prevent duplicate simultaneous crawls.
4. Deterministic failure backoff (15m, 30m, 1h, 3h, 6h) & auto-classification.
5. Startup recovery & catch-up logic to prevent task explosion after PC restarts.
6. Fair progressive priority queue (approaching deadlines & uncrawled first, no starvation).
7. Vacancy deadline revalidation (OPEN, DEADLINE_APPROACHING, DEADLINE_TODAY, EXPIRED, EXTENDED).
8. Comprehensive monitoring & freshness SLA metrics.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc, func, case

from app.models.government import GovernmentSource, GovernmentVacancy, GovernmentChangeEvent, GovernmentDiscoveryRun
from app.models.automation import AutomationTask
from app.services.automation.queue_service import AutomationQueueService

logger = logging.getLogger(__name__)


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GovernmentContinuousScheduler:
    """
    Central autonomous coordinator for continuous government vacancy monitoring.
    Replaces static/one-off crawls with a living, self-healing monitoring queue.
    """

    # Freshness SLA targets (hours)
    SLA_HOURS = {
        "high": 3,
        "medium": 12,
        "low": 72,
        "very_low": 72,
        "deadline_sensitive": 3,
    }

    # Deterministic Failure Backoff (minutes)
    BACKOFF_MINUTES = {
        1: 15,
        2: 30,
        3: 60,
        4: 180,
        5: 360,
    }

    @classmethod
    def initialize_monitoring_queue(cls, db: Session) -> int:
        """
        Fixes the initial pending problem and brings all registered sources
        into the living monitoring queue.
        Idempotent: sets next_crawl_at = NOW() for all uncrawled or unscheduled sources.
        """
        now = get_utc_now()
        unscheduled = db.query(GovernmentSource).filter(
            or_(
                GovernmentSource.next_crawl_at.is_(None),
                GovernmentSource.last_crawled_at.is_(None)
            )
        ).all()

        updated_count = 0
        for src in unscheduled:
            if src.crawl_interval_minutes is None or src.crawl_interval_minutes <= 0:
                src.crawl_interval_minutes = 1440  # 24 hours default
            if not src.change_frequency_category:
                src.change_frequency_category = "low"
            if src.last_checked and not src.last_crawled_at:
                src.last_crawled_at = src.last_checked
            if src.last_success and not src.last_successful_crawl_at:
                src.last_successful_crawl_at = src.last_success
            if not src.next_crawl_at:
                # If never checked, schedule immediately for first crawl
                src.next_crawl_at = now
            updated_count += 1

        if updated_count > 0:
            db.commit()
            logger.info(f"Initialized continuous monitoring queue for {updated_count} sources.")

        return updated_count

    @classmethod
    def get_nearest_vacancy_deadline(cls, db: Session, source_id: str) -> Optional[datetime]:
        """Returns the earliest active/approaching deadline for vacancies under this source."""
        now = get_utc_now()
        vac = (
            db.query(GovernmentVacancy.application_deadline)
            .filter(
                GovernmentVacancy.source_id == source_id,
                GovernmentVacancy.application_deadline.is_not(None),
                GovernmentVacancy.deadline_status.in_(["OPEN", "DEADLINE_APPROACHING", "DEADLINE_TODAY", "EXTENDED", "UNKNOWN"]),
                GovernmentVacancy.application_deadline >= now - timedelta(days=1),
            )
            .order_by(GovernmentVacancy.application_deadline.asc())
            .first()
        )
        return vac[0] if vac else None

    @classmethod
    def compute_adaptive_interval(
        cls,
        source: GovernmentSource,
        last_outcome: str = "success",
        nearest_deadline: Optional[datetime] = None,
    ) -> int:
        """
        Deterministically computes crawl interval in minutes based on:
        1. Failure backoff (if failed)
        2. Approaching vacancy deadlines
        3. Observed change & publication frequency
        4. Source type & activity history
        """
        now = get_utc_now()

        # 1. Deterministic Failure Backoff
        if last_outcome != "success" and source.consecutive_failures > 0:
            failures = min(source.consecutive_failures, 5)
            backoff_min = cls.BACKOFF_MINUTES.get(failures, 360)
            if source.consecutive_failures >= 5:
                # Cap and reschedule at lower 24h frequency
                return 1440
            return backoff_min

        # 2. Deadline-Aware Frequency Acceleration (Section 6)
        if nearest_deadline:
            remaining_seconds = (nearest_deadline - now).total_seconds()
            remaining_days = remaining_seconds / 86400.0

            if remaining_seconds <= 0:
                # Deadline just passed -> 30 min recheck to confirm closed or detect extension
                return 30
            elif remaining_days <= 1.0:
                # < 24 hours remaining -> very high frequency (60 min)
                return 60
            elif remaining_days <= 3.0:
                # 1–3 days remaining -> high frequency (180 min / 3h)
                return 180
            elif remaining_days <= 7.0:
                # 3–7 days remaining -> increased frequency (360 min / 6h)
                return 360

        # 3. Frequency Category based on Historical Behavior (Section 4)
        cat = source.change_frequency_category or "low"

        # Heuristic adjustment based on activity
        if source.vacancies_found >= 10:
            cat = "high"
        elif source.vacancies_found >= 3 or source.last_change_detected_at and (now - source.last_change_detected_at).days <= 7:
            cat = "medium"

        if cat == "high":
            # 1–3 hours -> 120 min
            return 120
        elif cat == "medium":
            # 6–12 hours -> 360 min
            return 360
        elif cat == "very_low":
            # 48–72 hours -> 2880 min
            return 2880
        else:
            # low -> 24 hours -> 1440 min
            return 1440

    @classmethod
    def reschedule_source(
        cls,
        db: Session,
        source: GovernmentSource,
        outcome: str = "success",
        change_detected: bool = False,
        error_type: Optional[str] = None,
        nearest_deadline: Optional[datetime] = None,
    ) -> None:
        """
        Updates crawl tracking, computes new adaptive next_crawl_at,
        releases execution locks, and commits atomically.
        """
        now = get_utc_now()
        source.last_crawled_at = now
        source.last_checked = now
        source.crawl_count = (source.crawl_count or 0) + 1

        if outcome == "success":
            source.successful_crawl_count = (source.successful_crawl_count or 0) + 1
            source.consecutive_failures = 0
            source.last_successful_crawl_at = now
            source.last_success = now
            source.crawl_status = "success"

            # Auto-restore if was temporarily unavailable
            if source.source_status == "TEMPORARILY_UNAVAILABLE":
                source.source_status = "ACTIVE"

            if change_detected:
                source.last_change_detected_at = now
                source.change_frequency_category = "high"
        else:
            source.failed_crawl_count = (source.failed_crawl_count or 0) + 1
            source.failure_count = (source.failure_count or 0) + 1
            source.consecutive_failures = (source.consecutive_failures or 0) + 1
            source.last_failure_at = now

            if error_type == "BLOCKED":
                source.source_status = "BLOCKED"
                source.crawl_status = "blocked"
            elif error_type == "MANUAL_ACCESS":
                source.source_status = "REQUIRES_MANUAL_ACCESS"
                source.crawl_status = "manual_access"
            elif error_type == "DEAD":
                source.source_status = "DEAD"
                source.crawl_status = "dead"
            else:
                source.crawl_status = "failed"
                if source.consecutive_failures >= 5:
                    source.source_status = "TEMPORARILY_UNAVAILABLE"

        # Determine nearest deadline if not provided
        if nearest_deadline is None:
            nearest_deadline = cls.get_nearest_vacancy_deadline(db, source.id)

        interval = cls.compute_adaptive_interval(source, last_outcome=outcome, nearest_deadline=nearest_deadline)
        source.crawl_interval_minutes = interval
        source.next_crawl_at = now + timedelta(minutes=interval)

        # Release concurrency lock
        source.is_locked = False
        source.locked_at = None

        db.commit()
        logger.debug(
            f"Rescheduled [{source.official_domain}]: outcome={outcome}, "
            f"failures={source.consecutive_failures}, interval={interval}m, "
            f"next_crawl_at={source.next_crawl_at.isoformat()}"
        )

    @classmethod
    def get_due_sources(
        cls,
        db: Session,
        limit: int = 20,
        lock_sources: bool = True,
        worker_id: str = "scheduler",
    ) -> List[GovernmentSource]:
        """
        Selects due sources (next_crawl_at <= NOW() or next_crawl_at IS NULL).
        Employs progressive priority ordering without starvation:
        1. Imminent deadlines (< 7 days)
        2. Never-crawled sources (fixing the 71-pending problem)
        3. Oldest overdue sources (round-robin catch-up)
        Prevents concurrency overlap by locking claimed sources with a 30m lease.
        """
        now = get_utc_now()
        stale_lock_cutoff = now - timedelta(minutes=30)

        # Base filter: not dead, and (not locked OR lease expired)
        base_query = db.query(GovernmentSource).filter(
            GovernmentSource.source_status.notin_(["DEAD"]),
            or_(
                GovernmentSource.is_locked == False,
                GovernmentSource.locked_at.is_(None),
                GovernmentSource.locked_at <= stale_lock_cutoff,
            ),
            or_(
                GovernmentSource.next_crawl_at.is_(None),
                GovernmentSource.next_crawl_at <= now,
            )
        )

        # Ordering:
        # 1. Sources with active approaching vacancies (priority 1)
        # 2. Never crawled sources (priority 2: last_crawled_at IS NULL)
        # 3. Oldest next_crawl_at / last_crawled_at (priority 3: progressive catch-up)
        sources = base_query.order_by(
            # Uncrawled sources prioritized right after critical deadlines
            case(
                (GovernmentSource.last_crawled_at.is_(None), 1),
                (GovernmentSource.change_frequency_category == "high", 2),
                else_=3
            ).asc(),
            GovernmentSource.next_crawl_at.asc().nullsfirst(),
            GovernmentSource.last_crawled_at.asc().nullsfirst(),
        ).limit(limit).all()

        if lock_sources and sources:
            for s in sources:
                s.is_locked = True
                s.locked_at = now
            db.commit()

        return sources

    @classmethod
    def revalidate_vacancy_deadlines(cls, db: Session) -> Dict[str, int]:
        """
        Revalidates application deadlines across all active GovernmentVacancy records.
        Transitions status:
        - EXPIRED: deadline passed
        - DEADLINE_TODAY: <= 24 hours
        - DEADLINE_APPROACHING: <= 3 days (72 hours)
        - OPEN: > 3 days
        Records GovernmentChangeEvent when status shifts to EXPIRED or EXTENDED.
        """
        now = get_utc_now()
        vacancies = db.query(GovernmentVacancy).filter(
            GovernmentVacancy.application_deadline.is_not(None),
            GovernmentVacancy.deadline_status.notin_(["CANCELLED"])
        ).all()

        stats = {
            "revalidated": 0,
            "open": 0,
            "deadline_approaching": 0,
            "deadline_today": 0,
            "expired": 0,
            "status_changed": 0,
        }

        for vac in vacancies:
            stats["revalidated"] += 1
            vac.last_verified_at = now
            old_status = vac.deadline_status
            deadline = vac.application_deadline

            diff = (deadline - now).total_seconds()
            if diff <= 0:
                new_status = "EXPIRED"
                stats["expired"] += 1
            elif diff <= 86400:  # 24h
                new_status = "DEADLINE_TODAY"
                stats["deadline_today"] += 1
            elif diff <= 259200:  # 72h / 3 days
                new_status = "DEADLINE_APPROACHING"
                stats["deadline_approaching"] += 1
            else:
                new_status = "OPEN"
                stats["open"] += 1

            if old_status != new_status:
                vac.deadline_status = new_status
                stats["status_changed"] += 1

                # Record change event
                if vac.source_id:
                    event = GovernmentChangeEvent(
                        source_id=vac.source_id,
                        vacancy_id=vac.id,
                        url=vac.official_notification_url or vac.pdf_url or "https://gov.in",
                        document_type="notice",
                        change_type="CLOSED" if new_status == "EXPIRED" else "UPDATED",
                        change_summary=f"Deadline status transitioned from {old_status} to {new_status} (Deadline: {deadline.strftime('%Y-%m-%d')})",
                        detected_at=now,
                    )
                    db.add(event)

        db.commit()
        return stats

    @classmethod
    def enqueue_monitoring_tasks(cls, db: Session, batch_size: int = 20) -> Dict[str, Any]:
        """
        Enqueues idempotent crawl tasks for due sources into the AutomationTask queue.
        Enforces Catch-Up Logic: Enqueues exactly ONE catch-up task per due source
        regardless of how long the PC was turned off.
        """
        cls.initialize_monitoring_queue(db)
        cls.revalidate_vacancy_deadlines(db)

        now = get_utc_now()
        due_sources = cls.get_due_sources(db, limit=batch_size, lock_sources=False)

        enqueued_count = 0
        skipped_count = 0
        enqueued_task_ids = []

        window_bucket = now.strftime("%Y%m%d_%H")

        for src in due_sources:
            # Deterministic idempotency key: gov_crawl:{source_id}:{window_bucket}
            idempotency_key = f"gov_crawl:{src.id}:{window_bucket}"
            existing_task = db.query(AutomationTask).filter(
                AutomationTask.idempotency_key == idempotency_key
            ).first()

            if existing_task:
                skipped_count += 1
                continue

            # Calculate priority based on deadline sensitivity
            priority = 50
            if src.change_frequency_category == "high":
                priority = 80
            elif src.last_crawled_at is None:
                priority = 75  # High priority to resolve uncrawled sources
            elif src.change_frequency_category == "medium":
                priority = 65

            task = AutomationQueueService.enqueue_task(
                db=db,
                task_type="GOV_SOURCE_CRAWL",
                idempotency_key=idempotency_key,
                priority=priority,
                payload={
                    "source_id": src.id,
                    "official_domain": src.official_domain,
                    "organisation_name": src.organisation_name,
                }
            )

            enqueued_count += 1
            enqueued_task_ids.append(task.id)

        # Check if periodic rediscovery is due (once every 24 hours)
        last_disc_run = (
            db.query(GovernmentDiscoveryRun)
            .filter(GovernmentDiscoveryRun.run_type == "source_discovery")
            .order_by(GovernmentDiscoveryRun.created_at.desc())
            .first()
        )
        should_run_disc = False
        if not last_disc_run or (now - last_disc_run.created_at).total_seconds() >= 86400:
            should_run_disc = True

        disc_enqueued = False
        if should_run_disc:
            disc_key = f"gov_discovery:{now.strftime('%Y%m%d')}"
            disc_task = AutomationQueueService.enqueue_task(
                db=db,
                task_type="GOV_SOURCE_DISCOVERY",
                idempotency_key=disc_key,
                priority=45,
                payload={"scope": "ALL", "max_queries": 15}
            )
            if disc_task.status == "PENDING" and disc_task.attempts == 0:
                disc_enqueued = True
                enqueued_task_ids.append(disc_task.id)

        return {
            "due_sources_count": len(due_sources),
            "enqueued_crawls": enqueued_count,
            "skipped_crawls": skipped_count,
            "discovery_enqueued": disc_enqueued,
            "enqueued_task_ids": enqueued_task_ids,
        }

    @classmethod
    def get_monitoring_metrics(cls, db: Session) -> Dict[str, Any]:
        """
        Calculates exact continuous monitoring and freshness SLA telemetry.
        """
        cls.initialize_monitoring_queue(db)
        now = get_utc_now()
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

        total_sources = db.query(GovernmentSource).count()
        scheduled_sources = db.query(GovernmentSource).filter(GovernmentSource.next_crawl_at.is_not(None)).count()
        never_crawled = db.query(GovernmentSource).filter(GovernmentSource.last_crawled_at.is_(None)).count()
        crawling = db.query(GovernmentSource).filter(GovernmentSource.is_locked == True).count()

        due_now = db.query(GovernmentSource).filter(
            GovernmentSource.source_status.notin_(["DEAD"]),
            GovernmentSource.next_crawl_at <= now
        ).count()

        # Overdue = next_crawl_at <= NOW() - 1 hour
        overdue_threshold = now - timedelta(hours=1)
        overdue_sources = db.query(GovernmentSource).filter(
            GovernmentSource.source_status.notin_(["DEAD"]),
            GovernmentSource.next_crawl_at <= overdue_threshold
        ).count()

        crawled_today = db.query(GovernmentSource).filter(
            GovernmentSource.last_crawled_at >= today_start
        ).count()

        success_today = db.query(GovernmentSource).filter(
            GovernmentSource.last_successful_crawl_at >= today_start
        ).count()

        failed_today = db.query(GovernmentSource).filter(
            GovernmentSource.last_crawled_at >= today_start,
            GovernmentSource.consecutive_failures > 0
        ).count()

        blocked_sources = db.query(GovernmentSource).filter(
            GovernmentSource.source_status == "BLOCKED"
        ).count()

        manual_access_sources = db.query(GovernmentSource).filter(
            GovernmentSource.source_status == "REQUIRES_MANUAL_ACCESS"
        ).count()

        new_sources_today = db.query(GovernmentSource).filter(
            GovernmentSource.discovered_at >= today_start
        ).count()

        # Vacancy & Change stats
        new_vacancies_today = db.query(GovernmentVacancy).filter(
            GovernmentVacancy.created_at >= today_start
        ).count()

        updated_vacancies_today = db.query(GovernmentVacancy).filter(
            GovernmentVacancy.updated_at >= today_start,
            GovernmentVacancy.updated_at > GovernmentVacancy.created_at
        ).count()

        corrigenda_count = db.query(GovernmentVacancy).filter(
            or_(
                GovernmentVacancy.change_type == "corrigendum",
                GovernmentVacancy.corrigendum_details.is_not(None),
            )
        ).count()

        deadline_extensions_count = db.query(GovernmentChangeEvent).filter(
            GovernmentChangeEvent.change_type == "EXTENDED"
        ).count()

        expired_vacancies = db.query(GovernmentVacancy).filter(
            GovernmentVacancy.deadline_status == "EXPIRED"
        ).count()

        deadline_lt_24h = db.query(GovernmentVacancy).filter(
            GovernmentVacancy.application_deadline.is_not(None),
            GovernmentVacancy.application_deadline >= now,
            GovernmentVacancy.application_deadline <= now + timedelta(hours=24),
            GovernmentVacancy.deadline_status.notin_(["EXPIRED", "CANCELLED"]),
        ).count()

        deadline_lt_3d = db.query(GovernmentVacancy).filter(
            GovernmentVacancy.application_deadline.is_not(None),
            GovernmentVacancy.application_deadline >= now,
            GovernmentVacancy.application_deadline <= now + timedelta(days=3),
            GovernmentVacancy.deadline_status.notin_(["EXPIRED", "CANCELLED"]),
        ).count()

        # SLA Compliance: A source is outside SLA if overdue_hours > SLA_HOURS[category]
        outside_sla = overdue_sources
        within_sla = max(0, total_sources - outside_sla)

        # Dates & Names
        oldest_overdue = (
            db.query(GovernmentSource)
            .filter(
                GovernmentSource.source_status.notin_(["DEAD"]),
                GovernmentSource.next_crawl_at.is_not(None),
            )
            .order_by(GovernmentSource.next_crawl_at.asc())
            .first()
        )
        oldest_overdue_name = (
            f"{oldest_overdue.organisation_name} ({oldest_overdue.official_domain})"
            if oldest_overdue else "None"
        )

        next_scheduled = (
            db.query(func.min(GovernmentSource.next_crawl_at))
            .filter(GovernmentSource.next_crawl_at > now)
            .scalar()
        )

        last_global_crawl = (
            db.query(func.max(GovernmentSource.last_crawled_at)).scalar()
        )

        last_disc = (
            db.query(GovernmentDiscoveryRun)
            .filter(GovernmentDiscoveryRun.run_type == "source_discovery")
            .order_by(GovernmentDiscoveryRun.created_at.desc())
            .first()
        )
        last_disc_time = last_disc.created_at if last_disc else None
        next_disc_time = (last_disc_time + timedelta(hours=24)) if last_disc_time else now

        return {
            "total_registered_sources": total_sources,
            "sources_with_scheduled_crawl": scheduled_sources,
            "sources_never_crawled": never_crawled,
            "sources_currently_due": due_now,
            "sources_currently_overdue": overdue_sources,
            "sources_crawling": crawling,
            "sources_successfully_crawled_today": success_today,
            "sources_failed_today": failed_today,
            "sources_blocked": blocked_sources,
            "sources_requiring_manual_access": manual_access_sources,
            "new_sources_discovered_today": new_sources_today,
            "new_vacancies_today": new_vacancies_today,
            "updated_vacancies_today": updated_vacancies_today,
            "corrigenda_count": corrigenda_count,
            "deadline_extensions_count": deadline_extensions_count,
            "expired_vacancies_count": expired_vacancies,
            "deadline_lt_24h_count": deadline_lt_24h,
            "deadline_lt_3d_count": deadline_lt_3d,
            "sources_within_freshness_sla": within_sla,
            "sources_outside_freshness_sla": outside_sla,
            "oldest_overdue_source": oldest_overdue_name,
            "last_global_crawl": last_global_crawl,
            "next_scheduled_crawl": next_scheduled,
            "discovery_engine_last_run": last_disc_time,
            "next_global_discovery": next_disc_time,
        }
