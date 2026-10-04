from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PreparationRequest(BaseModel):
    candidate_id: Optional[str] = None
    force_regenerate: bool = False
    allow_skip: bool = False
    user_overrides: Optional[Dict[str, Any]] = None
    user_notes: Optional[str] = None


class PreparationUpdateRequest(BaseModel):
    user_overrides: Dict[str, Any] = Field(default_factory=dict)
    user_notes: Optional[str] = None
    candidate_id: Optional[str] = None


class ApplicationPreparationResponse(BaseModel):
    id: str
    application_id: Optional[str] = None
    job_id: str
    candidate_id: str
    version: int
    readiness_status: str
    readiness_score: float
    readiness_reasons: Optional[List[str]] = None
    job_snapshot: Optional[Dict[str, Any]] = None
    decision_snapshot: Optional[Dict[str, Any]] = None
    resume_recommendation: Optional[Dict[str, Any]] = None
    extracted_requirements: Optional[Dict[str, Any]] = None
    evidence_mapping: Optional[List[Dict[str, Any]]] = None
    skills_recommendation: Optional[Dict[str, Any]] = None
    generated_content: Optional[Dict[str, Any]] = None
    question_answers: Optional[List[Dict[str, Any]]] = None
    warnings: Optional[List[str]] = None
    human_confirmation_required: Optional[List[Dict[str, Any]]] = None
    user_overrides: Optional[Dict[str, Any]] = None
    user_notes: Optional[str] = None
    engine_version: str
    prepared_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
