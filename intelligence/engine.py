import re
from typing import List, Dict, Any, Optional, Tuple
from intelligence.models import (
    JobRequirements,
    CandidateData,
    CanonicalSkill,
    DimensionEvaluation,
    MatchResultData,
    HardRequirementWarning,
    HardRequirementEvaluation,
)

ENGINE_VERSION = "1.2.0"

# Base dimension weights
BASE_WEIGHTS = {
    "role": 0.30,
    "skills": 0.35,
    "experience": 0.15,
    "location": 0.08,
    "work_mode": 0.04,
    "salary": 0.03,
    "education": 0.03,
    "employment_type": 0.02,
}


def evaluate_hard_requirements(
    job_reqs: JobRequirements,
    candidate: CandidateData,
    missing_required_skills: List[str],
) -> HardRequirementEvaluation:
    """
    Evaluates hard requirements independently from general similarity scoring:
    1. Experience: minimum required years vs candidate actual experience from Experience records.
    2. Required Skills: explicit mandatory technical skills missing from candidate profile.
    3. Location: explicit geographic restriction that excludes candidate location (India).
    4. Education: explicit degree level requirements (e.g. PhD, Master's) unmet by candidate.
    """
    warnings: List[HardRequirementWarning] = []
    has_critical = False
    has_major = False
    score_cap: Optional[float] = None
    max_fit_category: Optional[str] = None

    # --- 1. EXPERIENCE HARD REQUIREMENT ---
    min_exp = job_reqs.minimum_experience
    cand_exp = candidate.actual_experience_years
    exp_mismatch_data: Optional[Dict[str, Any]] = None

    if min_exp is not None and cand_exp < min_exp:
        gap = round(min_exp - cand_exp, 1)
        req_label = job_reqs.experience_text or f"{int(min_exp) if min_exp.is_integer() else min_exp}+ years"

        if min_exp >= 5.0 and cand_exp <= 2.5:
            # Critical seniority gap (e.g., 5+ or 8+ years vs 2 years)
            has_critical = True
            msg = f"Job explicitly requires {req_label}. Candidate has approximately {cand_exp} years of practical experience (seniority gap of ~{gap} yrs)."
            warnings.append(
                HardRequirementWarning(
                    category="experience",
                    severity="CRITICAL",
                    message=msg,
                    details={"required": req_label, "actual": cand_exp, "gap": gap},
                )
            )
            score_cap = min(score_cap or 100.0, 54.0)
            max_fit_category = "PARTIAL_RELEVANCE"
            exp_mismatch_data = {"required": req_label, "actual": cand_exp, "gap": gap, "severity": "CRITICAL"}
        elif gap >= 1.5:
            # Major seniority gap (e.g., 4+ years vs ~2.0 years)
            has_major = True
            msg = f"Job explicitly requires {req_label}. Candidate has approximately {cand_exp} years of practical experience."
            warnings.append(
                HardRequirementWarning(
                    category="experience",
                    severity="MAJOR",
                    message=msg,
                    details={"required": req_label, "actual": cand_exp, "gap": gap},
                )
            )
            score_cap = min(score_cap or 100.0, 64.0)
            max_fit_category = "PARTIAL_RELEVANCE"
            exp_mismatch_data = {"required": req_label, "actual": cand_exp, "gap": gap, "severity": "MAJOR"}
        else:
            # Minor/moderate gap (e.g. 3+ years vs 2.0 years)
            has_major = True
            msg = f"Job requests {req_label}. Candidate has approximately {cand_exp} years of practical experience."
            warnings.append(
                HardRequirementWarning(
                    category="experience",
                    severity="MAJOR",
                    message=msg,
                    details={"required": req_label, "actual": cand_exp, "gap": gap},
                )
            )
            score_cap = min(score_cap or 100.0, 78.0)
            if not max_fit_category or max_fit_category == "HIGH_RELEVANCE":
                max_fit_category = "GOOD_RELEVANCE"
            exp_mismatch_data = {"required": req_label, "actual": cand_exp, "gap": gap, "severity": "MAJOR"}

    # --- 2. REQUIRED SKILLS HARD REQUIREMENT ---
    req_skill_mismatches = list(missing_required_skills)
    if len(req_skill_mismatches) >= 2:
        has_major = True
        preview = ", ".join(req_skill_mismatches[:4])
        if len(req_skill_mismatches) > 4:
            preview += f" (+{len(req_skill_mismatches) - 4} more)"
        msg = f"Missing {len(req_skill_mismatches)} required technical skills: {preview}."
        warnings.append(
            HardRequirementWarning(
                category="required_skills",
                severity="MAJOR",
                message=msg,
                details={"missing": req_skill_mismatches, "count": len(req_skill_mismatches)},
            )
        )
        score_cap = min(score_cap or 100.0, 64.0)
        max_fit_category = "PARTIAL_RELEVANCE"
    elif len(req_skill_mismatches) == 1:
        has_major = True
        msg = f"Missing 1 required technical skill: {req_skill_mismatches[0]}."
        warnings.append(
            HardRequirementWarning(
                category="required_skills",
                severity="MAJOR",
                message=msg,
                details={"missing": req_skill_mismatches, "count": 1},
            )
        )
        score_cap = min(score_cap or 100.0, 78.0)
        if not max_fit_category or max_fit_category == "HIGH_RELEVANCE":
            max_fit_category = "GOOD_RELEVANCE"

    # --- 3. LOCATION RESTRICTION HARD REQUIREMENT ---
    loc = job_reqs.location
    loc_mismatch_data: Optional[Dict[str, Any]] = None
    if loc and loc.strip():
        loc_lower = loc.lower()
        # Non-restrictive / global / candidate-friendly keywords
        friendly_keywords = ["worldwide", "anywhere", "global", "remote", "apac", "india", "asia"]
        is_friendly = any(k in loc_lower for k in friendly_keywords)

        # Check for explicit exclusions
        if not is_friendly:
            # Job specifies restricted regions (e.g. 'USA', 'Americas, Europe, Israel', 'US only', 'Europe')
            has_major = True
            msg = f"Job has an explicit geographic restriction ('{loc}') that excludes candidate's primary location (India)."
            warnings.append(
                HardRequirementWarning(
                    category="location",
                    severity="MAJOR",
                    message=msg,
                    details={"restricted_to": loc, "candidate_location": "India"},
                )
            )
            score_cap = min(score_cap or 100.0, 64.0)
            max_fit_category = "PARTIAL_RELEVANCE"
            loc_mismatch_data = {"restricted_to": loc, "candidate_location": "India"}

    # --- 4. EDUCATION HARD REQUIREMENT ---
    edu_mismatch_data: Optional[Dict[str, Any]] = None
    if job_reqs.education_requirements:
        edu_text = " ".join(job_reqs.education_requirements).lower()
        # Candidate degrees: B.Tech in CSE, BS in Data Science & Applications
        if "phd" in edu_text or "doctorate" in edu_text or "doctoral" in edu_text:
            has_major = True
            msg = f"Job explicitly requires a PhD/Doctorate degree ({', '.join(job_reqs.education_requirements)}). Candidate holds Bachelor degrees (B.Tech, BS)."
            warnings.append(
                HardRequirementWarning(
                    category="education",
                    severity="MAJOR",
                    message=msg,
                    details={"required": job_reqs.education_requirements, "actual": "B.Tech CSE, BS Data Science"},
                )
            )
            score_cap = min(score_cap or 100.0, 64.0)
            max_fit_category = "PARTIAL_RELEVANCE"
            edu_mismatch_data = {"required": job_reqs.education_requirements, "actual": "B.Tech CSE, BS Data Science"}
        elif "master" in edu_text or "m.tech" in edu_text or "m.s" in edu_text or "ms in" in edu_text:
            # If it strictly requires Master's without Bachelor
            if "bachelor" not in edu_text and "or equivalent" not in edu_text:
                has_major = True
                msg = f"Job explicitly requires a Master's degree ({', '.join(job_reqs.education_requirements)}). Candidate holds Bachelor degrees (B.Tech, BS)."
                warnings.append(
                    HardRequirementWarning(
                        category="education",
                        severity="MAJOR",
                        message=msg,
                        details={"required": job_reqs.education_requirements, "actual": "B.Tech CSE, BS Data Science"},
                    )
                )
                score_cap = min(score_cap or 100.0, 64.0)
                max_fit_category = "PARTIAL_RELEVANCE"
                edu_mismatch_data = {"required": job_reqs.education_requirements, "actual": "B.Tech CSE, BS Data Science"}

    # --- 5. ROLE RELEVANCE HARD REQUIREMENT ---
    norm_role = job_reqs.normalized_role
    if norm_role and norm_role.relevance_tier == "UNRELATED":
        has_critical = True
        msg = f"Role '{job_reqs.raw_title}' is fundamentally outside candidate's target career families ({norm_role.concept})."
        warnings.append(
            HardRequirementWarning(
                category="role_relevance",
                severity="CRITICAL",
                message=msg,
                details={"title": job_reqs.raw_title, "concept": norm_role.concept, "role_family": norm_role.role_family},
            )
        )
        score_cap = min(score_cap or 100.0, 35.0)
        max_fit_category = "LOW_RELEVANCE"

    # Overall evaluation status
    if has_critical or (has_major and (exp_mismatch_data and exp_mismatch_data.get("gap", 0) >= 1.5 or len(req_skill_mismatches) >= 2 or loc_mismatch_data or edu_mismatch_data)):
        status = "MISMATCH"
    elif has_major:
        status = "WARNING"
    else:
        status = "PASSED"

    return HardRequirementEvaluation(
        has_critical_mismatch=has_critical,
        has_major_mismatch=has_major,
        status=status,
        warnings=warnings,
        experience_mismatch=exp_mismatch_data,
        required_skill_mismatches=req_skill_mismatches,
        location_mismatch=loc_mismatch_data,
        education_mismatch=edu_mismatch_data,
        score_cap=score_cap,
        max_fit_category=max_fit_category,
    )


