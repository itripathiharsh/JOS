import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, JSON, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from typing import List, Optional, Any, Dict


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Structured JSON for preferences and social links
    preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
    links: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    preference_record: Mapped[Optional["CandidatePreference"]] = relationship("CandidatePreference", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    educations: Mapped[List["Education"]] = relationship("Education", back_populates="candidate", cascade="all, delete-orphan")
    experiences: Mapped[List["Experience"]] = relationship("Experience", back_populates="candidate", cascade="all, delete-orphan")
    skills: Mapped[List["Skill"]] = relationship("Skill", back_populates="candidate", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="candidate", cascade="all, delete-orphan")
    certifications: Mapped[List["Certification"]] = relationship("Certification", back_populates="candidate", cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="candidate", cascade="all, delete-orphan")
    match_results: Mapped[List["MatchResult"]] = relationship("MatchResult", back_populates="candidate", cascade="all, delete-orphan")
    decisions: Mapped[List["ApplicationDecision"]] = relationship("ApplicationDecision", back_populates="candidate", cascade="all, delete-orphan")
    preparations: Mapped[List["ApplicationPreparation"]] = relationship("ApplicationPreparation", back_populates="candidate", cascade="all, delete-orphan")
    executions: Mapped[List["ApplicationExecution"]] = relationship("ApplicationExecution", back_populates="candidate", cascade="all, delete-orphan")



class Education(Base):
    __tablename__ = "educations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(255), nullable=False)
    field: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CONFIRMED")  # CONFIRMED, USER_PROVIDED, INFERRED

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="educations")


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current: Mapped[bool] = mapped_column(Boolean, default=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    responsibilities: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    achievements: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    technologies: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CONFIRMED")  # CONFIRMED, USER_PROVIDED, INFERRED

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="experiences")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    proficiency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CONFIRMED")  # CONFIRMED, USER_PROVIDED, INFERRED

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="skills")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technologies: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    repo_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    demo_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CONFIRMED")  # CONFIRMED, USER_PROVIDED, INFERRED

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="projects")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuing_organization: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    expiry_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    credential_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    credential_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    document_ref: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CONFIRMED")  # CONFIRMED, USER_PROVIDED, INFERRED

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="certifications")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # resume, cover_letter, certificate, other
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # storage reference
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="documents")


class CandidatePreference(Base):
    __tablename__ = "candidate_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    target_roles: Mapped[List[str]] = mapped_column(JSON, default=list)
    role_priority: Mapped[List[str]] = mapped_column(JSON, default=list)
    preferred_locations: Mapped[List[str]] = mapped_column(JSON, default=list)
    location_priority: Mapped[List[str]] = mapped_column(JSON, default=list)
    work_modes: Mapped[List[str]] = mapped_column(JSON, default=list)
    minimum_salary: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    salary_status: Mapped[str] = mapped_column(String(50), default="NEEDS_CONFIRMATION")  # NEEDS_CONFIRMATION, CONFIRMED
    experience_preference: Mapped[str] = mapped_column(String(50), default="0-1 years")
    employment_types: Mapped[List[str]] = mapped_column(JSON, default=list)
    relocation_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    startup_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    service_company_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    product_company_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    internship_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    contract_allowed: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="preference_record")
