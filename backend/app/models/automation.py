import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class AutomationTask(Base):
    """
    Step 12: Durable, PostgreSQL-backed asynchronous automation task queue.
    Supports atomic task claiming (SELECT ... FOR UPDATE SKIP LOCKED),
    idempotent deduplication, lease-based worker recovery, and bounded retries.
    """
    __tablename__ = "automation_tasks"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_automation_task_idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Task Type: DISCOVERY, MATCHING, DECISION, PREPARATION, FOLLOWUP_CHECK, STALE_CHECK, EXECUTION
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    candidate_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    application_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=True, index=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True)

    # Status: PENDING, RUNNING, SUCCEEDED, FAILED, RETRY_WAIT, CANCELLED, BLOCKED
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    
    # Priority: higher integer = higher claim priority (e.g., 100 for high, 50 for normal, 10 for background)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False, index=True)
    
    # Retry & Lease tracking
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Worker lease lock
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Error classification
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True) # TRANSIENT, NON_TRANSIENT, BLOCKED, SECURITY
    
    # Deterministic uniqueness key
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Payload & Result metadata
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)


class ApplicationApproval(Base):
    """
    Step 12: Explicit Human Approval Gate for Application Submission.
    Prevents background automation from submitting applications without explicit candidate consent.
    Approval is strictly bound to the exact preparation version and expires automatically if
    candidate profile, job description, or preparation package is modified.
    """
    __tablename__ = "application_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    preparation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("application_preparations.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Preparation Version bound to this approval
    preparation_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    approved_by: Mapped[str] = mapped_column(String(100), default="candidate")
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    approval_scope: Mapped[str] = mapped_column(String(50), default="SINGLE_SUBMISSION") # SINGLE_SUBMISSION, TEMPORARY_SESSION
    
    # Expiration and Revocation
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Approval Status: PENDING, APPROVED, REVOKED, EXPIRED, NOT_REQUIRED
    approval_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    application: Mapped["Application"] = relationship("Application")
    job: Mapped["Job"] = relationship("Job")
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile")
    preparation: Mapped[Optional["ApplicationPreparation"]] = relationship("ApplicationPreparation")


class AutomationSettings(Base):
    """
    Step 12: Controlled Autonomy Policy and Configuration per Candidate.
    Enforces safe defaults (submission_requires_approval=True, assisted mode).
    """
    __tablename__ = "automation_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Modes: MANUAL, ASSISTED, CONTROLLED_AUTO (Default is ASSISTED)
    mode: Mapped[str] = mapped_column(String(50), default="ASSISTED", nullable=False, index=True)
    
    # Safe operation toggles
    job_discovery_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    matching_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deduplication_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preparation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Submission Gate: Strictly default to True (requires explicit human approval before external submission)
    submission_requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Intervals & Thresholds
    discovery_interval_hours: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    max_daily_preparations: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    stale_job_threshold_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile")
