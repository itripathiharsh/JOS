from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class JobBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    work_mode: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = "USD"
    application_url: Optional[str] = None
    source: str
    external_job_id: Optional[str] = None
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: Optional[str] = "discovered"


class JobCreate(JobBase):
    pass


class JobOccurrenceResponse(BaseModel):
    job_id: str
    source: str
    external_job_id: Optional[str] = None
    application_url: Optional[str] = None
    canonical_url: Optional[str] = None
    discovered_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    is_canonical: bool = True
    duplicate_status: str = "canonical"
    duplicate_confidence: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobDuplicateLinkResponse(BaseModel):
    id: str
    canonical_job_id: str
    duplicate_job_id: str
    confidence: str
    confidence_score: float
    match_method: str
    status: str
    evidence: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


from app.schemas.decision import ApplicationDecisionResponse


class JobResponse(JobBase):
    id: str
    canonical_job_id: Optional[str] = None
    is_canonical: bool = True
    duplicate_status: str = "canonical"
    duplicate_confidence: Optional[str] = None
    canonical_url: Optional[str] = None
    occurrences_count: int = 1
    sources: List[str] = []
    discovered_at: datetime
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    match_score: Optional[float] = None
    fit_category: Optional[str] = None
    application_decision: Optional[str] = None
    decision_reason: Optional[str] = None
    decision_risk_level: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobDetailResponse(JobResponse):
    raw_payload: Optional[str] = None
    occurrences: List[JobOccurrenceResponse] = []
    duplicate_links: List[JobDuplicateLinkResponse] = []
    decision_details: Optional[ApplicationDecisionResponse] = None


class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int
    skip: int = 0
    limit: int = 50
    canonical_count: int = 0
    duplicate_count: int = 0
    possible_duplicate_count: int = 0
    apply_count: int = 0
    review_count: int = 0
    skip_count: int = 0



class FetchJobsRequest(BaseModel):
    keyword: str = Field("", description="Search term, e.g. 'AI Engineer', 'Backend', 'Python'")
    location: Optional[str] = Field(None, description="Location filter text")
    remote: Optional[bool] = Field(True, description="Filter for remote positions")
    limit: int = Field(20, ge=1, le=100, description="Max jobs to fetch")
    source: str = Field("remotive", description="Connector identifier, e.g. 'remotive'")


class IngestionResponse(BaseModel):
    success: bool
    source: str
    query: str
    jobs_fetched: int
    jobs_created: int
    jobs_updated: int
    jobs_skipped: int
    errors: List[str] = []
    message: str


class CompanyResponse(BaseModel):
    id: str
    name: str
    website: Optional[str] = None
    careers_url: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceStatusResponse(BaseModel):
    id: str
    source: str
    status: str
    last_checked: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    jobs_fetched: int = 0
    jobs_created: int = 0
    jobs_updated: int = 0
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BatchDeduplicationRequest(BaseModel):
    limit: int = Field(500, ge=1, le=5000, description="Max jobs to evaluate")
    dry_run: bool = Field(False, description="Preview potential duplicates without writing links")


class BatchDeduplicationResponse(BaseModel):
    jobs_evaluated: int
    duplicates_found: int
    possible_duplicates_found: int
    duration_ms: float
    message: str