def evaluate_role_dimension(job_reqs: JobRequirements, candidate: CandidateData) -> DimensionEvaluation:
    norm_role = job_reqs.normalized_role
    if not norm_role or norm_role.relevance_tier == "UNKNOWN" or norm_role.fit_level == "UNKNOWN":
        return DimensionEvaluation(
            name="Role Fit",
            status="UNKNOWN",
            score=30.0,
            weight=BASE_WEIGHTS["role"],
            is_known=False,
            explanation="Job title does not provide sufficient clarity for role matching.",
        )

    concerns = []
    if norm_role.relevance_tier == "UNRELATED":
        concerns.append(f"Job title '{job_reqs.raw_title}' is in an unrelated domain ({norm_role.concept}) outside candidate's target engineering careers.")
    elif norm_role.relevance_tier == "TRANSFERABLE":
        concerns.append(f"Job title '{job_reqs.raw_title}' is outside primary target tracks; foundational skills are transferable.")

    return DimensionEvaluation(
        name="Role Fit",
        status=norm_role.fit_level,
        score=norm_role.score,
        weight=BASE_WEIGHTS["role"],
        is_known=True,
        explanation=norm_role.explanation,
        concerns=concerns,
    )


def evaluate_skills_dimension(
    job_reqs: JobRequirements,
    candidate: CandidateData
) -> Tuple[DimensionEvaluation, List[Dict[str, str]], List[str], List[Dict[str, str]], List[str]]:
    candidate_skills_lower = candidate.skill_names_canonical

    # 1. Match Required Skills
    matched_req: List[Dict[str, str]] = []
    missing_req: List[str] = []

    for req_skill in job_reqs.required_skills:
        if req_skill.canonical_name.lower() in candidate_skills_lower:
            matched_req.append(req_skill.to_dict())
        else:
            missing_req.append(req_skill.canonical_name)

    # 2. Match Preferred Skills
    matched_pref: List[Dict[str, str]] = []
    missing_pref: List[str] = []

    for pref_skill in job_reqs.preferred_skills:
        if pref_skill.canonical_name.lower() in candidate_skills_lower:
            matched_pref.append(pref_skill.to_dict())
        else:
            missing_pref.append(pref_skill.canonical_name)

    total_req_count = len(job_reqs.required_skills)
    total_pref_count = len(job_reqs.preferred_skills)

    if total_req_count == 0 and total_pref_count == 0:
        evaluation = DimensionEvaluation(
            name="Skill Fit",
            status="UNKNOWN",
            score=50.0,
            weight=BASE_WEIGHTS["skills"],
            is_known=False,
            explanation="No explicit technical skills were identified in the job posting.",
        )
        return evaluation, matched_req, missing_req, matched_pref, missing_pref

    # Calculate skill score
    if total_req_count > 0 and total_pref_count > 0:
        req_ratio = len(matched_req) / total_req_count
        pref_ratio = len(matched_pref) / total_pref_count
        score = (req_ratio * 85.0) + (pref_ratio * 15.0)
    elif total_req_count > 0:
        req_ratio = len(matched_req) / total_req_count
        score = req_ratio * 100.0
    else:
        pref_ratio = len(matched_pref) / total_pref_count
        score = 50.0 + (pref_ratio * 50.0)

    score = round(max(0.0, min(100.0, score)), 1)

    # Explanation and concerns
    concerns = []
    matched_req_names = [m["canonical"] for m in matched_req]
    matched_req_preview = ", ".join(matched_req_names[:6])
    if len(matched_req_names) > 6:
        matched_req_preview += f" (+{len(matched_req_names) - 6} more)"

    if total_req_count > 0:
        explanation = f"Matched {len(matched_req)} of {total_req_count} required skills ({matched_req_preview or 'None'})."
    else:
        explanation = f"Matched {len(matched_pref)} of {total_pref_count} preferred skills."

    if missing_req:
        missing_preview = ", ".join(missing_req[:4])
        concerns.append(f"Missing {len(missing_req)} required skill(s): {missing_preview}.")

    status = "FIT" if score >= 75.0 else ("PARTIAL" if score >= 45.0 else "MISMATCH")

    evaluation = DimensionEvaluation(
        name="Skill Fit",
        status=status,
        score=score,
        weight=BASE_WEIGHTS["skills"],
        is_known=True,
        explanation=explanation,
        concerns=concerns,
    )
    return evaluation, matched_req, missing_req, matched_pref, missing_pref


