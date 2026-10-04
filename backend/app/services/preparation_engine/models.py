from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class EvidenceMatchType(str, Enum):
    DIRECT = "DIRECT"
    TRANSFERABLE = "TRANSFERABLE"
    WEAK = "WEAK"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class ReadinessStatus(str, Enum):
    READY = "READY"
    READY_WITH_REVIEW = "READY_WITH_REVIEW"
    BLOCKED = "BLOCKED"


@dataclass
class CandidateEvidenceItem:
    requirement: str
    category: str  # "experience", "required_skill", "preferred_skill", "education", "location", "responsibility"
    match_type: str  # DIRECT, TRANSFERABLE, WEAK, MISSING, UNKNOWN
    candidate_evidence: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement": self.requirement,
            "category": self.category,
            "match_type": self.match_type,
            "candidate_evidence": self.candidate_evidence,
            "source": self.source,
            "notes": self.notes,
        }


@dataclass
class ExtractedJobRequirements:
    required_qualifications: List[str] = field(default_factory=list)
    preferred_qualifications: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    required_degree: Optional[str] = None
    required_location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "required_qualifications": self.required_qualifications,
            "preferred_qualifications": self.preferred_qualifications,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "responsibilities": self.responsibilities,
            "keywords": self.keywords,
            "min_experience_years": self.min_experience_years,
            "max_experience_years": self.max_experience_years,
            "required_degree": self.required_degree,
            "required_location": self.required_location,
            "work_mode": self.work_mode,
            "employment_type": self.employment_type,
        }


@dataclass
class ResumeRecommendation:
    recommended_document_id: Optional[str]
    document_name: str
    file_path: str
    why_recommended: str
    sufficiency_assessment: str
    gaps_identified: List[str] = field(default_factory=list)
    keep_points: List[str] = field(default_factory=list)
    emphasize_points: List[str] = field(default_factory=list)
    deemphasize_points: List[str] = field(default_factory=list)
    add_if_true_points: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_document_id": self.recommended_document_id,
            "document_name": self.document_name,
            "file_path": self.file_path,
            "why_recommended": self.why_recommended,
            "sufficiency_assessment": self.sufficiency_assessment,
            "gaps_identified": self.gaps_identified,
            "keep_points": self.keep_points,
            "emphasize_points": self.emphasize_points,
            "deemphasize_points": self.deemphasize_points,
            "add_if_true_points": self.add_if_true_points,
        }


@dataclass
class SkillsRecommendation:
    strong_match: List[str] = field(default_factory=list)
    supporting_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    do_not_claim: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strong_match": self.strong_match,
            "supporting_skills": self.supporting_skills,
            "missing_skills": self.missing_skills,
            "do_not_claim": self.do_not_claim,
        }


@dataclass
class GeneratedContent:
    application_summary: str
    cover_letter: str
    short_message: str
    claim_safety_audit: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_summary": self.application_summary,
            "cover_letter": self.cover_letter,
            "short_message": self.short_message,
            "claim_safety_audit": self.claim_safety_audit,
        }


@dataclass
class ApplicationQuestionAnswer:
    question: str
    category: str
    proposed_answer: Optional[str]
    answer_source: str
    confidence: str  # HIGH, MEDIUM, LOW
    evidence: str
    requires_human_confirmation: bool
    confirmed_answer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "category": self.category,
            "proposed_answer": self.proposed_answer,
            "answer_source": self.answer_source,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "requires_human_confirmation": self.requires_human_confirmation,
            "confirmed_answer": self.confirmed_answer,
        }


@dataclass
class ApplicationPreparationPackage:
    id: str
    application_id: Optional[str]
    job_id: str
    candidate_id: str
    version: int
    readiness_status: str
    readiness_score: float
    readiness_reasons: List[str]
    job_snapshot: Dict[str, Any]
    decision_snapshot: Dict[str, Any]
    resume_recommendation: Dict[str, Any]
    extracted_requirements: Dict[str, Any]
    evidence_mapping: List[Dict[str, Any]]
    skills_recommendation: Dict[str, Any]
    generated_content: Dict[str, Any]
    question_answers: List[Dict[str, Any]]
    warnings: List[str]
    human_confirmation_required: List[Dict[str, Any]]
    engine_version: str
    prepared_at: str
    user_overrides: Optional[Dict[str, Any]] = None
    user_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "job_id": self.job_id,
            "candidate_id": self.candidate_id,
            "version": self.version,
            "readiness_status": self.readiness_status,
            "readiness_score": self.readiness_score,
            "readiness_reasons": self.readiness_reasons,
            "job_snapshot": self.job_snapshot,
            "decision_snapshot": self.decision_snapshot,
            "resume_recommendation": self.resume_recommendation,
            "extracted_requirements": self.extracted_requirements,
            "evidence_mapping": self.evidence_mapping,
            "skills_recommendation": self.skills_recommendation,
            "generated_content": self.generated_content,
            "question_answers": self.question_answers,
            "warnings": self.warnings,
            "human_confirmation_required": self.human_confirmation_required,
            "engine_version": self.engine_version,
            "prepared_at": self.prepared_at,
            "user_overrides": self.user_overrides,
            "user_notes": self.user_notes,
        }
