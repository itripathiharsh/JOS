from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ApplicationDecisionResponse(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    decision: str  # APPLY, REVIEW, SKIP
    confidence_score: float
    risk_level: str  # LOW, MEDIUM, HIGH
    reasons: List[str] = Field(default_factory=list)
    supporting_factors: List[str] = Field(default_factory=list)
    disqualifying_factors: List[str] = Field(default_factory=list)
    review_reasons: List[str] = Field(default_factory=list)
    evaluation_metadata: Dict[str, Any] = Field(default_factory=dict)
    engine_version: str
    decided_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DecisionBatchRequest(BaseModel):
    limit: int = Field(50, ge=1, le=200, description="Max jobs to process")
    force_recompute: bool = Field(False, description="Force re-evaluation even if decision is fresh")
    only_canonical: bool = Field(True, description="Evaluate only canonical jobs")


class DecisionBatchResponse(BaseModel):
    processed: int
    reused: int
    new_or_updated: int
    apply_count: int
    review_count: int
    skip_count: int
    items: List[ApplicationDecisionResponse] = Field(default_factory=list)


class DecisionListResponse(BaseModel):
    total: int
    items: List[ApplicationDecisionResponse]
    apply_count: int
    review_count: int
    skip_count: int
