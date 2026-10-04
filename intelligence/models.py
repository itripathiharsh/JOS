from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set


@dataclass
class CanonicalSkill:
    source_name: str
    canonical_name: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "source": self.source_name,
            "canonical": self.canonical_name,
        }


@dataclass
class NormalizedRole:
    concept: str
    target_role: Optional[str]
    priority_rank: Optional[int]  # 1 to N, or None
    fit_level: str  # STRONG, ADJACENT, MODERATE, WEAK, UNKNOWN, UNRELATED
    score: float  # 0.0 to 100.0
    explanation: str
    role_family: str = "UNKNOWN"
    relevance_tier: str = "UNKNOWN"  # DIRECT, ADJACENT, TRANSFERABLE, UNRELATED, UNKNOWN
    is_target_career_aligned: bool = False


@dataclass
class JobRequirements:
    raw_title: str
    role: str
    normalized_role: Optional[NormalizedRole] = None
    required_skills: List[CanonicalSkill] = field(default_factory=list)
    preferred_skills: List[CanonicalSkill] = field(default_factory=list)
    minimum_experience: Optional[float] = None
    maximum_experience: Optional[float] = None
    experience_text: Optional[str] = None
    location: Optional[str] = None
    work_modes: List[str] = field(default_factory=list)
    employment_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = "USD"
    education_requirements: List[str] = field(default_factory=list)


@dataclass
class CandidateData:
    id: str
    name: str
    target_roles: List[str] = field(default_factory=list)
    role_priority: List[str] = field(default_factory=list)
    preferred_locations: List[str] = field(default_factory=list)
    location_priority: List[str] = field(default_factory=list)
    work_modes: List[str] = field(default_factory=list)
    minimum_salary: Optional[float] = None
    salary_currency: str = "INR"
    salary_status: str = "NEEDS_CONFIRMATION"
    actual_experience_years: float = 0.0
    experience_records_summary: List[Dict[str, Any]] = field(default_factory=list)
    skills: List[CanonicalSkill] = field(default_factory=list)
    skill_names_canonical: Set[str] = field(default_factory=set)
    educations: List[Dict[str, Any]] = field(default_factory=list)
    employment_types: List[str] = field(default_factory=list)
    relocation_allowed: bool = True


@dataclass
class HardRequirementWarning:
    category: str  # experience, required_skills, location, education
    severity: str  # CRITICAL, MAJOR, MINOR, INFORMATIONAL
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class HardRequirementEvaluation:
    has_critical_mismatch: bool = False
    has_major_mismatch: bool = False
    status: str = "PASSED"  # PASSED, WARNING, MISMATCH
    warnings: List[HardRequirementWarning] = field(default_factory=list)
    experience_mismatch: Optional[Dict[str, Any]] = None
    required_skill_mismatches: List[str] = field(default_factory=list)
    location_mismatch: Optional[Dict[str, Any]] = None
    education_mismatch: Optional[Dict[str, Any]] = None
    score_cap: Optional[float] = None
    max_fit_category: Optional[str] = None
    explanation: Optional[str] = None


@dataclass
class DimensionEvaluation:
    name: str
    status: str  # FIT, PARTIAL, MISMATCH, UNKNOWN, STRONG, MODERATE, WEAK, etc.
    score: float  # 0.0 to 100.0
    weight: float  # base weight (e.g. 0.30)
    is_known: bool  # whether the dimension had concrete data to evaluate
    explanation: str
    concerns: List[str] = field(default_factory=list)


@dataclass
class MatchResultData:
    engine_version: str
    overall_score: float
    fit_category: str  # HIGH_RELEVANCE, GOOD_RELEVANCE, PARTIAL_RELEVANCE, LOW_RELEVANCE, INSUFFICIENT_DATA
    role_score: float
    skill_score: float
    experience_score: float
    location_score: float
    work_mode_score: float
    salary_score: float
    education_score: float
    employment_type_score: float
    matched_required_skills: List[Dict[str, str]] = field(default_factory=list)
    missing_required_skills: List[str] = field(default_factory=list)
    matched_preferred_skills: List[Dict[str, str]] = field(default_factory=list)
    missing_preferred_skills: List[str] = field(default_factory=list)
    dimension_details: Dict[str, Any] = field(default_factory=dict)
    concerns: List[str] = field(default_factory=list)
    explanations: List[str] = field(default_factory=list)
    data_completeness: float = 100.0
    data_completeness_level: str = "HIGH"

    # Phase 4.1: Hard Requirement Evaluation
    hard_requirement_status: str = "PASSED"  # PASSED, WARNING, MISMATCH
    hard_requirement_warnings: List[Dict[str, Any]] = field(default_factory=list)
    has_hard_mismatch: bool = False
