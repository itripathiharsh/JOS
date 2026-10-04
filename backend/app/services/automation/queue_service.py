import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.automation import AutomationTask

logger = logging.getLogger(__name__)


def get_utc_now():
    return datetime.now(timezone.utc)


class AutomationQueueService:
    """
    Durable, PostgreSQL-backed asynchronous task queue.
    Features:
    - Atomic task claiming using SELECT ... FOR UPDATE SKIP LOCKED
    - Lease-based crash recovery for orphaned tasks
    - Deterministic uniqueness and idempotency key checks
    - Bounded exponential backoff retries for transient errors
    - Hard blocking for non-transient / human-intervention barriers
    """

    @classmethod
    def enqueue_task(
        cls,
        db: Session,
        task_type: str,
        idempotency_key: str,
        candidate_id: Optional[str] = None,
        application_id: Optional[str] = None,
        job_id: Optional[str] = None,
        priority: int = 50,
        payload: Optional[Dict[str, Any]] = None,
        delay_seconds: int = 0,
        max_attempts: int = 3,
    ) -> AutomationTask:
        """
        Enqueues an automation task with strict idempotency protection.
        If a task with the given idempotency_key already exists, returns the existing record.
        """
        existing = db.query(AutomationTask).filter(
            AutomationTask.idempotency_key == idempotency_key
        ).first()

        if existing:
            # If existing task has already succeeded or is currently queued/running, reuse it
            if existing.status in ("SUCCEEDED", "RUNNING", "PENDING", "RETRY_WAIT"):
                return existing
            # If existing task failed and max attempts exhausted, caller must decide or we return it
            return existing

        now = get_utc_now()
        available_at = now + timedelta(seconds=delay_seconds) if delay_seconds > 0 else now

        task = AutomationTask(
            task_type=task_type,
            candidate_id=candidate_id,
            application_id=application_id,
            job_id=job_id,
            status="PENDING",
            priority=priority,
            attempts=0,
            max_attempts=max_attempts,
            available_at=available_at,
            idempotency_key=idempotency_key,
            payload=payload or {},
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info(f"Enqueued automation task {task.id} (type={task_type}, key={idempotency_key})")
        return task

    @classmethod
    def claim_next_task(
        cls,
        db: Session,
        worker_id: str,
        lease_seconds: int = 300,
    ) -> Optional[AutomationTask]:
        """
        Atomically claims the next highest-priority available task.
        Uses PostgreSQL SELECT ... FOR UPDATE SKIP LOCKED to ensure zero concurrency conflicts.
        """
        now = get_utc_now()
        lease_cutoff = now - timedelta(seconds=lease_seconds)

        # Claim tasks in PENDING or RETRY_WAIT that are available
        query = (
            db.query(AutomationTask)
            .filter(
                AutomationTask.status.in_(["PENDING", "RETRY_WAIT"]),
                AutomationTask.available_at <= now,
                or_(
                    AutomationTask.locked_at.is_(None),
                    AutomationTask.locked_at < lease_cutoff,
                ),
            )
            .order_by(AutomationTask.priority.desc(), AutomationTask.available_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        task = query.first()
        if not task:
            return None

        task.status = "RUNNING"
        task.locked_at = now
        task.locked_by = worker_id
        task.started_at = now
        task.attempts += 1
        db.commit()
        db.refresh(task)
        logger.info(f"Worker {worker_id} claimed task {task.id} (type={task.task_type}, attempt={task.attempts}/{task.max_attempts})")
        return task

    @classmethod
    def complete_task(
        cls,
        db: Session,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> AutomationTask:
        """Marks a task as successfully completed."""
        task = db.query(AutomationTask).filter(AutomationTask.id == task_id).first()
        if not task:
            raise ValueError(f"AutomationTask {task_id} not found.")

        task.status = "SUCCEEDED"
        task.completed_at = get_utc_now()
        task.locked_at = None
        task.locked_by = None
        task.result = result or {}
        task.last_error = None
        db.commit()
        db.refresh(task)
        logger.info(f"Task {task_id} marked as SUCCEEDED.")
        return task

    @classmethod
    def fail_task(
        cls,
        db: Session,
        task_id: str,
        error_msg: str,
        is_transient: bool = False,
        error_category: Optional[str] = None,
    ) -> AutomationTask:
        """
        Records task failure. If transient and attempts < max_attempts, schedules a retry.
        Otherwise marks FAILED.
        """
        task = db.query(AutomationTask).filter(AutomationTask.id == task_id).first()
        if not task:
            raise ValueError(f"AutomationTask {task_id} not found.")

        now = get_utc_now()
        task.last_error = error_msg

        if is_transient and task.attempts < task.max_attempts:
            # Exponential backoff: 30s * 2^(attempts-1) -> 30s, 60s, 120s
            backoff_seconds = 30 * (2 ** (task.attempts - 1))
            task.status = "RETRY_WAIT"
            task.available_at = now + timedelta(seconds=backoff_seconds)
            task.locked_at = None
            task.locked_by = None
            task.error_category = "TRANSIENT"
            logger.warning(
                f"Task {task_id} transient failure (attempt {task.attempts}/{task.max_attempts}). "
                f"Retrying in {backoff_seconds}s. Error: {error_msg}"
            )
        else:
            task.status = "FAILED"
            task.completed_at = now
            task.locked_at = None
            task.locked_by = None
            task.error_category = error_category or ("TRANSIENT_EXHAUSTED" if is_transient else "NON_TRANSIENT")
            logger.error(f"Task {task_id} marked as FAILED ({task.error_category}): {error_msg}")

        db.commit()
        db.refresh(task)
        return task

    @classmethod
    def block_task(
        cls,
        db: Session,
        task_id: str,
        reason: str,
        error_category: str = "BLOCKED",
    ) -> AutomationTask:
        """
        Halts a task in BLOCKED state requiring human intervention (e.g. CAPTCHA, login, missing approval).
        Does NOT automatically retry.
        """
        task = db.query(AutomationTask).filter(AutomationTask.id == task_id).first()
        if not task:
            raise ValueError(f"AutomationTask {task_id} not found.")

        task.status = "BLOCKED"
        task.completed_at = get_utc_now()
        task.locked_at = None
        task.locked_by = None
        task.last_error = reason
        task.error_category = error_category
        db.commit()
        db.refresh(task)
        logger.warning(f"Task {task_id} BLOCKED: {reason}")
        return task

    @classmethod
    def recover_stuck_tasks(
        cls,
        db: Session,
        lease_seconds: int = 300,
    ) -> int:
        """
        Recovers tasks stuck in RUNNING state where worker lease expired (e.g., worker died/crashed).
        If attempts < max_attempts, resets to RETRY_WAIT for another worker to claim.
        Otherwise marks FAILED.
        """
        now = get_utc_now()
        lease_cutoff = now - timedelta(seconds=lease_seconds)

        stuck_tasks = (
            db.query(AutomationTask)
            .filter(
                AutomationTask.status == "RUNNING",
                AutomationTask.locked_at < lease_cutoff,
            )
            .all()
        )

        recovered_count = 0
        for task in stuck_tasks:
            if task.attempts < task.max_attempts:
                task.status = "RETRY_WAIT"
                task.available_at = now
                task.locked_at = None
                task.locked_by = None
                task.last_error = f"Recovered from dead worker lease (previous lock: {task.locked_at})"
                task.error_category = "LEASE_RECOVERED"
            else:
                task.status = "FAILED"
                task.completed_at = now
                task.locked_at = None
                task.locked_by = None
                task.last_error = "Task failed: worker lease timed out and max attempts reached"
                task.error_category = "LEASE_EXHAUSTED"
            recovered_count += 1

        if recovered_count > 0:
            db.commit()
            logger.info(f"Recovered {recovered_count} stuck tasks whose worker lease timed out.")

        return recovered_count

    @classmethod
    def cancel_task(
        cls,
        db: Session,
        task_id: str,
        reason: str = "User cancelled",
    ) -> AutomationTask:
        """Cancels an uncompleted task."""
        task = db.query(AutomationTask).filter(AutomationTask.id == task_id).first()
        if not task:
            raise ValueError(f"AutomationTask {task_id} not found.")

        if task.status in ("SUCCEEDED", "CANCELLED"):
            return task

        task.status = "CANCELLED"
        task.completed_at = get_utc_now()
        task.locked_at = None
        task.locked_by = None
        task.last_error = reason
        db.commit()
        db.refresh(task)
        logger.info(f"Task {task_id} CANCELLED: {reason}")
        return task
