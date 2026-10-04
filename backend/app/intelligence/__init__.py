import sys
import os

workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from intelligence import (
    MatchResult,
    JobAnalyzer,
    DeterministicJobAnalyzer,
    CanonicalSkill,
    NormalizedRole,
    JobRequirements,
    CandidateData,
    DimensionEvaluation,
    MatchResultData,
    HardRequirementWarning,
    HardRequirementEvaluation,
    normalize_skill,
    normalize_role,
    extract_job_requirements,
    extract_candidate_data_from_profile,
    evaluate_hard_requirements,
    match_job_against_candidate,
    ENGINE_VERSION,
)

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
