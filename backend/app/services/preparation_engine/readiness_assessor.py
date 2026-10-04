from typing import Tuple, List, Dict, Any, Optional
from app.models.decision import ApplicationDecision
from app.models.matching import MatchResult
from app.services.preparation_engine.models import (
    CandidateEvidenceItem,
    ApplicationQuestionAnswer,
    ReadinessStatus,
    ExtractedJobRequirements,
)


def assess_application_readiness(
    evidence_items: List[CandidateEvidenceItem],
    questions: List[ApplicationQuestionAnswer],
    extracted_reqs: ExtractedJobRequirements,
    decision: Optional[ApplicationDecision] = None,
    match_result: Optional[MatchResult] = None,
) -> Tuple[str, float, List[str], List[Dict[str, Any]], List[str]]:
    """
    Evaluates Application Readiness:
    - READY: Enough verified information exists to safely finalize application package.
    - READY_WITH_REVIEW: Materials prepared, but specific questions/salary require user confirmation.
    - BLOCKED: Critical qualification or seniority mismatch makes application unsafe/defenseless.

    Returns: (readiness_status, readiness_score, readiness_reasons, human_confirmation_required, warnings)
    """
    score = 100.0
    reasons: List[str] = []
    warnings: List[str] = []
    confirmations_required: List[Dict[str, Any]] = []

    # 1. Check for Critical Decision or Hard Requirement Blockers
    is_blocked = False

    if decision and decision.decision == "SKIP":
        is_blocked = True
        reasons.append(f"Blocked by Decision Engine: Job is marked SKIP ('{decision.reasons[0] if decision.reasons else 'Disqualified'}').")
        score = min(score, 35.0)

    if match_result and match_result.has_hard_mismatch:
        is_blocked = True
        warnings.append(f"Hard Requirement Warning: {match_result.hard_requirement_status}")
        for hw in (match_result.hard_requirement_warnings or []):
            msg = hw.get("message") if isinstance(hw, dict) else str(hw)
            warnings.append(msg)
            if "CRITICAL" in str(hw):
                reasons.append(f"Critical hard requirement mismatch: {msg}")
                score = min(score, 30.0)

    # 2. Check Candidate Evidence for Seniority or Major Missing Requirements
    missing_req_count = 0
    transferable_count = 0

    for item in evidence_items:
        if item.category == "experience" and item.match_type == "MISSING":
            is_blocked = True
            reasons.append(f"Seniority gap: {item.notes}")
            score -= 30.0
        elif item.category == "required_skill" and item.match_type == "MISSING":
            missing_req_count += 1
            score -= 10.0
        elif item.match_type == "TRANSFERABLE":
            transferable_count += 1
            score -= 3.0

    if missing_req_count > 3:
        is_blocked = True
        reasons.append(f"Multiple missing required skills ({missing_req_count} unverified technologies).")
        score -= 15.0

    # 3. Check Questions Requiring Human Confirmation
    for q in questions:
        if q.requires_human_confirmation and not q.confirmed_answer:
            confirmations_required.append({
                "question": q.question,
                "category": q.category,
                "proposed_answer": q.proposed_answer,
                "reason": q.evidence,
            })
            if q.category == "salary":
                warnings.append("Salary expectation: ₹3.5 LPA baseline floor requires explicit candidate confirmation.")
                score -= 8.0
            elif q.category in ["work_authorization", "sponsorship"]:
                warnings.append(f"{q.question}: Work authorization / sponsorship must be confirmed by candidate.")
                score -= 5.0
            else:
                score -= 3.0

    # 4. Final Status Determination
    score = max(0.0, min(100.0, score))

    if is_blocked or score < 45.0:
        status = ReadinessStatus.BLOCKED.value
        if not reasons:
            reasons.append("Application blocked due to significant qualification gaps or unresolved hard mismatches.")
    elif len(confirmations_required) > 0 or score < 85.0:
        status = ReadinessStatus.READY_WITH_REVIEW.value
        reasons.append(
            f"Application package prepared with {len(confirmations_required)} items requiring human confirmation "
            f"({', '.join([c['category'] for c in confirmations_required[:3]])})."
        )
    else:
        status = ReadinessStatus.READY.value
        reasons.append("Complete verified application package ready for human review.")

    return status, round(score, 1), reasons, confirmations_required, warnings
