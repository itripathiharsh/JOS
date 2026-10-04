from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class OutcomeUpdateRequest(BaseModel):
    lifecycle_stage: str
    provenance: str = "USER_CONFIRMED"
    rejection_category: Optional[str] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None


class NoteCreateRequest(BaseModel):
    content: str
    category: str = "general"
    author: str = "candidate"


class NoteResponse(BaseModel):
    id: str
    application_id: str
    author: str
    category: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OverrideCreateRequest(BaseModel):
    override_decision: str
    original_decision: Optional[str] = None
    override_type: str = "decision"
    reason: Optional[str] = None


class OverrideResponse(BaseModel):
    id: str
    application_id: str
    original_decision: str
    override_decision: str
    override_type: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimelineItemResponse(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    title: str
    description: Optional[str] = None
    actor: str = "system"
    provenance: str = "SYSTEM_DETECTED"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApplicationMemoryResponse(BaseModel):
    id: str
    job_id: Optional[str] = None
    candidate_id: Optional[str] = None
    lifecycle_stage: str
    status: str
    source: Optional[str] = None
    application_url: Optional[str] = None
    outcome_category: Optional[str] = None
    outcome_provenance: str
    rejection_category: Optional[str] = None
    rejection_reason: Optional[str] = None
    last_outcome_date: Optional[datetime] = None
    candidate_snapshot: Optional[Dict[str, Any]] = None
    job_snapshot: Optional[Dict[str, Any]] = None
    decision_snapshot: Optional[Dict[str, Any]] = None
    artifacts_snapshot: Optional[Dict[str, Any]] = None
    notes: List[NoteResponse] = Field(default_factory=list)
    overrides: List[OverrideResponse] = Field(default_factory=list)
    timeline: List[TimelineItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
