import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ApplicationDecision(Base):
    __tablename__ = "application_decisions"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_decision_job_candidate"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    # Primary Decision: APPLY, REVIEW, SKIP
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Quantitative & Risk Signals
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)  # 0.0 - 1.0
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW", index=True)  # LOW, MEDIUM, HIGH

    # Structured Reason Collections
    reasons: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    supporting_factors: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    disqualifying_factors: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    review_reasons: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)

    # Detailed Evaluation Metadata (snapshot of match score, hard mismatch, duplicate status, history, etc.)
    evaluation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Engine metadata
    engine_version: Mapped[str] = mapped_column(String(50), default="1.0.0", index=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="decisions")
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="decisions")
