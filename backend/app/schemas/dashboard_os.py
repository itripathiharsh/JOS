from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DashboardHealthKPIs(BaseModel):
    """Core health and operational metrics for the job search."""
    jobs_discovered: int = Field(..., description="Total raw jobs discovered across sources")
    canonical_jobs: int = Field(..., description="Unique canonical job postings")
    high_relevance_jobs: int = Field(..., description="Jobs with HIGH_RELEVANCE fit category")
    ready_to_apply: int = Field(..., description="Jobs ready to apply (Decision=APPLY, Preparation=READY, not submitted)")
    review_required: int = Field(..., description="Jobs requiring candidate review or confirmation")
    applications_submitted: int = Field(..., description="Total applications submitted to employers")
    active_interviews: int = Field(..., description="Applications in SCREENING or INTERVIEW stage")
    offers_received: int = Field(..., description="Applications in OFFER or ACCEPTED stage")
    awaiting_response: int = Field(..., description="Applications submitted awaiting employer response")


class AttentionQueueItem(BaseModel):
    """An actionable, prioritized task for the candidate to address today."""
    id: str
    priority: str = Field(..., description="HIGH, MEDIUM, INFO")
    category: str = Field(..., description="APPROVAL, BLOCKED, DECISION, PREPARATION, FOLLOW_UP, INTERVIEW, PROFILE")
    title: str
    description: str
    job_id: Optional[str] = None
    application_id: Optional[str] = None
    action_label: str
    action_target: str = Field(..., description="jobs, applications, profile")
    action_type: str = Field(..., description="open_job, open_execution, open_preparation, open_memory, open_profile")
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class DashboardFunnelStep(BaseModel):
    """A single stage in the end-to-end job discovery and application funnel."""
    stage: str
    label: str
    count: int
    conversion_from_prev: Optional[float] = Field(None, description="Percentage conversion from previous funnel step")


class DashboardFunnel(BaseModel):
    """Multi-stage funnel from raw discovery to offer."""
    discovered: int
    unique_canonical: int
    career_aligned: int
    decided_apply_review: int
    prepared: int
    submitted: int
    interviews: int
    offers: int
    steps: List[DashboardFunnelStep]


class PipelineStageCount(BaseModel):
    """Count of applications in a specific lifecycle stage."""
    stage: str
    label: str
    count: int
    is_terminal: bool = False
    is_positive: bool = False
    is_active: bool = False


class MatchQualityDistribution(BaseModel):
    """Breakdown of available jobs across match quality tiers."""
    high_relevance: int
    good_relevance: int
    partial_relevance: int
    low_relevance: int
    hard_mismatches: int
    insufficient_data: int


class TopOpportunityItem(BaseModel):
    """High-quality job opportunity ready for candidate action."""
    id: str
    title: str
    company: str
    source: str
    location: Optional[str] = None
    work_mode: Optional[str] = None
    salary_display: Optional[str] = None
    match_score: Optional[float] = None
    fit_category: Optional[str] = None
    decision: Optional[str] = None
    decision_reasons: List[str] = []
    hard_requirement_status: Optional[str] = None
    is_canonical: bool = True
    application_id: Optional[str] = None
    preparation_status: Optional[str] = None
    execution_status: Optional[str] = None
    posted_at: Optional[datetime] = None


class SourceHealthItem(BaseModel):
    """Operational health metrics for a registered job source connector."""
    source: str
    status: str  # active, idle, degraded, error
    last_checked: Optional[datetime] = None
    last_success: Optional[datetime] = None
    jobs_fetched: int = 0
    jobs_created: int = 0
    jobs_updated: int = 0
    error_message: Optional[str] = None


class ProfileHealthSummary(BaseModel):
    """Candidate profile completeness and readiness status."""
    completeness_score: int
    is_ready_for_apply: bool
    missing_critical_items: List[str]
    pending_confirmations: List[str]
    has_resume: bool
    target_roles_count: int


class RecentActivityItem(BaseModel):
    """Unified chronological feed item across applications, decisions, and system events."""
    id: str
    timestamp: datetime
    event_type: str
    title: str
    description: str
    actor: str
    job_id: Optional[str] = None
    application_id: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None


class FeedbackSummaryKPIs(BaseModel):
    """Key conversion rates and sample size status from ApplicationFeedbackEngine."""
    submitted_count: int
    app_to_interview_rate: float
    app_to_interview_fraction: str
    app_to_offer_rate: float
    app_to_offer_fraction: str
    interview_to_offer_rate: float
    interview_to_offer_fraction: str
    sample_size_alert: Optional[str] = None
    top_observations: List[str] = []


class AutomationTelemetrySummary(BaseModel):
    """Step 12: Controlled autonomy state and task queue counts."""
    mode: str
    is_active: bool
    pending_tasks: int
    running_tasks: int
    failed_tasks: int
    blocked_tasks: int
    last_run: Optional[datetime] = None


class JobOperatingSystemResponse(BaseModel):
    """Comprehensive, single-request payload for the Job Operating System Dashboard."""
    health_kpis: DashboardHealthKPIs
    action_queue: List[AttentionQueueItem]
    funnel: DashboardFunnel
    pipeline: List[PipelineStageCount]
    match_quality: MatchQualityDistribution
    top_opportunities: List[TopOpportunityItem]
    source_health: List[SourceHealthItem]
    profile_health: ProfileHealthSummary
    recent_activity: List[RecentActivityItem]
    feedback_summary: FeedbackSummaryKPIs
    automation_telemetry: Optional[AutomationTelemetrySummary] = None
    generated_at: datetime
