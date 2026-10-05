from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class GovernmentSourceBase(BaseModel):
    organisation_name: str
    organisation_type: str = "other"
    government_level: str = "central"
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    parent_source_id: Optional[str] = None
    official_domain: str
    career_url: Optional[str] = None
    recruitment_url: Optional[str] = None
    vacancy_url: Optional[str] = None
    notification_url: Optional[str] = None
    source_type: str = "portal"
    source_status: str = "DISCOVERED"
    confidence_category: str = "AUTHORITATIVE"
    discovery_method: str = "search_engine"
    discovered_from: Optional[str] = None
    crawl_frequency_hours: int = 24
    confidence: float = 1.0
    relevance_score: float = 1.0
    metadata_json: Optional[str] = None


class GovernmentSourceCreate(GovernmentSourceBase):
    pass


class GovernmentSourceResponse(GovernmentSourceBase):
    id: str
    discovered_at: datetime
    last_seen: datetime
    last_checked: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    crawl_status: str = "idle"
    failure_count: int = 0
    vacancies_found: int = 0
    content_hash: Optional[str] = None

    # Continuous Monitoring & Adaptive Scheduling Fields
    crawl_interval_minutes: int = 1440
    next_crawl_at: Optional[datetime] = None
    last_crawled_at: Optional[datetime] = None
    last_successful_crawl_at: Optional[datetime] = None
    last_change_detected_at: Optional[datetime] = None
    crawl_count: int = 0
    successful_crawl_count: int = 0
    failed_crawl_count: int = 0
    consecutive_failures: int = 0
    change_frequency_category: str = "low"
    is_locked: bool = False
    locked_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GovernmentSourceListResponse(BaseModel):
    total: int
    items: List[GovernmentSourceResponse]


class GovernmentVacancyResponse(BaseModel):
    id: str
    job_id: str
    source_id: Optional[str] = None
    organisation_name: Optional[str] = None
    title: Optional[str] = None
    government_level: str
    organisation_type: str
    state: Optional[str] = None
    department: Optional[str] = None
    ministry: Optional[str] = None
    scheme_or_project: Optional[str] = None
    advertisement_number: Optional[str] = None
    employment_type: str
    contract_duration: Optional[str] = None
    pay_scale: Optional[str] = None
    number_of_positions: Optional[int] = None
    age_limit: Optional[str] = None
    selection_process: Optional[str] = None
    official_notification_url: Optional[str] = None
    official_application_url: Optional[str] = None
    application_mode: str
    application_email: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_sha256: Optional[str] = None
    extraction_status: str
    change_type: str
    corrigendum_details: Optional[str] = None

    # Freshness & Deadline Protection Fields
    published_at: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    deadline_status: str = "UNKNOWN"
    last_verified_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    # Associated Core Job details
    job_title: Optional[str] = None
    job_company: Optional[str] = None
    job_location: Optional[str] = None
    match_score: Optional[float] = None
    fit_category: Optional[str] = None
    decision: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GovernmentVacancyListResponse(BaseModel):
    total: int
    items: List[GovernmentVacancyResponse]


class StateCoverageItem(BaseModel):
    state: str
    is_ut: bool = False
    sources_count: int = 0
    active_sources: int = 0
    vacancies_count: int = 0
    status: str = "COVERED"  # COVERED, MINIMAL, UNEXPLORED


class SectorCoverageItem(BaseModel):
    sector: str
    sources_count: int = 0
    vacancies_count: int = 0


class GovernmentCoverageResponse(BaseModel):
    total_sources_discovered: int = 0
    verified_sources: int = 0
    active_sources: int = 0
    sources_checked_today: int = 0
    sources_never_checked: int = 0
    sources_requiring_manual_access: int = 0
    new_sources_discovered_recent: int = 0
    new_vacancies_discovered_recent: int = 0
    updated_vacancies_recent: int = 0
    expired_vacancies: int = 0

    # Sector breakdown
    central_government_sources: int = 0
    state_government_sources: int = 0
    union_territory_sources: int = 0
    psu_sources: int = 0
    research_institute_sources: int = 0
    university_sources: int = 0
    regulator_sources: int = 0
    healthcare_sources: int = 0
    district_municipal_sources: int = 0
    other_sources: int = 0

    # Full State/UT matrix (All 28 States + 8 UTs)
    states_coverage: List[StateCoverageItem] = Field(default_factory=list)
    sectors_coverage: List[SectorCoverageItem] = Field(default_factory=list)


