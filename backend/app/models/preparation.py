import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ApplicationPreparation(Base):
    __tablename__ = "application_preparations"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_preparation_job_candidate"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    application_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    # Regeneration Version Counter (increments 1, 2, 3... on regeneration to avoid uncontrolled duplicates)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Readiness Assessment: READY, READY_WITH_REVIEW, BLOCKED
    readiness_status: Mapped[str] = mapped_column(String(50), default="READY_WITH_REVIEW", index=True)
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 100.0
    readiness_reasons: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)

    # Snapshots
    job_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    decision_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Resume Recommendation & Tailoring
    resume_recommendation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Extracted Requirements
    extracted_requirements: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Candidate Evidence Mapping
    evidence_mapping: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list, nullable=True)

    # Skills Recommendation (Strong Match, Supporting, Missing, Do Not Claim)
    skills_recommendation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Deterministic Generated Content (Summary, Tailored Cover Letter, Short Message, Claim Safety Audit)
    generated_content: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Application Questions & Proposed Answers
    question_answers: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list, nullable=True)

    # Warnings & Human Confirmation Checklist
    warnings: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    human_confirmation_required: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list, nullable=True)

    # User overrides & human confirmed modifications (preserves human edits across views)
    user_overrides: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    user_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata & Versioning
    engine_version: Mapped[str] = mapped_column(String(50), default="1.0.0", index=True)
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    application: Mapped[Optional["Application"]] = relationship("Application", back_populates="preparation")
    job: Mapped["Job"] = relationship("Job", back_populates="preparations")
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="preparations")
    executions: Mapped[List["ApplicationExecution"]] = relationship("ApplicationExecution", back_populates="preparation")
