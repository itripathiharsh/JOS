from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class DecisionEvaluationResult:
    decision: str  # "APPLY", "REVIEW", "SKIP"
    confidence_score: float  # 0.0 to 1.0
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    reasons: List[str] = field(default_factory=list)
    supporting_factors: List[str] = field(default_factory=list)
    disqualifying_factors: List[str] = field(default_factory=list)
    review_reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