class GovernmentDiscoveryTriggerRequest(BaseModel):
    scope: str = "ALL"  # ALL, CENTRAL, STATE, UT, PSU, RESEARCH, REGULATOR, CONTRACTUAL
    state_filter: Optional[str] = None
    max_search_queries: int = 25
    deep_recursive_crawl: bool = True
    dry_run: bool = False


class GovernmentCrawlRequest(BaseModel):
    batch_size: int = 20  # Batch processing chunk
    force_recheck: bool = False
    state_filter: Optional[str] = None
    organisation_type_filter: Optional[str] = None


class GovernmentDiscoveryRunResponse(BaseModel):
    id: str
    run_type: str
    status: str
    scope_filter: Optional[str] = None
    sources_discovered: int = 0
    sources_verified: int = 0
    vacancies_discovered: int = 0
    vacancies_created: int = 0
    vacancies_updated: int = 0
    duration_ms: Optional[float] = None
    coverage_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GovernmentChangeEventResponse(BaseModel):
    id: str
    source_id: str
    vacancy_id: Optional[str] = None
    url: str
    document_type: str
    previous_hash: Optional[str] = None
    new_hash: Optional[str] = None
    change_type: str
    change_summary: Optional[str] = None
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GovernmentMonitoringStatsResponse(BaseModel):
    total_registered_sources: int = 0
    sources_with_scheduled_crawl: int = 0
    sources_never_crawled: int = 0
    sources_currently_due: int = 0
    sources_currently_overdue: int = 0
    sources_crawling: int = 0
    sources_successfully_crawled_today: int = 0
    sources_failed_today: int = 0
    sources_blocked: int = 0
    sources_requiring_manual_access: int = 0
    new_sources_discovered_today: int = 0
    new_vacancies_today: int = 0
    updated_vacancies_today: int = 0
    corrigenda_count: int = 0
    deadline_extensions_count: int = 0
    expired_vacancies_count: int = 0
    deadline_lt_24h_count: int = 0
    deadline_lt_3d_count: int = 0
    sources_within_freshness_sla: int = 0
    sources_outside_freshness_sla: int = 0
    oldest_overdue_source: Optional[str] = None
    last_global_crawl: Optional[datetime] = None
    next_scheduled_crawl: Optional[datetime] = None
    discovery_engine_last_run: Optional[datetime] = None
    next_global_discovery: Optional[datetime] = None


class GovernmentMonitoringTickResponse(BaseModel):
    due_sources_count: int = 0
    enqueued_crawls: int = 0
    skipped_crawls: int = 0
    discovery_enqueued: bool = False
    enqueued_task_ids: List[str] = Field(default_factory=list)


class GovernmentUnresolvedTargetResponse(BaseModel):
    id: str
    target_name: str
    target_type: str
    state: Optional[str] = None
    district: Optional[str] = None
    reason: str
    attempted_queries: Optional[str] = None
    attempted_domains: Optional[str] = None
    discovery_status: str
    attempts_count: int
    last_attempted_at: datetime
    retry_at: Optional[datetime] = None
    resolved_source_id: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GovernmentUnresolvedTargetListResponse(BaseModel):
    total: int
    items: List[GovernmentUnresolvedTargetResponse]


class GovernmentUniverseMissionRequest(BaseModel):
    max_passes: int = 10
    run_search: bool = True
    batch_size: int = 50


class GovernmentUniverseMissionResponse(BaseModel):
    status: str
    passes_completed: int
    total_raw_targets: int
    total_deduplicated_targets: int
    verified_sources: int
    unresolved_backlog: int
    pass_results: Dict[str, Any]
    metrics: Dict[str, Any]

