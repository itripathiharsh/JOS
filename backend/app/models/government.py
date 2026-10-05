import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, Integer, Numeric, Float, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship, backref
from app.models.base import Base


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class GovernmentSource(Base):
    """
    Persistent registry of Indian government, PSU, research, academic,
    regulatory, mission, project, and contractual employment sources.
    Optimizes for source coverage across Central, 28 States, 8 UTs, and local bodies.
    """
    __tablename__ = "government_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    organisation_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    organisation_type: Mapped[str] = mapped_column(
        String(100),
        default="other",
        nullable=False,
        index=True
    )  # ministry, department, attached_office, subordinate_office, autonomous_body, statutory_body, psu, research_institute, university, college, hospital, regulator, authority, mission, project, district_administration, municipal_body, other

    government_level: Mapped[str] = mapped_column(
        String(50),
        default="central",
        nullable=False,
        index=True
    )  # central, state, ut, district, municipal

    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    parent_source_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("government_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    official_domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    career_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    recruitment_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    vacancy_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    notification_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    source_type: Mapped[str] = mapped_column(
        String(50),
        default="portal",
        nullable=False,
        index=True
    )  # portal, directory, pdf_listing, direct_html, contractual_portal

    source_status: Mapped[str] = mapped_column(
        String(50),
        default="DISCOVERED",
        nullable=False,
        index=True
    )  # DISCOVERED, VERIFIED, ACTIVE, TEMPORARILY_UNAVAILABLE, BLOCKED, DEAD, DUPLICATE, REQUIRES_MANUAL_ACCESS

    confidence_category: Mapped[str] = mapped_column(
        String(50),
        default="AUTHORITATIVE",
        nullable=False,
        index=True
    )  # AUTHORITATIVE, GOVERNMENT_AFFILIATED, INSTITUTIONAL, DISCOVERED_UNVERIFIED, INVALID

    discovery_method: Mapped[str] = mapped_column(String(100), default="search_engine")  # seed, search_engine, recursive_link, directory, sitemap
    discovered_from: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    crawl_frequency_hours: Mapped[int] = mapped_column(Integer, default=24)
    crawl_status: Mapped[str] = mapped_column(String(50), default="idle")  # idle, crawling, success, failed, blocked, connection_failed, timeout
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    vacancies_found: Mapped[int] = mapped_column(Integer, default=0)

    # Continuous Monitoring & Adaptive Scheduling Fields
    crawl_interval_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False)
    next_crawl_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_crawl_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_change_detected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    crawl_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_crawl_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_crawl_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    change_frequency_category: Mapped[str] = mapped_column(String(50), default="low", index=True, nullable=False)  # high, medium, low, very_low
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    children: Mapped[List["GovernmentSource"]] = relationship(
        "GovernmentSource",
        backref=backref("parent_source", remote_side="GovernmentSource.id")
    )
    vacancies: Mapped[List["GovernmentVacancy"]] = relationship(
        "GovernmentVacancy",
        back_populates="source",
        cascade="all, delete-orphan"
    )
    change_events: Mapped[List["GovernmentChangeEvent"]] = relationship(
        "GovernmentChangeEvent",
        back_populates="source",
        cascade="all, delete-orphan"
    )


