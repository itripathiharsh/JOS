from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class SourceCapabilities(BaseModel):
    """Declarative capabilities of a job source connector."""
    supports_search: bool = True
    supports_location_filter: bool = True
    supports_remote_filter: bool = True
    supports_pagination: bool = True
    max_limit: int = 100


class NormalizedJob(BaseModel):
    """
    Standardized intermediate job entity produced by all source connectors.
    Decouples source-specific formats from internal database models.
    """
    source: str = Field(..., description="Unique source identifier, e.g., 'remotive'")
    external_job_id: str = Field(..., description="Unique job ID within the source platform")
    url: Optional[str] = Field(None, description="Direct URL to view/apply for the job posting")
    title: str = Field(..., description="Standardized job title")
    company: str = Field(..., description="Hiring organization name")
    location: Optional[str] = Field(None, description="Location text or geographical eligibility")
    work_mode: str = Field(
        "unknown",
        description="Work arrangement: remote, hybrid, onsite, unknown"
    )
    employment_type: Optional[str] = Field(None, description="Employment type: full_time, part_time, contract, freelance, internship")
    skills: List[str] = Field(default_factory=list, description="Extracted or source-provided skills/technology tags")
    experience_level: Optional[str] = Field(None, description="Extracted experience level: entry, mid, senior, lead, executive")
    description: Optional[str] = Field(None, description="Full job description (cleaned text or formatted)")
    requirements: Optional[str] = Field(None, description="Extracted requirements or qualifications")
    responsibilities: Optional[str] = Field(None, description="Extracted responsibilities or duties")
    
    salary_min: Optional[float] = Field(None, description="Minimum compensation amount if disclosed")
    salary_max: Optional[float] = Field(None, description="Maximum compensation amount if disclosed")
    currency: Optional[str] = Field(None, description="Currency code (e.g. USD, EUR, INR)")
    
    posted_at: Optional[datetime] = Field(None, description="Publication timestamp in UTC")
    expires_at: Optional[datetime] = Field(None, description="Expiration or closing date in UTC")
    raw_payload: Optional[Dict[str, Any]] = Field(None, description="Raw source metadata for debugging")

    @field_validator("work_mode")
    @classmethod
    def validate_work_mode(cls, v: str) -> str:
        valid_modes = {"remote", "hybrid", "onsite", "on-site", "unknown"}
        v_clean = (v or "unknown").strip().lower()
        if v_clean == "on-site":
            v_clean = "onsite"
        return v_clean if v_clean in valid_modes else "unknown"

    @field_validator("title", "company", "source", "external_job_id")
    @classmethod
    def validate_required_non_empty(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Field cannot be empty")
        return str(v).strip()


class SourceHealth(BaseModel):
    healthy: bool
    message: str
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class IngestionStats(BaseModel):
    source: str
    query: str
    jobs_fetched: int = 0
    jobs_created: int = 0
    jobs_updated: int = 0
    jobs_skipped: int = 0
    errors: List[str] = Field(default_factory=list)
