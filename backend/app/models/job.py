import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Numeric, UniqueConstraint, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from typing import Optional, List


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_job_id", name="uq_source_external_job_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # remote, hybrid, on-site, unknown
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    salary_min: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), default="USD")
    
    application_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # remotive, manual, etc.
    external_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=get_utc_now, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="discovered", index=True)  # discovered, relevant, applied, archived
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Step 6: Anti-Duplicate & Canonical Identity Fields
    canonical_job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    duplicate_status: Mapped[str] = mapped_column(String(50), default="canonical", index=True)  # canonical, duplicate, possible_duplicate
    duplicate_confidence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # VERY_HIGH, HIGH, MEDIUM, LOW
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    match_results: Mapped[List["MatchResult"]] = relationship("MatchResult", back_populates="job", cascade="all, delete-orphan")
    decisions: Mapped[List["ApplicationDecision"]] = relationship("ApplicationDecision", back_populates="job", cascade="all, delete-orphan")
    preparations: Mapped[List["ApplicationPreparation"]] = relationship("ApplicationPreparation", back_populates="job", cascade="all, delete-orphan")
    executions: Mapped[List["ApplicationExecution"]] = relationship("ApplicationExecution", back_populates="job", cascade="all, delete-orphan")
    duplicate_links_as_canonical: Mapped[List["JobDuplicate"]] = relationship(
        "JobDuplicate",
        foreign_keys="JobDuplicate.canonical_job_id",
        back_populates="canonical_job",
        cascade="all, delete-orphan",
    )
    duplicate_links_as_duplicate: Mapped[List["JobDuplicate"]] = relationship(
        "JobDuplicate",
        foreign_keys="JobDuplicate.duplicate_job_id",
        back_populates="duplicate_job",
        cascade="all, delete-orphan",
    )



class JobDuplicate(Base):
    __tablename__ = "job_duplicates"
    __table_args__ = (
        UniqueConstraint("canonical_job_id", "duplicate_job_id", name="uq_canonical_duplicate"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    canonical_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    duplicate_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    confidence: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # VERY_HIGH, HIGH, MEDIUM, LOW
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)  # 0.0000 to 1.0000
    match_method: Mapped[str] = mapped_column(String(100), nullable=False)  # canonical_url, requisition_id, company_title_location, etc.
    status: Mapped[str] = mapped_column(String(50), default="auto_merged", index=True)  # auto_merged, possible_duplicate, confirmed_duplicate, rejected_duplicate

    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON payload with signals, scores, checks

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    canonical_job: Mapped["Job"] = relationship("Job", foreign_keys=[canonical_job_id], back_populates="duplicate_links_as_canonical")
    duplicate_job: Mapped["Job"] = relationship("Job", foreign_keys=[duplicate_job_id], back_populates="duplicate_links_as_duplicate")



class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    careers_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, completed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)


class SourceStatus(Base):
    __tablename__ = "source_statuses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="idle")  # idle, active, degraded, error
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    jobs_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