class GovernmentVacancy(Base):
    """
    Detailed government-specific metadata for public sector and contractual postings,
    extending the core Job entity with official Gazette/PDF provenance, pay-scales,
    contract duration, selection mode, and corrigendum tracking.
    """
    __tablename__ = "government_vacancies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    source_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("government_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    government_level: Mapped[str] = mapped_column(String(50), default="central", index=True)
    organisation_type: Mapped[str] = mapped_column(String(100), default="other", index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ministry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scheme_or_project: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    advertisement_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    employment_type: Mapped[str] = mapped_column(
        String(50),
        default="Contract",
        index=True
    )  # Permanent, Contract, Temporary, Project, Consultant, Young Professional, Fellowship, Research, Internship, Walk-in, Outsourced, Empanelment

    contract_duration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pay_scale: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    number_of_positions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_limit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    selection_process: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    official_notification_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    official_application_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    application_mode: Mapped[str] = mapped_column(
        String(50),
        default="online_portal"
    )  # online_portal, email, postal, walk_in
    application_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    document_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    pdf_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    pdf_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    pdf_extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(
        String(50),
        default="not_applicable"
    )  # success, partial, failed, not_applicable

    change_type: Mapped[str] = mapped_column(
        String(50),
        default="new_vacancy"
    )  # new_vacancy, updated_vacancy, deadline_extended, corrigendum, vacancy_cancelled, vacancy_closed
    corrigendum_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Deadline Protection & Freshness Fields
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    application_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deadline_status: Mapped[str] = mapped_column(
        String(50),
        default="UNKNOWN",
        index=True,
        nullable=False
    )  # OPEN, DEADLINE_APPROACHING, DEADLINE_TODAY, EXPIRED, EXTENDED, CANCELLED, UNKNOWN
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    job: Mapped["Job"] = relationship("Job", backref=backref("government_detail", uselist=False, cascade="all, delete-orphan"))
    source: Mapped[Optional["GovernmentSource"]] = relationship("GovernmentSource", back_populates="vacancies")
    change_events: Mapped[List["GovernmentChangeEvent"]] = relationship(
        "GovernmentChangeEvent",
        back_populates="vacancy",
        cascade="all, delete-orphan"
    )


class GovernmentChangeEvent(Base):
    """
    Audit log of detected changes across government sources and vacancies.
    Captures document hash differences, corrigenda, deadline extensions, and status changes.
    """
    __tablename__ = "government_change_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("government_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    vacancy_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("government_vacancies.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), default="page")  # page, pdf, notice
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    new_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    change_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # NEW, UPDATED, EXTENDED, CORRIGENDUM, CANCELLED, CLOSED, REMOVED, RESTORED
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, index=True)

    source: Mapped["GovernmentSource"] = relationship("GovernmentSource", back_populates="change_events")
    vacancy: Mapped[Optional["GovernmentVacancy"]] = relationship("GovernmentVacancy", back_populates="change_events")


class GovernmentDiscoveryRun(Base):
    """
    Execution run audit log for government source discovery and vacancy crawls.
    """
    __tablename__ = "government_discovery_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_type: Mapped[str] = mapped_column(String(50), default="source_discovery")  # source_discovery, vacancy_crawl, full_refresh
    status: Mapped[str] = mapped_column(String(50), default="in_progress", index=True)  # in_progress, completed, failed
    scope_filter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    sources_discovered: Mapped[int] = mapped_column(Integer, default=0)
    sources_verified: Mapped[int] = mapped_column(Integer, default=0)
    vacancies_discovered: Mapped[int] = mapped_column(Integer, default=0)
    vacancies_created: Mapped[int] = mapped_column(Integer, default=0)
    vacancies_updated: Mapped[int] = mapped_column(Integer, default=0)

    duration_ms: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    coverage_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class GovernmentUnresolvedTarget(Base):
    """
    Persistent backlog for discovery targets from the universe specifications
    that could not currently be resolved to an authoritative public domain or hiring endpoint.
    Maintains attempted queries, domains, failure reasons, and retry schedules (Phase 15).
    """
    __tablename__ = "government_unresolved_targets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    target_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(
        String(100),
        default="ORGANISATION",
        nullable=False,
        index=True
    )  # ORGANISATION, STATE_TARGET, DISTRICT_TARGET, LOCAL_BODY_TARGET, RECRUITMENT_ENDPOINT_TARGET, SEARCH_TARGET, HIRING_QUERY
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(String(255), default="unresolved_domain")
    attempted_queries: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    attempted_domains: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    discovery_status: Mapped[str] = mapped_column(
        String(50),
        default="UNRESOLVED",
        nullable=False,
        index=True
    )  # UNRESOLVED, RETRYING, RESOLVED, ABANDONED
    attempts_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    resolved_source_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("government_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

