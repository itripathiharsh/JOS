from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.job import Job
from app.models.profile import CandidateProfile, CandidatePreference
from app.models.matching import MatchResult
from app.models.application import Application
from intelligence.normalization import normalize_role
from intelligence.models import NormalizedRole


def check_application_history(
    job: Job,
    candidate: CandidateProfile,
    db: Optional[Session] = None,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Checks if candidate has already applied to this job or its canonical sibling.
    Returns (already_applied: bool, reason: Optional[str], details: Optional[Dict]).
    """
    if db is None:
        return False, None, None

    # Check for direct job match or canonical sibling match
    job_ids = [job.id] if job.id else []
    if job.canonical_job_id:
        job_ids.append(job.canonical_job_id)

    # Also check if this job is canonical, did we apply to any duplicate?
    if job.is_canonical and job.id:
        dup_ids = [row[0] for row in db.query(Job.id).filter(Job.canonical_job_id == job.id).all()]
        job_ids.extend(dup_ids)

    job_ids = [jid for jid in job_ids if jid]
    if not job_ids:
        return False, None, None

    existing_app = db.query(Application).filter(
        Application.candidate_id == candidate.id,
        Application.job_id.in_(job_ids),
    ).first()


    if existing_app:
        status_str = existing_app.status or "active"
        applied_time = existing_app.applied_at or existing_app.created_at
        time_str = applied_time.strftime("%Y-%m-%d") if applied_time else "previously"
        return (
            True,
            f"Candidate already has an existing application record ({status_str}) tracked on {time_str}.",
            {
                "application_id": existing_app.id,
                "status": existing_app.status,
                "applied_at": time_str,
            }
        )

    return False, None, None


def check_duplicate_status(job: Job) -> Tuple[bool, bool, Optional[str]]:
    """
    Checks job duplicate status from Step 6.
    Returns (is_duplicate: bool, is_possible_duplicate: bool, reason: Optional[str]).
    """
    if job.duplicate_status == "duplicate" or not job.is_canonical:
        canon_id = job.canonical_job_id or "unknown"
        return (
            True,
            False,
            f"Non-canonical duplicate record of canonical job {canon_id}. Do not duplicate applications.",
        )

    if job.duplicate_status == "possible_duplicate":
        return (
            False,
            True,
            "Flagged as a possible cross-source duplicate; human verification recommended before applying.",
        )

    return False, False, None


def check_hard_requirements(
    match_result: MatchResult,
) -> Tuple[bool, bool, List[str], List[str]]:
    """
    Evaluates hard requirement signals from Phase 4.1.
    Returns (is_critical: bool, is_major: bool, critical_reasons: List[str], major_reasons: List[str]).
    """
    critical_reasons: List[str] = []
    major_reasons: List[str] = []

    warnings = match_result.hard_requirement_warnings or []
    for w in warnings:
        sev = str(w.get("severity", "")).upper()
        msg = w.get("message", "Hard requirement mismatch")
        cat = w.get("category", "general")
        if sev == "CRITICAL":
            critical_reasons.append(f"Critical {cat} mismatch: {msg}")
        elif sev == "MAJOR":
            major_reasons.append(f"Major {cat} mismatch: {msg}")

    # Fallback to status flag if warnings list empty
    if not critical_reasons and not major_reasons:
        if match_result.hard_requirement_status == "CRITICAL":
            critical_reasons.append("Critical hard requirement mismatch recorded on match.")
        elif match_result.hard_requirement_status in ["MISMATCH", "MAJOR"]:
            major_reasons.append("Major hard requirement mismatch recorded on match.")

    is_critical = len(critical_reasons) > 0
    is_major = len(major_reasons) > 0

    return is_critical, is_major, critical_reasons, major_reasons


def check_candidate_preferences(
    job: Job,
    candidate: CandidateProfile,
    pref: Optional[CandidatePreference],
) -> Tuple[List[str], List[str], List[str]]:
    """
    Evaluates candidate preferences against job attributes.
    Returns (disqualifications: List[str], review_reasons: List[str], supporting: List[str]).
    """
    disqualifications: List[str] = []
    review_reasons: List[str] = []
    supporting: List[str] = []

    if not pref:
        review_reasons.append("Candidate preferences not explicitly configured; using standard profile heuristics.")
        return disqualifications, review_reasons, supporting

    # 1. Work Mode Compatibility
    job_work_mode = (job.work_mode or "unknown").lower()
    allowed_modes = [m.lower() for m in (pref.work_modes or ["remote"])]

    if job_work_mode in ["unknown", ""]:
        review_reasons.append("Job work mode is unstated in source listing.")
    elif job_work_mode in allowed_modes:
        supporting.append(f"Work mode '{job.work_mode}' aligns with candidate preference.")
    else:
        # Check if relocation is disallowed
        if not pref.relocation_allowed and job_work_mode in ["on-site", "onsite", "hybrid"]:
            disqualifications.append(
                f"Work mode mismatch: Job is '{job.work_mode}' but candidate prefers {pref.work_modes} and relocation is disallowed."
            )
        else:
            review_reasons.append(
                f"Work mode '{job.work_mode}' differs from preferred {pref.work_modes}, but relocation is permitted."
            )

    # 2. Employment Type Compatibility
    job_desc = (job.description or "").lower()
    job_title = (job.title or "").lower()

    is_internship = "intern" in job_title or "internship" in job_desc
    is_contract = "contract" in job_desc or "freelance" in job_desc

    if is_internship and not pref.internship_allowed:
        disqualifications.append("Internship position detected, but candidate preference disallows internships.")
    elif is_contract and not pref.contract_allowed:
        disqualifications.append("Contract/freelance position detected, but candidate preference disallows contract work.")
    else:
        if is_internship and pref.internship_allowed:
            supporting.append("Internship position acceptable per candidate preferences.")
        elif not is_internship:
            supporting.append("Standard direct employment aligns with candidate preference.")

    # 3. Salary Floor Compatibility
    cand_min_sal = float(pref.minimum_salary) if pref.minimum_salary is not None else None
    salary_status = pref.salary_status or "NEEDS_CONFIRMATION"

    if cand_min_sal is not None:
        if salary_status == "CONFIRMED":
            if job.salary_max is not None and float(job.salary_max) < cand_min_sal:
                disqualifications.append(
                    f"Job max compensation ({job.salary_max} {job.currency}) is below confirmed minimum floor ({cand_min_sal} {pref.currency})."
                )
            elif job.salary_min is not None and float(job.salary_min) >= cand_min_sal:
                supporting.append(
                    f"Job compensation ({job.salary_min}-{job.salary_max} {job.currency}) satisfies confirmed salary floor."
                )
            elif job.salary_max is None and job.salary_min is None:
                review_reasons.append("Job does not disclose compensation details; candidate has a confirmed salary floor.")
        else:
            # Salary floor is NEEDS_CONFIRMATION: Never hard-reject for missing salary!
            if job.salary_max is None and job.salary_min is None:
                review_reasons.append("Compensation undisclosed; candidate salary expectations pending confirmation.")
            elif job.salary_max is not None and float(job.salary_max) < cand_min_sal:
                review_reasons.append(
                    f"Job max compensation ({job.salary_max} {job.currency}) is below unconfirmed target ({cand_min_sal} {pref.currency}); requires confirmation."
                )
            else:
                supporting.append(f"Disclosed salary meets or exceeds candidate target ({cand_min_sal} {pref.currency}).")

    return disqualifications, review_reasons, supporting


def check_role_relevance(
    job: Job,
    match_result: MatchResult,
    candidate: CandidateProfile,
    pref: Optional[CandidatePreference] = None,
) -> Tuple[NormalizedRole, Optional[str], Optional[str], Optional[str]]:
    """
    Evaluates role relevance independently from general match score.
    Returns (norm_role, disqualifier, review_reason, supporting_signal).
    Tiers:
      - DIRECT: Matches target role families (AI/ML, Backend, FDE/Tech Consulting)
      - ADJACENT: High-overlap technical specialization (Data Science, Systems, AI Platform)
      - TRANSFERABLE: General software/technical role outside primary target tracks
      - UNRELATED: Non-technical or unrelated domain
      - UNKNOWN: Unspecified or vague role
    """
    target_roles = pref.target_roles if pref and pref.target_roles else None

    # Inspect match_result role dimension details first
    norm_role: Optional[NormalizedRole] = None
    role_dim = (match_result.dimension_details or {}).get("role_fit", {})
    if role_dim and "relevance_tier" in role_dim:
        norm_role = NormalizedRole(
            concept=role_dim.get("concept") or job.title or "Unknown Role",
            target_role=None,
            priority_rank=None,
            fit_level=role_dim.get("status", "UNKNOWN"),
            score=float(role_dim.get("score", 50.0)),
            explanation=role_dim.get("explanation", ""),
            role_family=role_dim.get("role_family", "UNKNOWN"),
            relevance_tier=role_dim.get("relevance_tier", "UNKNOWN"),
            is_target_career_aligned=bool(role_dim.get("is_target_career_aligned", False)),
        )

    # Normalize directly if not cached or unknown
    if not norm_role or norm_role.relevance_tier == "UNKNOWN":
        norm_role = normalize_role(job.title or "", target_roles)

    disqualifier: Optional[str] = None
    review_reason: Optional[str] = None
    supporting: Optional[str] = None

    if norm_role.relevance_tier == "UNRELATED":
        disqualifier = (
            f"Role mismatch: Job role '{job.title}' is fundamentally outside candidate's target career families "
            f"({norm_role.concept} - {norm_role.role_family})."
        )
    elif norm_role.relevance_tier == "UNKNOWN":
        review_reason = f"Job title '{job.title}' is ambiguous or unspecified; role relevance cannot be confirmed."
    elif norm_role.relevance_tier == "TRANSFERABLE":
        review_reason = (
            f"Transferable role: '{job.title}' ({norm_role.concept}) shares general software skills "
            f"but is outside primary target career directions."
        )
    elif norm_role.relevance_tier == "ADJACENT":
        supporting = f"Role '{job.title}' is an adjacent technical specialization ({norm_role.concept} - {norm_role.role_family})."
    elif norm_role.relevance_tier == "DIRECT":
        supporting = f"Direct alignment with target career role: {norm_role.concept} ({norm_role.role_family})."

    return norm_role, disqualifier, review_reason, supporting