def evaluate_experience_dimension(job_reqs: JobRequirements, candidate: CandidateData) -> DimensionEvaluation:
    min_exp = job_reqs.minimum_experience
    cand_exp = candidate.actual_experience_years

    if min_exp is None:
        return DimensionEvaluation(
            name="Experience Fit",
            status="UNKNOWN",
            score=50.0,
            weight=BASE_WEIGHTS["experience"],
            is_known=False,
            explanation="Experience requirement is not explicitly specified in the job posting.",
        )

    concerns = []
    req_label = job_reqs.experience_text or f"{int(min_exp)}+ years"

    if cand_exp >= min_exp:
        status = "FIT"
        score = 100.0
        explanation = f"Candidate experience (~{cand_exp} yrs) satisfies the required {req_label}."
    elif cand_exp >= (min_exp * 0.5) or min_exp <= 2.5:
        status = "PARTIAL"
        score = 60.0
        explanation = f"Job requests {req_label}; candidate has ~{cand_exp} yrs of practical experience."
        concerns.append(f"Experience requirement ({req_label}) is moderately above candidate's current ~{cand_exp} yrs.")
    else:
        status = "MISMATCH"
        score = 25.0
        explanation = f"Significant experience seniority gap: job requires {req_label} vs candidate's ~{cand_exp} yrs."
        concerns.append(f"Job requires {req_label}, exceeding candidate's ~{cand_exp} yrs experience.")

    return DimensionEvaluation(
        name="Experience Fit",
        status=status,
        score=score,
        weight=BASE_WEIGHTS["experience"],
        is_known=True,
        explanation=explanation,
        concerns=concerns,
    )


