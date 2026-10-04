from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class LifecycleStage(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PREPARED = "PREPARED"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_USER = "AWAITING_USER"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    SCREENING = "SCREENING"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"
    NO_RESPONSE = "NO_RESPONSE"


class OutcomeCategory(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    PENDING = "pending"
    UNKNOWN = "unknown"


class OutcomeProvenance(str, Enum):
    USER_CONFIRMED = "USER_CONFIRMED"
    SYSTEM_DETECTED = "SYSTEM_DETECTED"
    IMPORTED = "IMPORTED"
    UNKNOWN = "UNKNOWN"


class RejectionCategory(str, Enum):
    EXPERIENCE_GAP = "experience_gap"
    MISSING_SKILL = "missing_skill"
    LOCATION = "location"
    SALARY = "salary"
    ROLE_MISMATCH = "role_mismatch"
    RESUME_ISSUE = "resume_issue"
    INTERVIEW_PERFORMANCE = "interview_performance"
    TECHNICAL_ASSESSMENT = "technical_assessment"
    POSITION_CLOSED = "position_closed"
    UNKNOWN = "unknown"
    OTHER = "other"


class NoteCategory(str, Enum):
    GENERAL = "general"
    RECRUITER = "recruiter"
    INTERVIEW = "interview"
    COMPENSATION = "compensation"
    REFERRAL = "referral"
    FOLLOW_UP = "follow_up"


class TimelineEventType(str, Enum):
    APPLICATION_CREATED = "APPLICATION_CREATED"
    DECISION_EVALUATED = "DECISION_EVALUATED"
    PREPARATION_GENERATED = "PREPARATION_GENERATED"
    PREPARATION_UPDATED = "PREPARATION_UPDATED"
    EXECUTION_ATTEMPT = "EXECUTION_ATTEMPT"
    HUMAN_INTERVENTION = "HUMAN_INTERVENTION"
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    STATUS_CHANGED = "STATUS_CHANGED"
    USER_NOTE_ADDED = "USER_NOTE_ADDED"
    USER_OVERRIDE_RECORDED = "USER_OVERRIDE_RECORDED"
    OUTCOME_RECORDED = "OUTCOME_RECORDED"


class TimelineItem(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    title: str
    description: Optional[str] = None
    actor: str = "system"  # user, system, recruiter, import
    provenance: str = "SYSTEM_DETECTED"  # USER_CONFIRMED, SYSTEM_DETECTED, IMPORTED, UNKNOWN
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidateSnapshot(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    target_roles: List[str] = Field(default_factory=list)
    total_experience_years: float = 2.0
    skills: List[str] = Field(default_factory=list)
    educations: List[Dict[str, Any]] = Field(default_factory=list)
    experiences: List[Dict[str, Any]] = Field(default_factory=list)
    captured_at: datetime


class JobSnapshot(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = "USD"
    application_url: Optional[str] = None
    source: str
    is_canonical: bool = True
    canonical_job_id: Optional[str] = None
    captured_at: datetime


class DecisionSnapshot(BaseModel):
    decision: str  # APPLY, REVIEW, SKIP
    confidence_score: float = 1.0
    risk_level: str = "LOW"
    reasons: List[str] = Field(default_factory=list)
    supporting_factors: List[str] = Field(default_factory=list)
    disqualifying_factors: List[str] = Field(default_factory=list)
    review_reasons: List[str] = Field(default_factory=list)
    match_score: Optional[float] = None
    engine_version: str = "1.0.0"
    captured_at: datetime


class ArtifactsSnapshot(BaseModel):
    resume_name: Optional[str] = None
    resume_path: Optional[str] = None
    resume_version: Optional[str] = None
    cover_letter: Optional[str] = None
    application_message: Optional[str] = None
    screening_answers: List[Dict[str, Any]] = Field(default_factory=list)
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    captured_at: datetime


class ConversionMetric(BaseModel):
    numerator: int
    denominator: int
    rate: float  # 0.0 to 100.0%
    is_statistically_significant: bool = False
    warning: Optional[str] = None
