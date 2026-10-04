import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.automation import AutomationTask, AutomationSettings, ApplicationApproval
from app.models.profile import CandidateProfile
from app.schemas.automation import (
    AutomationSettingsResponse,
    AutomationSettingsUpdateRequest,
    AutomationTaskResponse,
    AutomationTaskListResponse,
    AutomationStatusResponse,
    ApplicationApprovalResponse,
    ApplicationApprovalCreateRequest,
    WorkerTickResult,
    SchedulerTickResult,
)
from app.services.automation.queue_service import AutomationQueueService
from app.services.automation.approval_service import ApplicationApprovalService
from app.services.automation.worker_service import AutomationWorkerService
from app.services.automation.scheduler_service import AutomationSchedulerService

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_candidate_id(db: Session, candidate_id: Optional[str] = None) -> str:
    if candidate_id:
        return candidate_id
    cand = db.query(CandidateProfile).order_by(CandidateProfile.updated_at.desc()).first()
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidate profile found. Please create a profile first.",
        )
    return cand.id


@router.get("/automation/status", response_model=AutomationStatusResponse)
def get_automation_status(
    candidate_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Step 12: Retrieves real-time automation telemetry, queue metrics, and operational mode.
    """
    cand_id = _get_candidate_id(db, candidate_id)
    settings_rec = AutomationSchedulerService.get_or_create_settings(db, cand_id)

    pending_count = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == "PENDING").scalar() or 0
    running_count = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == "RUNNING").scalar() or 0
    failed_count = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == "FAILED").scalar() or 0
    blocked_count = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == "BLOCKED").scalar() or 0
    succeeded_count = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == "SUCCEEDED").scalar() or 0

    last_success = (
        db.query(AutomationTask.completed_at)
        .filter(AutomationTask.status == "SUCCEEDED")
        .order_by(AutomationTask.completed_at.desc())
        .first()
    )

    return AutomationStatusResponse(
        mode=settings_rec.mode,
        is_active=settings_rec.mode != "MANUAL",
        scheduler_enabled=settings_rec.mode != "MANUAL",
        worker_enabled=True,
        pending_tasks=pending_count,
        running_tasks=running_count,
        failed_tasks=failed_count,
        blocked_tasks=blocked_count,
        succeeded_tasks=succeeded_count,
        last_successful_run=last_success[0] if last_success else None,
        next_scheduled_run=None,
        settings=AutomationSettingsResponse.model_validate(settings_rec),
    )


@router.get("/automation/settings", response_model=AutomationSettingsResponse)
def get_automation_settings(
    candidate_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieves current candidate automation policy."""
    cand_id = _get_candidate_id(db, candidate_id)
    settings_rec = AutomationSchedulerService.get_or_create_settings(db, cand_id)
    return AutomationSettingsResponse.model_validate(settings_rec)


@router.put("/automation/settings", response_model=AutomationSettingsResponse)
def update_automation_settings(
    payload: AutomationSettingsUpdateRequest,
    candidate_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Updates candidate automation policy.
    Submission approval requirement remains strictly TRUE for real external submissions.
    """
    cand_id = _get_candidate_id(db, candidate_id)
    settings_rec = AutomationSchedulerService.get_or_create_settings(db, cand_id)

    if payload.mode:
        if payload.mode not in ("MANUAL", "ASSISTED", "CONTROLLED_AUTO"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid automation mode '{payload.mode}'. Supported modes: MANUAL, ASSISTED, CONTROLLED_AUTO",
            )
        settings_rec.mode = payload.mode

    if payload.job_discovery_enabled is not None:
        settings_rec.job_discovery_enabled = payload.job_discovery_enabled
    if payload.matching_enabled is not None:
        settings_rec.matching_enabled = payload.matching_enabled
    if payload.deduplication_enabled is not None:
        settings_rec.deduplication_enabled = payload.deduplication_enabled
    if payload.preparation_enabled is not None:
        settings_rec.preparation_enabled = payload.preparation_enabled
    if payload.discovery_interval_hours is not None:
        settings_rec.discovery_interval_hours = payload.discovery_interval_hours
    if payload.max_daily_preparations is not None:
        settings_rec.max_daily_preparations = payload.max_daily_preparations
    if payload.stale_job_threshold_days is not None:
        settings_rec.stale_job_threshold_days = payload.stale_job_threshold_days

    db.commit()
    db.refresh(settings_rec)
    return AutomationSettingsResponse.model_validate(settings_rec)


@router.get("/automation/tasks", response_model=AutomationTaskListResponse)
def list_automation_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    task_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lists automation tasks from the durable PostgreSQL queue."""
    query = db.query(AutomationTask)
    if status_filter:
        query = query.filter(AutomationTask.status == status_filter)
    if task_type:
        query = query.filter(AutomationTask.task_type == task_type)

    total = query.count()
    tasks = query.order_by(AutomationTask.created_at.desc()).offset(skip).limit(limit).all()

    return AutomationTaskListResponse(
        items=[AutomationTaskResponse.model_validate(t) for t in tasks],
        total=total,
    )


@router.post("/automation/tasks/{task_id}/retry", response_model=AutomationTaskResponse)
def retry_automation_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    """Resets a FAILED or BLOCKED task back to PENDING for re-execution."""
    task = db.query(AutomationTask).filter(AutomationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "PENDING"
    task.attempts = 0
    task.last_error = None
    task.locked_at = None
    task.locked_by = None
    db.commit()
    db.refresh(task)
    return AutomationTaskResponse.model_validate(task)


@router.post("/automation/tasks/{task_id}/cancel", response_model=AutomationTaskResponse)
def cancel_automation_task(
    task_id: str,
    reason: Optional[str] = Query("Cancelled by user"),
    db: Session = Depends(get_db),
):
    """Cancels an uncompleted task."""
    try:
        task = AutomationQueueService.cancel_task(db, task_id, reason=reason)
        return AutomationTaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/automation/worker/tick", response_model=WorkerTickResult)
def trigger_worker_tick(
    worker_id: Optional[str] = Query(None),
    max_tasks: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Executes a single controlled worker execution cycle.
    Recovers orphaned leases and processes claimed queue tasks.
    """
    return AutomationWorkerService.run_worker_tick(db, worker_id=worker_id, max_tasks=max_tasks)


@router.post("/automation/scheduler/tick", response_model=SchedulerTickResult)
def trigger_scheduler_tick(
    candidate_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Executes a single scheduler cycle: generates background tasks based on intervals and policies.
    """
    cand_id = _get_candidate_id(db, candidate_id)
    return AutomationSchedulerService.run_scheduler_tick(db, candidate_id=cand_id)


# --- Step 12: Human-in-the-Loop Submission Approval Gate Endpoints ---

@router.post("/applications/{application_id}/approve", response_model=ApplicationApprovalResponse)
def approve_application_submission(
    application_id: str,
    payload: Optional[ApplicationApprovalCreateRequest] = None,
    candidate_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Step 12: Explicitly grants human approval to submit an application package.
    Strictly binds approval to the current preparation version.
    """
    cand_id = _get_candidate_id(db, candidate_id)
    req_data = payload or ApplicationApprovalCreateRequest()
    try:
        approval = ApplicationApprovalService.grant_approval(
            db=db,
            application_id=application_id,
            candidate_id=cand_id,
            scope=req_data.scope,
            expires_hours=req_data.expires_hours,
            notes=req_data.notes,
        )
        return ApplicationApprovalResponse.model_validate(approval)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/applications/{application_id}/revoke-approval", response_model=Optional[ApplicationApprovalResponse])
def revoke_application_submission_approval(
    application_id: str,
    reason: Optional[str] = Query("Revoked by candidate"),
    db: Session = Depends(get_db),
):
    """Revokes active human submission approval for an application."""
    approval = ApplicationApprovalService.revoke_approval(db, application_id, reason=reason)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active approval found for application '{application_id}'.",
        )
    return ApplicationApprovalResponse.model_validate(approval)


@router.get("/applications/{application_id}/approval", response_model=Optional[ApplicationApprovalResponse])
def get_application_submission_approval(
    application_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves the latest human submission approval status for an application."""
    approval = (
        db.query(ApplicationApproval)
        .filter(ApplicationApproval.application_id == application_id)
        .order_by(ApplicationApproval.created_at.desc())
        .first()
    )
    if not approval:
        return None
    return ApplicationApprovalResponse.model_validate(approval)