def evaluate_location_dimension(job_reqs: JobRequirements, candidate: CandidateData) -> DimensionEvaluation:
    loc = job_reqs.location
    if not loc or not loc.strip():
        return DimensionEvaluation(
            name="Location Fit",
            status="UNKNOWN",
            score=50.0,
            weight=BASE_WEIGHTS["location"],
            is_known=False,
            explanation="Job location was not specified.",
        )

    loc_lower = loc.lower()
    concerns = []

    # Worldwide / APAC / India remote
    if any(k in loc_lower for k in ["worldwide", "anywhere", "global", "apac", "india", "asia"]):
        status = "FIT"
        score = 100.0
        explanation = f"Job location ({loc}) is compatible with candidate's remote location in India."
    elif any(k in loc_lower for k in ["americas", "europe", "usa", "uk", "israel", "canada", "latam"]):
        # Regional remote
        status = "PARTIAL"
        score = 55.0
        explanation = f"Job specifies regional location: '{loc}'. Candidate is in India, so time-zone overlap or eligibility verification may be needed."
        concerns.append(f"Location restricted to '{loc}'; may require regional timezone alignment.")
    elif "remote" in job_reqs.work_modes:
        status = "FIT"
        score = 90.0
        explanation = f"Job offers remote work, aligning with candidate's remote preference ({loc})."
    else:
        # On-site / unknown regional
        if candidate.relocation_allowed:
            status = "PARTIAL"
            score = 50.0
            explanation = f"Job is located in '{loc}'. Candidate has indicated willingness to relocate."
        else:
            status = "MISMATCH"
            score = 20.0
            explanation = f"Job location '{loc}' does not match candidate's preferred locations."
            concerns.append(f"Location ({loc}) does not match candidate preferences.")

    return DimensionEvaluation(
        name="Location Fit",
        status=status,
        score=score,
        weight=BASE_WEIGHTS["location"],
        is_known=True,
        explanation=explanation,
        concerns=concerns,
    )


