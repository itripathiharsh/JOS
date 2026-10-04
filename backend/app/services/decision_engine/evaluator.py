from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.profile import CandidateProfile, CandidatePreference
from app.models.matching import MatchResult
from app.services.decision_engine.models import DecisionEvaluationResult
from app.services.decision_engine.rules import (
    check_application_history,
    check_duplicate_status,
    check_hard_requirements,
    check_candidate_preferences,
    check_role_relevance,
)


def evaluate_application_decision(
    job: Job,
    candidate: CandidateProfile,
    match_result: MatchResult,
    db: Optional[Session] = None,
) -> DecisionEvaluationResult:
    """
    Pure deterministic multi-dimensional application decision evaluation.
    Evaluates:
      1. Application History Gate (Already applied -> SKIP)
      2. Duplicate Status Gate (Duplicate -> SKIP; Possible Duplicate -> REVIEW)
      3. Hard Requirement Gate (Critical mismatch -> SKIP; Major mismatch -> SKIP/REVIEW)
      4. Candidate Preference Compatibility Gate (Work mode, employment, salary floor -> SKIP/REVIEW)
      5. Role Alignment & Match Score Gate (Low score / unrelated role -> SKIP)
      6. Quality & Synthesis (High match -> APPLY; Moderate/Ambiguous -> REVIEW)
    """
    reasons: List[str] = []
    supporting_factors: List[str] = []
    disqualifying_factors: List[str] = []
    review_reasons: List[str] = []

    # Retrieve candidate preference record
    pref: Optional[CandidatePreference] = candidate.preference_record

    # -------------------------------------------------------------
    # GATE 1: Application History Gate
    # -------------------------------------------------------------
    already_applied, app_reason, app_details = check_application_history(job, candidate, db)
    if already_applied:
        disqualifying_factors.append(app_reason or "Already applied to this canonical vacancy.")
        return DecisionEvaluationResult(
            decision="SKIP",
            confidence_score=1.0,
            risk_level="HIGH",
            reasons=[app_reason or "Candidate already submitted an application for this job."],
            disqualifying_factors=disqualifying_factors,
            supporting_factors=[],
            review_reasons=[],
            metadata={
                "gate": "application_history",
                "application_details": app_details,
                "job_id": job.id,
                "is_canonical": job.is_canonical,
            }
        )

    # -------------------------------------------------------------
    # GATE 2: Duplicate Status Gate (Step 6 Anti-Duplicate)
    # -------------------------------------------------------------
    is_duplicate, is_possible_duplicate, dup_reason = check_duplicate_status(job)
    if is_duplicate:
        disqualifying_factors.append(dup_reason or "Duplicate job record.")
        return DecisionEvaluationResult(
            decision="SKIP",
            confidence_score=1.0,
            risk_level="HIGH",
            reasons=[dup_reason or "Non-canonical duplicate record; evaluate canonical job instead."],
            disqualifying_factors=disqualifying_factors,
            supporting_factors=[],
            review_reasons=[],
            metadata={
                "gate": "duplicate_check",
                "duplicate_status": job.duplicate_status,
                "canonical_job_id": job.canonical_job_id,
            }
        )

    if is_possible_duplicate and dup_reason:
        review_reasons.append(dup_reason)

    # -------------------------------------------------------------
    # GATE 3: Hard Requirement Gate (Phase 4.1)
    # -------------------------------------------------------------
    is_critical, is_major, critical_reasons, major_reasons = check_hard_requirements(match_result)

    if is_critical:
        disqualifying_factors.extend(critical_reasons)
        return DecisionEvaluationResult(
            decision="SKIP",
            confidence_score=0.95,
            risk_level="HIGH",
            reasons=[critical_reasons[0]],
            disqualifying_factors=disqualifying_factors,
            supporting_factors=[],
            review_reasons=[],
            metadata={
                "gate": "hard_requirement_critical",
                "hard_requirement_status": match_result.hard_requirement_status,
                "warnings": match_result.hard_requirement_warnings,
            }
        )

    major_mismatch_needs_review = False
    if is_major:
        # Legitimate reason to reconsider: exceptionally high overall score (>= 80.0) with strong role score (>= 75.0)
        if match_result.overall_score >= 80.0 and match_result.role_score >= 75.0:
            major_mismatch_needs_review = True
            review_reasons.extend(major_reasons)
            supporting_factors.append(f"High overall match ({match_result.overall_score:.1f}%) warrants human review despite requirement warning.")
        else:
            disqualifying_factors.extend(major_reasons)
            return DecisionEvaluationResult(
                decision="SKIP",
                confidence_score=0.90,
                risk_level="HIGH",
                reasons=[major_reasons[0]],
                disqualifying_factors=disqualifying_factors,
                supporting_factors=[],
                review_reasons=[],
                metadata={
                    "gate": "hard_requirement_major",
                    "hard_requirement_status": match_result.hard_requirement_status,
                    "warnings": match_result.hard_requirement_warnings,
                }
            )

    # -------------------------------------------------------------
    # GATE 4: Candidate Preferences Gate
    # -------------------------------------------------------------
    pref_disqualifications, pref_reviews, pref_support = check_candidate_preferences(job, candidate, pref)
    if pref_disqualifications:
        disqualifying_factors.extend(pref_disqualifications)
        return DecisionEvaluationResult(
            decision="SKIP",
            confidence_score=0.90,
            risk_level="HIGH",
            reasons=[pref_disqualifications[0]],
            disqualifying_factors=disqualifying_factors,
            supporting_factors=pref_support,
            review_reasons=pref_reviews,
            metadata={
                "gate": "candidate_preferences",
                "disqualifications": pref_disqualifications,
            }
        )

    review_reasons.extend(pref_reviews)
    supporting_factors.extend(pref_support)

    # -------------------------------------------------------------
    # GATE 5: Role Relevance Gate (Phase B, C, D)
    # -------------------------------------------------------------
    norm_role, role_disqualifier, role_review_reason, role_supporting = check_role_relevance(
        job=job,
        match_result=match_result,
        candidate=candidate,
        pref=pref,
    )

    if norm_role.relevance_tier == "UNRELATED":
        disq = role_disqualifier or f"Role '{job.title}' is fundamentally outside candidate's target career families."
        disqualifying_factors.append(disq)
        return DecisionEvaluationResult(
            decision="SKIP",
            confidence_score=0.95,
            risk_level="HIGH",
            reasons=[disq],
            disqualifying_factors=disqualifying_factors,
            supporting_factors=[],
            review_reasons=[],
            metadata={
                "gate": "role_relevance_unrelated",
                "role_relevance_tier": norm_role.relevance_tier,
                "role_family": norm_role.role_family,
                "role_concept": norm_role.concept,
                "role_score": norm_role.score,
            }
        )

    if role_review_reason:
        review_reasons.append(role_review_reason)
    if role_supporting:
        supporting_factors.append(role_supporting)

    # -------------------------------------------------------------
    # GATE 6: Overall Match Score & Category Gate
    # -------------------------------------------------------------
    if match_result.fit_category == "LOW_RELEVANCE" or match_result.overall_score < 45.0:
        disq = f"Insufficient match score ({match_result.overall_score:.1f}% fit, category: {match_result.fit_category})."
        disqualifying_factors.append(disq)
        return DecisionEvaluationResult(
            decision="SKIP",
            confidence_score=0.90,
            risk_level="HIGH",
            reasons=[disq],
            disqualifying_factors=disqualifying_factors,
            supporting_factors=[],
            review_reasons=[],
            metadata={
                "gate": "match_score_low",
                "overall_score": match_result.overall_score,
                "fit_category": match_result.fit_category,
                "role_relevance_tier": norm_role.relevance_tier,
            }
        )

    if match_result.role_score < 40.0:
        disq = f"Low role alignment: Role score is only {match_result.role_score:.1f}%."
        disqualifying_factors.append(disq)
        return DecisionEvaluationResult(
            decision="SKIP",
            confidence_score=0.90,
            risk_level="HIGH",
            reasons=[disq],
            disqualifying_factors=disqualifying_factors,
            supporting_factors=[],
            review_reasons=[],
            metadata={
                "gate": "role_score_low",
                "role_score": match_result.role_score,
                "role_relevance_tier": norm_role.relevance_tier,
            }
        )

    # -------------------------------------------------------------
    # GATE 7: Decision Synthesis (APPLY vs REVIEW vs SKIP)
    # -------------------------------------------------------------
    # Supporting factors from MatchResult
    supporting_factors.append(f"{match_result.overall_score:.1f}% overall match score ({match_result.fit_category})")
    supporting_factors.append(f"Role alignment: {match_result.role_score:.1f}% for '{job.title}'")

    if not match_result.has_hard_mismatch and match_result.hard_requirement_status == "PASSED":
        supporting_factors.append("All hard requirements satisfied without warnings.")

    if job.is_canonical and job.duplicate_status == "canonical":
        supporting_factors.append("Canonical vacancy record with direct application link.")

    # 1. Condition for REVIEW: Possible duplicate
    if is_possible_duplicate:
        reasons.append("Flagged as possible cross-source duplicate; human confirmation recommended before applying.")
        return DecisionEvaluationResult(
            decision="REVIEW",
            confidence_score=0.85,
            risk_level="MEDIUM",
            reasons=reasons,
            supporting_factors=supporting_factors,
            disqualifying_factors=[],
            review_reasons=review_reasons,
            metadata={
                "reason_type": "possible_duplicate",
                "overall_score": match_result.overall_score,
                "duplicate_status": job.duplicate_status,
                "role_relevance_tier": norm_role.relevance_tier,
            }
        )

    # 2. Condition for REVIEW: Major requirement mismatch with strong overall score
    if major_mismatch_needs_review:
        reasons.append(f"Strong overall score ({match_result.overall_score:.1f}%), but has major requirement warning needing human judgment.")
        return DecisionEvaluationResult(
            decision="REVIEW",
            confidence_score=0.80,
            risk_level="MEDIUM",
            reasons=reasons,
            supporting_factors=supporting_factors,
            disqualifying_factors=[],
            review_reasons=review_reasons,
            metadata={
                "reason_type": "major_mismatch_borderline",
                "overall_score": match_result.overall_score,
                "warnings": match_result.hard_requirement_warnings,
                "role_relevance_tier": norm_role.relevance_tier,
            }
        )

    # 3. Condition for REVIEW: Low data completeness or insufficient data
    if match_result.data_completeness_level == "LOW" or match_result.fit_category == "INSUFFICIENT_DATA":
        reasons.append("Job description lacks sufficient detail or has incomplete requirements; manual review recommended.")
        return DecisionEvaluationResult(
            decision="REVIEW",
            confidence_score=0.80,
            risk_level="MEDIUM",
            reasons=reasons,
            supporting_factors=supporting_factors,
            disqualifying_factors=[],
            review_reasons=review_reasons,
            metadata={
                "reason_type": "insufficient_data",
                "completeness": match_result.data_completeness,
                "role_relevance_tier": norm_role.relevance_tier,
            }
        )

    # 4. Condition for REVIEW: Role is TRANSFERABLE (General Software, Fullstack, DevOps, QA)
    # Never auto-apply to transferable roles outside target tracks!
    if norm_role.relevance_tier == "TRANSFERABLE":
        reasons.append(
            f"Transferable software role ({norm_role.concept}) with {match_result.overall_score:.1f}% fit. "
            f"Human review recommended to verify alignment with career goals."
        )
        return DecisionEvaluationResult(
            decision="REVIEW",
            confidence_score=0.80,
            risk_level="MEDIUM",
            reasons=reasons,
            supporting_factors=supporting_factors,
            disqualifying_factors=[],
            review_reasons=review_reasons,
            metadata={
                "reason_type": "transferable_role",
                "overall_score": match_result.overall_score,
                "role_relevance_tier": norm_role.relevance_tier,
                "role_concept": norm_role.concept,
            }
        )

    # 5. Condition for REVIEW: Ambiguous or Unknown Role Title
    if norm_role.relevance_tier == "UNKNOWN":
        reasons.append(f"Ambiguous or unspecified job title ('{job.title}'); manual verification of role responsibilities required.")
        return DecisionEvaluationResult(
            decision="REVIEW",
            confidence_score=0.75,
            risk_level="MEDIUM",
            reasons=reasons,
            supporting_factors=supporting_factors,
            disqualifying_factors=[],
            review_reasons=review_reasons,
            metadata={
                "reason_type": "unknown_role_title",
                "overall_score": match_result.overall_score,
                "role_relevance_tier": norm_role.relevance_tier,
            }
        )

    # 6. Condition for REVIEW: Moderate match on DIRECT or ADJACENT role
    is_direct = (norm_role.relevance_tier == "DIRECT")
    is_adjacent = (norm_role.relevance_tier == "ADJACENT")

    needs_moderate_review = False
    if is_direct and (match_result.overall_score < 70.0 or match_result.role_score < 65.0):
        needs_moderate_review = True
    elif is_adjacent and (match_result.overall_score < 75.0 or match_result.role_score < 60.0):
        needs_moderate_review = True
    elif match_result.fit_category not in ["HIGH_RELEVANCE", "GOOD_RELEVANCE"]:
        needs_moderate_review = True

    if needs_moderate_review:
        reasons.append(f"Moderate match relevance ({match_result.overall_score:.1f}% fit, role: {match_result.role_score:.1f}%). Human review advised before application.")
        return DecisionEvaluationResult(
            decision="REVIEW",
            confidence_score=0.75,
            risk_level="MEDIUM",
            reasons=reasons,
            supporting_factors=supporting_factors,
            disqualifying_factors=[],
            review_reasons=review_reasons,
            metadata={
                "reason_type": "moderate_score",
                "overall_score": match_result.overall_score,
                "role_score": match_result.role_score,
                "role_relevance_tier": norm_role.relevance_tier,
            }
        )

    # 7. Condition for APPLY: Strong overall score (>= 70 for DIRECT, >= 75 for ADJACENT),
    # solid role score, verified target or adjacent specialization, no blockers
    tier_label = "direct target role" if is_direct else "adjacent specialization"
    reasons.append(f"Strong {match_result.overall_score:.1f}% overall match for {job.title} at {job.company} ({tier_label}).")
    reasons.append("No hard requirement mismatches detected.")
    if pref_support:
        reasons.append(pref_support[0])

    return DecisionEvaluationResult(
        decision="APPLY",
        confidence_score=0.90,
        risk_level="LOW",
        reasons=reasons,
        supporting_factors=supporting_factors,
        disqualifying_factors=[],
        review_reasons=review_reasons,
        metadata={
            "reason_type": "strong_match",
            "overall_score": match_result.overall_score,
            "role_score": match_result.role_score,
            "fit_category": match_result.fit_category,
            "work_mode": job.work_mode,
            "role_relevance_tier": norm_role.relevance_tier,
            "role_family": norm_role.role_family,
            "role_concept": norm_role.concept,
        }
    )
