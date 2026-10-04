import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.automation import AutomationSettings, AutomationTask
from app.models.profile import CandidateProfile
from app.models.job import Job
from app.models.discovery import DiscoveryRun
from app.models.matching import MatchResult
from app.models.decision import ApplicationDecision
from app.models.preparation import ApplicationPreparation
from app.models.application import Application

from app.services.automation.queue_service import AutomationQueueService
from app.schemas.automation import SchedulerTickResult

logger = logging.getLogger(__name__)


def get_utc_now():
    return datetime.now(timezone.utc)


class AutomationSchedulerService:
    """
    Step 12: Local, zero-cost task scheduler.
    Enqueues tasks into the PostgreSQL queue based on deterministic schedules and candidate settings.
    Does NOT execute tasks directly; relies on the AutomationWorkerService.
    Prevents duplicate scheduling via deterministic idempotency keys and bounded batches.
    """

    @classmethod
    def get_or_create_settings(
        cls,
        db: Session,
        candidate_id: str,
    ) -> AutomationSettings:
        """Retrieves or initializes default automation policy for a candidate."""
        settings = (
            db.query(AutomationSettings)
            .filter(AutomationSettings.candidate_id == candidate_id)
            .first()
        )
        if not settings:
            settings = AutomationSettings(
                candidate_id=candidate_id,
                mode="ASSISTED",
                job_discovery_enabled=True,
                matching_enabled=True,
                deduplication_enabled=True,
                preparation_enabled=True,
                submission_requires_approval=True,
                discovery_interval_hours=6,
                max_daily_preparations=20,
                stale_job_threshold_days=30,
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @classmethod
    def run_scheduler_tick(
        cls,
        db: Session,
        candidate_id: Optional[str] = None,
    ) -> SchedulerTickResult:
        """
        Executes a single scheduler cycle:
        1. Checks automation policy and mode.
        2. Evaluates discovery intervals.
        3. Enqueues matching for newly ingested canonical jobs.
        4. Enqueues preparation for jobs with APPLY decision.
        5. Enqueues daily maintenance (follow-up checks, staleness checks).
        """
        # Resolve candidate
        if not candidate_id:
            cand = db.query(CandidateProfile).order_by(CandidateProfile.updated_at.desc()).first()
            if not cand:
                return SchedulerTickResult(enqueued_count=0, skipped_count=0)
            candidate_id = cand.id

        settings = cls.get_or_create_settings(db, candidate_id)

        # In MANUAL mode, automation never triggers background tasks
        if settings.mode == "MANUAL":
            logger.info("Scheduler: Candidate is in MANUAL mode. Skipping automated task generation.")
            return SchedulerTickResult(enqueued_count=0, skipped_count=0)

        enqueued_ids: List[str] = []
        enqueued_types: List[str] = []
        skipped_count = 0
        now = get_utc_now()

        # 1. Job Discovery Scheduling
        if settings.job_discovery_enabled:
            last_run = (
                db.query(DiscoveryRun)
                .filter(DiscoveryRun.candidate_id == candidate_id)
                .order_by(DiscoveryRun.created_at.desc())
                .first()
            )
            should_run_discovery = False
            if not last_run:
                should_run_discovery = True
            else:
                elapsed = now - last_run.created_at
                if elapsed >= timedelta(hours=settings.discovery_interval_hours):
                    should_run_discovery = True

            if should_run_discovery:
                # Interval window key
                window_key = now.strftime("%Y%m%d_%H")
                idempotency_key = f"discovery:{candidate_id}:{window_key}"
                task = AutomationQueueService.enqueue_task(
                    db=db,
                    task_type="DISCOVERY",
                    idempotency_key=idempotency_key,
                    candidate_id=candidate_id,
                    priority=40,
                )
                if task.status == "PENDING" and task.attempts == 0:
                    enqueued_ids.append(task.id)
                    enqueued_types.append("DISCOVERY")
                else:
                    skipped_count += 1

        # 2. Matching Automation (Bounded to top 10 un-evaluated canonical jobs)
        if settings.matching_enabled:
            # Canonical jobs missing MatchResult
            unmatched_jobs = (
                db.query(Job)
                .outerjoin(
                    MatchResult,
                    (MatchResult.job_id == Job.id) & (MatchResult.candidate_id == candidate_id),
                )
                .filter(
                    Job.is_canonical == True,
                    MatchResult.id.is_(None),
                )
                .order_by(Job.created_at.desc())
                .limit(10)
                .all()
            )

            for job in unmatched_jobs:
                updated_stamp = job.updated_at.isoformat() if job.updated_at else "init"
                idempotency_key = f"match:{candidate_id}:{job.id}:{updated_stamp}"
                task = AutomationQueueService.enqueue_task(
                    db=db,
                    task_type="MATCHING",
                    idempotency_key=idempotency_key,
                    candidate_id=candidate_id,
                    job_id=job.id,
                    priority=60,
                )
                if task.status == "PENDING" and task.attempts == 0:
                    enqueued_ids.append(task.id)
                    if "MATCHING" not in enqueued_types:
                        enqueued_types.append("MATCHING")
                else:
                    skipped_count += 1

        # 3. Preparation Automation (Bounded to top 5 jobs with APPLY decision missing preparation)
        if settings.preparation_enabled:
            apply_jobs_without_prep = (
                db.query(Job.id, ApplicationDecision.updated_at)
                .join(ApplicationDecision, ApplicationDecision.job_id == Job.id)
                .outerjoin(
                    ApplicationPreparation,
                    (ApplicationPreparation.job_id == Job.id) & (ApplicationPreparation.candidate_id == candidate_id),
                )
                .filter(
                    Job.is_canonical == True,
                    ApplicationDecision.candidate_id == candidate_id,
                    ApplicationDecision.decision == "APPLY",
                    ApplicationPreparation.id.is_(None),
                )
                .order_by(ApplicationDecision.updated_at.desc())
                .limit(5)
                .all()
            )

            for job_id, dec_updated_at in apply_jobs_without_prep:
                dec_stamp = dec_updated_at.isoformat() if dec_updated_at else "init"
                idempotency_key = f"prep:{candidate_id}:{job_id}:{dec_stamp}"
                task = AutomationQueueService.enqueue_task(
                    db=db,
                    task_type="PREPARATION",
                    idempotency_key=idempotency_key,
                    candidate_id=candidate_id,
                    job_id=job_id,
                    priority=70,
                )
                if task.status == "PENDING" and task.attempts == 0:
                    enqueued_ids.append(task.id)
                    if "PREPARATION" not in enqueued_types:
                        enqueued_types.append("PREPARATION")
                else:
                    skipped_count += 1

        # 4. Daily Maintenance: Follow-up check & Stale check
        day_key = now.strftime("%Y%m%d")
        followup_key = f"followup:{candidate_id}:{day_key}"
        task_f = AutomationQueueService.enqueue_task(
            db=db,
            task_type="FOLLOWUP_CHECK",
            idempotency_key=followup_key,
            candidate_id=candidate_id,
            priority=20,
        )
        if task_f.status == "PENDING" and task_f.attempts == 0:
            enqueued_ids.append(task_f.id)
            if "FOLLOWUP_CHECK" not in enqueued_types:
                enqueued_types.append("FOLLOWUP_CHECK")

        stale_key = f"stale_check:{candidate_id}:{day_key}"
        task_s = AutomationQueueService.enqueue_task(
            db=db,
            task_type="STALE_CHECK",
            idempotency_key=stale_key,
            candidate_id=candidate_id,
            priority=20,
        )
        if task_s.status == "PENDING" and task_s.attempts == 0:
            enqueued_ids.append(task_s.id)
            if "STALE_CHECK" not in enqueued_types:
                enqueued_types.append("STALE_CHECK")

        return SchedulerTickResult(
            enqueued_count=len(enqueued_ids),
            skipped_count=skipped_count,
            task_types_enqueued=enqueued_types,
            enqueued_task_ids=enqueued_ids,
        )
