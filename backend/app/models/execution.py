import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ApplicationExecution(Base):
    """
    Step 9: Application Execution Record.
    Tracks each execution attempt of an approved application package through
    supported application workflows (MANUAL, ASSISTED, AUTOMATED).
    Preserves historical execution attempts and enforces auditability.
    """
    __tablename__ = "application_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    preparation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("application_preparations.id", ondelete="SET NULL"), nullable=True, index=True)

    # Execution Attempt Counter (1, 2, 3...) - preserves historical execution logs
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)

    # Execution Mode: MANUAL, ASSISTED, AUTOMATED
    mode: Mapped[str] = mapped_column(String(50), default="MANUAL", nullable=False, index=True)

    # Source Adapter: generic_web, manual, etc.
    source: Mapped[str] = mapped_column(String(100), default="generic_web", nullable=False, index=True)

    # State Machine:
    # NOT_STARTED, READY, AWAITING_APPROVAL, OPENING, NAVIGATING, FILLING,
    # AWAITING_USER, READY_TO_SUBMIT, SUBMITTING, SUBMITTED, FAILED, BLOCKED, CANCELLED
    status: Mapped[str] = mapped_column(String(50), default="NOT_STARTED", nullable=False, index=True)

    # Progress & Step Details
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    step_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Confidence-based Field Mappings
    field_mappings: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list, nullable=True)

    # Blocker & Failure Details
    blocker_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Human Gate Checkpoint
    requires_user_action: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    user_action_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Submission Evidence Verification (Never infer submitted without observable proof)
    submission_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    confirmation_evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Sanitized Browser Metadata (NO passwords, NO cookies, NO tokens)
    browser_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="executions")
    job: Mapped["Job"] = relationship("Job", back_populates="executions")
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="executions")
    preparation: Mapped[Optional["ApplicationPreparation"]] = relationship("ApplicationPreparation", back_populates="executions")