def evaluate_work_mode_dimension(job_reqs: JobRequirements, candidate: CandidateData) -> DimensionEvaluation:
    if not job_reqs.work_modes:
        return DimensionEvaluation(
            name="Work Mode Fit",
            status="UNKNOWN",
            score=50.0,
            weight=BASE_WEIGHTS["work_mode"],
            is_known=False,
            explanation="Work mode is not explicitly stated in the job posting.",
        )

    # Candidate accepts Remote, Hybrid, and On-site
    cand_modes_lower = [m.lower() for m in candidate.work_modes]
    matched_modes = [m for m in job_reqs.work_modes if m.lower() in cand_modes_lower]

    if matched_modes:
        status = "FIT"
        score = 100.0
        explanation = f"Job work mode ({', '.join(job_reqs.work_modes).title()}) aligns with candidate's preferences."
    else:
        status = "PARTIAL"
        score = 60.0
        explanation = f"Job work mode: {', '.join(job_reqs.work_modes)}."

    return DimensionEvaluation(
        name="Work Mode Fit",
        status=status,
        score=score,
        weight=BASE_WEIGHTS["work_mode"],
        is_known=True,
        explanation=explanation,
    )


def evaluate_salary_dimension(job_reqs: JobRequirements, candidate: CandidateData) -> DimensionEvaluation:
    if job_reqs.salary_min is None and job_reqs.salary_max is None:
        return DimensionEvaluation(
            name="Salary Fit",
            status="UNKNOWN",
            score=50.0,
            weight=BASE_WEIGHTS["salary"],
            is_known=False,
            explanation="Salary was not disclosed in the job posting; salary fit cannot be evaluated.",
            concerns=["Salary not disclosed."],
        )

    curr = (job_reqs.currency or "USD").upper()
    sal_min = job_reqs.salary_min or job_reqs.salary_max or 0.0
    sal_max = job_reqs.salary_max or sal_min

    # Candidate baseline: ₹3.5 LPA (~350,000 INR)
    # Status note
    cand_status_note = f"(Status: {candidate.salary_status})"
    concerns = []

    # If USD: 1 USD ~ 85 INR, or hourly rate ($50-$150/hr = $100k-$300k/yr >> 3.5 LPA)
    if curr == "USD":
        # Disclosed USD salary is universally above ₹3.5 LPA
        status = "FIT"
        score = 100.0
        explanation = f"Disclosed compensation ({sal_min:.0f} - {sal_max:.0f} USD) comfortably meets candidate's minimum baseline of ₹3.5 LPA {cand_status_note}."
    elif curr == "INR":
        if sal_max >= (candidate.minimum_salary or 350000.0):
            status = "FIT"
            score = 100.0
            explanation = f"Disclosed compensation (₹{sal_min:,.0f} - ₹{sal_max:,.0f} INR) satisfies candidate's minimum baseline of ₹3.5 LPA {cand_status_note}."
        else:
            status = "BELOW_PREFERENCE"
            score = 30.0
            explanation = f"Disclosed compensation (₹{sal_max:,.0f} INR) is below candidate's baseline preference (₹3.5 LPA)."
            concerns.append("Disclosed compensation is below candidate's baseline minimum.")
    else:
        status = "FIT"
        score = 90.0
        explanation = f"Disclosed compensation: {sal_min} - {sal_max} {curr}."

    return DimensionEvaluation(
        name="Salary Fit",
        status=status,
        score=score,
        weight=BASE_WEIGHTS["salary"],
        is_known=True,
        explanation=explanation,
        concerns=concerns,
    )


