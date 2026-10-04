from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class ApplicationEventResponse(BaseModel):
    id: str
    application_id: str
    event_type: str
    description: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationBase(BaseModel):
    job_id: Optional[str] = None
    candidate_id: Optional[str] = None
    status: str = "draft"
    source: Optional[str] = None
    application_url: Optional[str] = None
    resume_used: Optional[str] = None
    notes: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationResponse(ApplicationBase):
    id: str
    lifecycle_stage: str = "NOT_STARTED"
    outcome_category: Optional[str] = None
    outcome_provenance: str = "UNKNOWN"
    rejection_category: Optional[str] = None
    rejection_reason: Optional[str] = None
    last_outcome_date: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    events: List[ApplicationEventResponse] = []

    model_config = ConfigDict(from_attributes=True)



class ApplicationListResponse(BaseModel):
    items: List[ApplicationResponse]
    total: int
