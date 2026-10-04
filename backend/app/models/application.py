import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from typing import Optional, List, Dict, Any


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    candidate_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="SET NULL"), nullable=True)
    
    # Status: legacy compatibility (draft, preparation, submitted, assessment, interview, offer, rejected, human_action_required)
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    
    # Step 10: Normalized Application Lifecycle Stage:
    # NOT_STARTED, PREPARED, IN_PROGRESS, AWAITING_USER, SUBMITTED, ACKNOWLEDGED,
    # SCREENING, INTERVIEW, OFFER, ACCEPTED, REJECTED, WITHDRAWN, EXPIRED, NO_RESPONSE
    lifecycle_stage: Mapped[str] = mapped_column(String(50), default="NOT_STARTED", index=True)

    # Step 10: Structured Outcome & Provenance Tracking
    outcome_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # positive, negative, unknown, pending
    outcome_provenance: Mapped[str] = mapped_column(String(50), default="UNKNOWN", index=True)    # USER_CONFIRMED, SYSTEM_DETECTED, IMPORTED, UNKNOWN
    rejection_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True) # experience_gap, missing_skill, location, salary, role_mismatch, resume_issue, interview_performance, technical_assessment, position_closed, unknown, other
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_outcome_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Step 10: Immutable Context Snapshots (historical point-in-time state preservation)
    candidate_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    job_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    decision_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    artifacts_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    application_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    resume_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationship to events, preparation, executions, notes, and overrides
    events: Mapped[List["ApplicationEvent"]] = relationship("ApplicationEvent", back_populates="application", cascade="all, delete-orphan", order_by="ApplicationEvent.created_at")
    preparation: Mapped[Optional["ApplicationPreparation"]] = relationship("ApplicationPreparation", back_populates="application", uselist=False)
    executions: Mapped[List["ApplicationExecution"]] = relationship("ApplicationExecution", back_populates="application", cascade="all, delete-orphan", order_by="ApplicationExecution.attempt_number")
    notes_list: Mapped[List["ApplicationNote"]] = relationship("ApplicationNote", back_populates="application", cascade="all, delete-orphan", order_by="desc(ApplicationNote.created_at)")
    overrides: Mapped[List["ApplicationOverride"]] = relationship("ApplicationOverride", back_populates="application", cascade="all, delete-orphan", order_by="desc(ApplicationOverride.created_at)")


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Event types: application_created, preparation_started, application_submitted, assessment, interview, rejected, offer, human_action_required, etc.
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)

    # Step 10: Provenance and Actor tracking
    actor: Mapped[str] = mapped_column(String(50), default="system")  # user, system, recruiter, import
    provenance: Mapped[str] = mapped_column(String(50), default="SYSTEM_DETECTED") # USER_CONFIRMED, SYSTEM_DETECTED, IMPORTED, UNKNOWN

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    application: Mapped["Application"] = relationship("Application", back_populates="events")


class ApplicationNote(Base):
    """
    Step 10: Append-only timestamped application notes with structured categories.
    Preserves recruiter feedback, interview impressions, and follow-ups without overwriting history.
    """
    __tablename__ = "application_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(100), default="candidate")
    category: Mapped[str] = mapped_column(String(50), default="general", index=True) # general, recruiter, interview, compensation, referral, follow_up
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    application: Mapped["Application"] = relationship("Application", back_populates="notes_list")


class ApplicationOverride(Base):
    """
    Step 10: Preserves candidate overrides against system decisions.
    Records original decision vs override decision, rationale, and timestamp.
    """
    __tablename__ = "application_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    application_id: Mapped[str] = mapped_column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    original_decision: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # SKIP, REVIEW, APPLY
    override_decision: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # APPLY, REVIEW, SKIP
    override_type: Mapped[str] = mapped_column(String(50), default="decision") # decision, salary_floor, role_relevance, hard_requirement
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    application: Mapped["Application"] = relationship("Application", back_populates="overrides")