def evaluate_education_dimension(job_reqs: JobRequirements, candidate: CandidateData) -> DimensionEvaluation:
    if not job_reqs.education_requirements:
        return DimensionEvaluation(
            name="Education Fit",
            status="NOT_SPECIFIED",
            score=50.0,
            weight=BASE_WEIGHTS["education"],
            is_known=False,
            explanation="No formal degree requirement specified in the job posting.",
        )

    # Candidate has B.Tech in CSE and BS in Data Science & Applications
    degree_desc = ", ".join(job_reqs.education_requirements)
    return DimensionEvaluation(
        name="Education Fit",
        status="FIT",
        score=100.0,
        weight=BASE_WEIGHTS["education"],
        is_known=True,
        explanation=f"Candidate's technical degrees (B.Tech in CSE, BS in Data Science) satisfy job requirement: {degree_desc}.",
    )


def evaluate_employment_type_dimension(job_reqs: JobRequirements, candidate: CandidateData) -> DimensionEvaluation:
    if not job_reqs.employment_type:
        return DimensionEvaluation(
            name="Employment Type Fit",
            status="UNKNOWN",
            score=50.0,
            weight=BASE_WEIGHTS["employment_type"],
            is_known=False,
            explanation="Employment type is not explicitly specified.",
        )

    cand_types_lower = [t.lower() for t in candidate.employment_types]
    if job_reqs.employment_type.lower() in cand_types_lower:
        return DimensionEvaluation(
            name="Employment Type Fit",
            status="FIT",
            score=100.0,
            weight=BASE_WEIGHTS["employment_type"],
            is_known=True,
            explanation=f"Employment type ({job_reqs.employment_type}) is accepted by candidate.",
        )

    return DimensionEvaluation(
        name="Employment Type Fit",
        status="PARTIAL",
        score=60.0,
        weight=BASE_WEIGHTS["employment_type"],
        is_known=True,
        explanation=f"Employment type is {job_reqs.employment_type}.",
    )


