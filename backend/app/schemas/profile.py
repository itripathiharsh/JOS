from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==========================================
# Education Schemas
# ==========================================
class EducationBase(BaseModel):
    institution: str
    degree: str
    field: str
    start_date: str
    end_date: Optional[str] = None
    grade: Optional[str] = None
    location: Optional[str] = None
    details: Optional[str] = None
    status: Optional[str] = "CONFIRMED"  # CONFIRMED, USER_PROVIDED, INFERRED


class EducationCreate(EducationBase):
    pass


class EducationUpdate(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    grade: Optional[str] = None
    location: Optional[str] = None
    details: Optional[str] = None
    status: Optional[str] = None


class EducationResponse(EducationBase):
    id: str
    candidate_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Experience Schemas
# ==========================================
class ExperienceBase(BaseModel):
    company: str
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    current: bool = False
    location: Optional[str] = None
    employment_type: Optional[str] = None
    responsibilities: Optional[List[str]] = Field(default_factory=list)
    achievements: Optional[List[str]] = Field(default_factory=list)
    technologies: Optional[str] = None
    status: Optional[str] = "CONFIRMED"  # CONFIRMED, USER_PROVIDED, INFERRED


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    current: Optional[bool] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    achievements: Optional[List[str]] = None
    technologies: Optional[str] = None
    status: Optional[str] = None


class ExperienceResponse(ExperienceBase):
    id: str
    candidate_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Skill Schemas
# ==========================================
class SkillBase(BaseModel):
    name: str
    category: Optional[str] = None
    proficiency: Optional[str] = None
    status: Optional[str] = "CONFIRMED"  # CONFIRMED, USER_PROVIDED, INFERRED


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    proficiency: Optional[str] = None
    status: Optional[str] = None


class SkillResponse(SkillBase):
    id: str
    candidate_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Project Schemas
# ==========================================
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: Optional[str] = None
    url: Optional[str] = None
    role: Optional[str] = None
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = "CONFIRMED"  # CONFIRMED, USER_PROVIDED, INFERRED


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[str] = None
    url: Optional[str] = None
    role: Optional[str] = None
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: str
    candidate_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Certification Schemas
# ==========================================
class CertificationBase(BaseModel):
    name: str
    issuing_organization: str
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    source_url: Optional[str] = None
    document_ref: Optional[str] = None
    status: Optional[str] = "CONFIRMED"  # CONFIRMED, USER_PROVIDED, INFERRED


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(BaseModel):
    name: Optional[str] = None
    issuing_organization: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    source_url: Optional[str] = None
    document_ref: Optional[str] = None
    status: Optional[str] = None


class CertificationResponse(CertificationBase):
    id: str
    candidate_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Document Schemas
# ==========================================
class DocumentBase(BaseModel):
    name: str
    type: str  # resume, cover_letter, certificate, other
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    source: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: str
    candidate_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Candidate Preference Schemas
# ==========================================
class CandidatePreferenceBase(BaseModel):
    target_roles: List[str] = Field(default_factory=list)
    role_priority: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    location_priority: List[str] = Field(default_factory=list)
    work_modes: List[str] = Field(default_factory=list)
    minimum_salary: Optional[float] = None
    currency: str = "INR"
    salary_status: str = "NEEDS_CONFIRMATION"  # NEEDS_CONFIRMATION, CONFIRMED
    experience_preference: str = "0-1 years"
    employment_types: List[str] = Field(default_factory=list)
    relocation_allowed: bool = True
    startup_allowed: bool = True
    service_company_allowed: bool = True
    product_company_allowed: bool = True
    internship_allowed: bool = True
    contract_allowed: bool = True


class CandidatePreferenceCreate(CandidatePreferenceBase):
    pass


class CandidatePreferenceUpdate(BaseModel):
    target_roles: Optional[List[str]] = None
    role_priority: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    location_priority: Optional[List[str]] = None
    work_modes: Optional[List[str]] = None
    minimum_salary: Optional[float] = None
    currency: Optional[str] = None
    salary_status: Optional[str] = None
    experience_preference: Optional[str] = None
    employment_types: Optional[List[str]] = None
    relocation_allowed: Optional[bool] = None
    startup_allowed: Optional[bool] = None
    service_company_allowed: Optional[bool] = None
    product_company_allowed: Optional[bool] = None
    internship_allowed: Optional[bool] = None
    contract_allowed: Optional[bool] = None


class CandidatePreferenceResponse(CandidatePreferenceBase):
    id: str
    candidate_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Profile Completeness Schemas
# ==========================================
class ProfileCompletenessCriterion(BaseModel):
    criterion: str
    is_required: bool
    weight: int
    met: bool
    detail: str


class ProfileCompletenessResponse(BaseModel):
    score: int
    level: str  # Incomplete (<60), Good (60-84), Complete (85-100)
    missing_required: List[str]
    missing_optional: List[str]
    details: List[ProfileCompletenessCriterion]


# ==========================================
# Candidate Profile Schemas
# ==========================================
class CandidateProfileBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    links: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CandidateProfileCreate(CandidateProfileBase):
    educations: Optional[List[EducationCreate]] = None
    experiences: Optional[List[ExperienceCreate]] = None
    skills: Optional[List[SkillCreate]] = None
    projects: Optional[List[ProjectCreate]] = None
    certifications: Optional[List[CertificationCreate]] = None
    preference_record: Optional[CandidatePreferenceCreate] = None


class CandidateProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    links: Optional[Dict[str, Any]] = None
    educations: Optional[List[EducationCreate]] = None
    experiences: Optional[List[ExperienceCreate]] = None
    skills: Optional[List[SkillCreate]] = None
    projects: Optional[List[ProjectCreate]] = None
    certifications: Optional[List[CertificationCreate]] = None
    preference_record: Optional[CandidatePreferenceUpdate] = None


class CandidateProfileResponse(CandidateProfileBase):
    id: str
    created_at: datetime
    updated_at: datetime
    educations: List[EducationResponse] = Field(default_factory=list)
    experiences: List[ExperienceResponse] = Field(default_factory=list)
    skills: List[SkillResponse] = Field(default_factory=list)
    projects: List[ProjectResponse] = Field(default_factory=list)
    certifications: List[CertificationResponse] = Field(default_factory=list)
    documents: List[DocumentResponse] = Field(default_factory=list)
    preference_record: Optional[CandidatePreferenceResponse] = None
    completeness: Optional[ProfileCompletenessResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Resume Ingest Schemas
# ==========================================
class ResumeIngestResponse(BaseModel):
    success: bool
    message: str
    candidate: Dict[str, Any]
    provenance_summary: Dict[str, int]
    educations: List[Dict[str, Any]]
    experiences: List[Dict[str, Any]]
    skills: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]
    certifications: List[Dict[str, Any]]
    preferences: Dict[str, Any]
    documents: List[Dict[str, Any]]
    completeness: ProfileCompletenessResponse
