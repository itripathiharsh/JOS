from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from intelligence.models import (
    CanonicalSkill,
    NormalizedRole,
    JobRequirements,
    CandidateData,
    DimensionEvaluation,
    MatchResultData,
    HardRequirementWarning,
    HardRequirementEvaluation,
)
from intelligence.normalization import normalize_skill, normalize_role
from intelligence.extractor import extract_job_requirements
from intelligence.candidate import extract_candidate_data_from_profile
from intelligence.engine import (
    match_job_against_candidate,
    evaluate_hard_requirements,
    ENGINE_VERSION,
)


class MatchResult:
    """Legacy compatibility class."""
    def __init__(self, score: float, reasons: list[str], fit_category: str):
        self.score = score
        self.reasons = reasons
        self.fit_category = fit_category


class JobAnalyzer(ABC):
    """
    Abstract interface for deterministic job analysis and matching against CandidateProfile.
    """

    @abstractmethod
    def analyze(self, job_data: Dict[str, Any], candidate_profile: Dict[str, Any]) -> MatchResultData:
        """Analyze fit score, dimensions, and explanations."""
        pass


class DeterministicJobAnalyzer(JobAnalyzer):
    """
    Production deterministic implementation of JobAnalyzer.
    Runs completely local, ₹0-cost, and explainable evaluation.
    """

    def analyze(self, job_data: Dict[str, Any], candidate_profile: Dict[str, Any]) -> MatchResultData:
        # Compatibility wrapper
        return match_job_against_candidate(job_data, candidate_profile)


__all__ = [
    "MatchResult",
    "JobAnalyzer",
    "DeterministicJobAnalyzer",
    "CanonicalSkill",
    "NormalizedRole",
    "JobRequirements",
    "CandidateData",
    "DimensionEvaluation",
    "MatchResultData",
    "HardRequirementWarning",
    "HardRequirementEvaluation",
    "normalize_skill",
    "normalize_role",
    "extract_job_requirements",
    "extract_candidate_data_from_profile",
    "evaluate_hard_requirements",
    "match_job_against_candidate",
    "ENGINE_VERSION",
]
