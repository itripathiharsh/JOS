import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, JSON, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_match_job_candidate"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    engine_version: Mapped[str] = mapped_column(String(50), default="1.1.0", index=True)

    # Scoring & Category
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    fit_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # HIGH_RELEVANCE, GOOD_RELEVANCE, PARTIAL_RELEVANCE, LOW_RELEVANCE, INSUFFICIENT_DATA

    # Hard Requirement Evaluation (Phase 4.1)
    has_hard_mismatch: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    hard_requirement_status: Mapped[str] = mapped_column(String(50), default="PASSED")
    hard_requirement_warnings: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # Individual Dimension Scores (0.0 - 100.0)
    role_score: Mapped[float] = mapped_column(Float, nullable=False)
    skill_score: Mapped[float] = mapped_column(Float, nullable=False)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False)
    location_score: Mapped[float] = mapped_column(Float, nullable=False)
    work_mode_score: Mapped[float] = mapped_column(Float, nullable=False)
    salary_score: Mapped[float] = mapped_column(Float, nullable=False)
    education_score: Mapped[float] = mapped_column(Float, nullable=False)
    employment_type_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Detailed Skill Breakdown
    matched_required_skills: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    missing_required_skills: Mapped[List[str]] = mapped_column(JSON, default=list)
    matched_preferred_skills: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    missing_preferred_skills: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Dimension Details (Score, Status, Weight, Explanation per dimension)
    dimension_details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Human-Readable Explanations & Concerns
    concerns: Mapped[List[str]] = mapped_column(JSON, default=list)
    explanations: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Reliability / Data Completeness
    data_completeness: Mapped[float] = mapped_column(Float, default=100.0)  # 0.0 - 100.0%
    data_completeness_level: Mapped[str] = mapped_column(String(50), default="MEDIUM")  # HIGH, MEDIUM, LOW

    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="match_results")
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="match_results")
