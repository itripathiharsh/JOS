from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class ExecutionStartRequest(BaseModel):
    mode: Optional[str] = "MANUAL"  # MANUAL, ASSISTED, AUTOMATED
    source: Optional[str] = "generic_web"  # generic_web, manual, mock, etc.
    allow_force: Optional[bool] = False
    context: Optional[Dict[str, Any]] = None


class ExecutionResumeRequest(BaseModel):
    user_inputs: Dict[str, Any]  # action: confirm_fields, confirm_submitted, cancel; field_values: {field_name: value}
    context: Optional[Dict[str, Any]] = None


class ExecutionApproveRequest(BaseModel):
    context: Optional[Dict[str, Any]] = None


class ExecutionCancelRequest(BaseModel):
    reason: Optional[str] = "User cancelled execution"


class ApplicationExecutionResponse(BaseModel):
    id: str
    application_id: str
    job_id: str
    candidate_id: str
    preparation_id: Optional[str] = None
    attempt_number: int
    mode: str
    source: str
    status: str
    current_step: Optional[str] = None
    step_details: Optional[Dict[str, Any]] = None
    field_mappings: Optional[List[Dict[str, Any]]] = None
    blocker_reason: Optional[str] = None
    failure_reason: Optional[str] = None
    requires_user_action: bool
    user_action_prompt: Optional[str] = None
    submission_confirmed: bool
    confirmation_evidence: Optional[Dict[str, Any]] = None
    browser_metadata: Optional[Dict[str, Any]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationExecutionListResponse(BaseModel):
    items: List[ApplicationExecutionResponse]
    total: int
