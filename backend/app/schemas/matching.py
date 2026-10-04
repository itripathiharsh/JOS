from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DimensionDetailSchema(BaseModel):
    name: str
    status: str
    score: float
    weight: float
    is_known: bool
    explanation: str


class MatchResultResponse(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    engine_version: str

    overall_score: float
    fit_category: str

    # Hard Requirement Evaluation (Phase 4.1)
    has_hard_mismatch: bool = False
    hard_requirement_status: str = "PASSED"
    hard_requirement_warnings: List[Dict[str, Any]] = Field(default_factory=list)

    role_score: float
    skill_score: float
    experience_score: float
    location_score: float
    work_mode_score: float
    salary_score: float
    education_score: float
    employment_type_score: float

    matched_required_skills: List[Dict[str, str]] = Field(default_factory=list)
    missing_required_skills: List[str] = Field(default_factory=list)
    matched_preferred_skills: List[Dict[str, str]] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)

    dimension_details: Dict[str, Any] = Field(default_factory=dict)
    concerns: List[str] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)

    data_completeness: float
    data_completeness_level: str

    calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkMatchRequest(BaseModel):
    limit: int = Field(50, ge=1, le=100, description="Maximum number of stored jobs to analyze")
    force_recompute: bool = Field(False, description="Whether to recompute matches even if cache is fresh")


class BulkMatchResponse(BaseModel):
    processed: int
    created: int
    reused: int
    results: List[MatchResultResponse] = Field(default_factory=list)
