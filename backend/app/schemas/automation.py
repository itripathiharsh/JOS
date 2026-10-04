from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AutomationSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str
    mode: str = Field(..., description="MANUAL, ASSISTED, CONTROLLED_AUTO")
    job_discovery_enabled: bool
    matching_enabled: bool
    deduplication_enabled: bool
    preparation_enabled: bool
    submission_requires_approval: bool
    discovery_interval_hours: int
    max_daily_preparations: int
    stale_job_threshold_days: int
    created_at: datetime
    updated_at: datetime


class AutomationSettingsUpdateRequest(BaseModel):
    mode: Optional[str] = Field(None, description="MANUAL, ASSISTED, CONTROLLED_AUTO")
    job_discovery_enabled: Optional[bool] = None
    matching_enabled: Optional[bool] = None
    deduplication_enabled: Optional[bool] = None
    preparation_enabled: Optional[bool] = None
    discovery_interval_hours: Optional[int] = Field(None, ge=1, le=72)
    max_daily_preparations: Optional[int] = Field(None, ge=1, le=100)
    stale_job_threshold_days: Optional[int] = Field(None, ge=1, le=365)


class AutomationTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_type: str
    candidate_id: Optional[str] = None
    application_id: Optional[str] = None
    job_id: Optional[str] = None
    status: str
    priority: int
    attempts: int
    max_attempts: int
    available_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    last_error: Optional[str] = None
    error_category: Optional[str] = None
    idempotency_key: str
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class AutomationTaskListResponse(BaseModel):
    items: List[AutomationTaskResponse]
    total: int


class ApplicationApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    job_id: str
    candidate_id: str
    preparation_id: Optional[str] = None
    preparation_version: int
    approved_by: str
    approved_at: datetime
    approval_scope: str
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    approval_status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ApplicationApprovalCreateRequest(BaseModel):
    scope: str = Field("SINGLE_SUBMISSION", description="SINGLE_SUBMISSION or TEMPORARY_SESSION")
    expires_hours: int = Field(48, ge=1, le=168, description="Hours until approval expires")
    notes: Optional[str] = None


class AutomationStatusResponse(BaseModel):
    mode: str
    is_active: bool
    scheduler_enabled: bool
    worker_enabled: bool
    pending_tasks: int
    running_tasks: int
    failed_tasks: int
    blocked_tasks: int
    succeeded_tasks: int
    last_successful_run: Optional[datetime] = None
    next_scheduled_run: Optional[datetime] = None
    settings: AutomationSettingsResponse


class WorkerTickResult(BaseModel):
    worker_id: str
    claimed_count: int
    succeeded_count: int
    failed_count: int
    blocked_count: int
    recovered_count: int
    task_ids: List[str] = []


class SchedulerTickResult(BaseModel):
    enqueued_count: int
    skipped_count: int
    task_types_enqueued: List[str] = []
    enqueued_task_ids: List[str] = []