def match_job_against_candidate(
    job_reqs: JobRequirements,
    candidate: CandidateData,
    engine_version: str = ENGINE_VERSION,
) -> MatchResultData:
    """
    Deterministically evaluates all 8 matching dimensions between job and candidate profile,
    and applies Hard Requirement Evaluation to cap/penalize explicit gaps.
    """
    # 1. Evaluate Dimensions
    role_eval = evaluate_role_dimension(job_reqs, candidate)
    skills_eval, matched_req, missing_req, matched_pref, missing_pref = evaluate_skills_dimension(job_reqs, candidate)
    exp_eval = evaluate_experience_dimension(job_reqs, candidate)
    loc_eval = evaluate_location_dimension(job_reqs, candidate)
    mode_eval = evaluate_work_mode_dimension(job_reqs, candidate)
    salary_eval = evaluate_salary_dimension(job_reqs, candidate)
    edu_eval = evaluate_education_dimension(job_reqs, candidate)
    emp_eval = evaluate_employment_type_dimension(job_reqs, candidate)

    all_dims = [
        role_eval,
        skills_eval,
        exp_eval,
        loc_eval,
        mode_eval,
        salary_eval,
        edu_eval,
        emp_eval,
    ]

    # 2. Transparent Weighted Scoring with Unknown-Data Normalization
    known_dims = [d for d in all_dims if d.is_known]
    total_known_weight = sum(d.weight for d in known_dims)

    if total_known_weight > 0:
        # Renormalize known dimension weights so unknown data doesn't penalize candidate
        weighted_sum = sum(d.score * (d.weight / total_known_weight) for d in known_dims)
        base_score = round(weighted_sum, 1)
    else:
        base_score = 50.0

    base_score = max(0.0, min(100.0, base_score))

    # 3. Hard Requirement Check Layer
    hard_eval = evaluate_hard_requirements(
        job_reqs=job_reqs,
        candidate=candidate,
        missing_required_skills=missing_req,
    )

    # Apply penalty & score cap if hard mismatches exist
    final_score = base_score
    if hard_eval.has_critical_mismatch:
        final_score = base_score - 25.0
    elif hard_eval.has_major_mismatch:
        final_score = base_score - 15.0

    if hard_eval.score_cap is not None:
        final_score = min(final_score, hard_eval.score_cap)

    final_score = round(max(0.0, min(100.0, final_score)), 1)

    # 4. Data Completeness Calculation
    known_count = len(known_dims)
    data_completeness = round((known_count / len(all_dims)) * 100.0, 1)

    if data_completeness >= 75.0:
        completeness_level = "HIGH"
    elif data_completeness >= 50.0:
        completeness_level = "MEDIUM"
    else:
        completeness_level = "LOW"

    # 5. Fit Category Calculation
    if data_completeness < 30.0:
        fit_category = "INSUFFICIENT_DATA"
    elif final_score >= 80.0:
        fit_category = "HIGH_RELEVANCE"
    elif final_score >= 65.0:
        fit_category = "GOOD_RELEVANCE"
    elif final_score >= 45.0:
        fit_category = "PARTIAL_RELEVANCE"
    else:
        fit_category = "LOW_RELEVANCE"

    # Enforce Hard Requirement Max Category Cap
    FIT_RANKS = {
        "LOW_RELEVANCE": 1,
        "PARTIAL_RELEVANCE": 2,
        "GOOD_RELEVANCE": 3,
        "HIGH_RELEVANCE": 4,
        "INSUFFICIENT_DATA": 0,
    }
    if hard_eval.max_fit_category:
        max_rank = FIT_RANKS.get(hard_eval.max_fit_category, 4)
        curr_rank = FIT_RANKS.get(fit_category, 0)
        if curr_rank > max_rank:
            fit_category = hard_eval.max_fit_category

    # Absolute rule: Hard mismatch CANNOT receive HIGH_RELEVANCE
    if (hard_eval.has_critical_mismatch or hard_eval.has_major_mismatch) and fit_category == "HIGH_RELEVANCE":
        fit_category = "GOOD_RELEVANCE" if not (hard_eval.has_critical_mismatch or hard_eval.status == "MISMATCH") else "PARTIAL_RELEVANCE"

    # 6. Explanations & Concerns Compilation
    explanations: List[str] = [d.explanation for d in all_dims if d.explanation]
    concerns: List[str] = []
    for d in all_dims:
        concerns.extend(d.concerns)

    # If hard requirement warnings exist, prepend clear deterministic notice
    if hard_eval.warnings:
        warning_bullets = "\n".join(f"• {w.message}" for w in hard_eval.warnings)
        if hard_eval.status == "MISMATCH":
            hdr_text = (
                f"Hard Requirement Mismatch: This position is capped at {fit_category} (Score: {final_score:.1f}/100) "
                f"due to significant explicit requirement gaps:\n{warning_bullets}"
            )
        else:
            hdr_text = (
                f"Hard Requirement Notice: Capped at {fit_category} (Score: {final_score:.1f}/100) "
                f"due to requirement concerns:\n{warning_bullets}"
            )
        explanations.insert(0, hdr_text)
        # Also ensure warning messages are at the front of concerns
        for w in reversed(hard_eval.warnings):
            if w.message not in concerns:
                concerns.insert(0, f"[{w.severity}] {w.message}")

    # Dimension Details Map
    dimension_details = {}
    for d in all_dims:
        key = d.name.lower().replace(" ", "_")
        d_dict = {
            "name": d.name,
            "status": d.status,
            "score": d.score,
            "weight": d.weight,
            "is_known": d.is_known,
            "explanation": d.explanation,
        }
        if d.name == "Role Fit" and job_reqs.normalized_role:
            d_dict["role_family"] = job_reqs.normalized_role.role_family
            d_dict["relevance_tier"] = job_reqs.normalized_role.relevance_tier
            d_dict["is_target_career_aligned"] = job_reqs.normalized_role.is_target_career_aligned
        dimension_details[key] = d_dict

    return MatchResultData(
        engine_version=engine_version,
        overall_score=final_score,
        fit_category=fit_category,
        role_score=role_eval.score,
        skill_score=skills_eval.score,
        experience_score=exp_eval.score,
        location_score=loc_eval.score,
        work_mode_score=mode_eval.score,
        salary_score=salary_eval.score,
        education_score=edu_eval.score,
        employment_type_score=emp_eval.score,
        matched_required_skills=matched_req,
        missing_required_skills=missing_req,
        matched_preferred_skills=matched_pref,
        missing_preferred_skills=missing_pref,
        dimension_details=dimension_details,
        concerns=concerns,
        explanations=explanations,
        data_completeness=data_completeness,
        data_completeness_level=completeness_level,
        hard_requirement_status=hard_eval.status,
        hard_requirement_warnings=[w.to_dict() for w in hard_eval.warnings],
        has_hard_mismatch=hard_eval.has_critical_mismatch or hard_eval.has_major_mismatch,
    )
