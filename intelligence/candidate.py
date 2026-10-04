import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set, Tuple
from intelligence.models import CandidateData, CanonicalSkill
from intelligence.normalization import normalize_skill

# Month name mapping
MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_date_to_year_month(date_str: Optional[str], default_year: int = 2026, default_month: int = 10) -> Optional[Tuple[int, int]]:
    """
    Parse date string like 'Nov 2025', '2026', 'Present', 'June 2025' to (year, month).
    """
    if not date_str:
        return None

    cleaned = date_str.strip().lower()
    if cleaned in ["present", "current", "now"]:
        return (default_year, default_month)

    # Check for Month Year (e.g., 'Nov 2025' or 'November 2025')
    m = re.match(r"([a-z]+)\.?\s*(\d{4})", cleaned)
    if m:
        month_name = m.group(1)
        year_num = int(m.group(2))
        month_num = MONTH_MAP.get(month_name, 1)
        return (year_num, month_num)

    # Check for Year Month (e.g., '2025-11' or '2025/11')
    m = re.match(r"(\d{4})[-/](\d{1,2})", cleaned)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # Check for Year only (e.g., '2026')
    m = re.match(r"^(\d{4})$", cleaned)
    if m:
        return (int(m.group(1)), 1)

    return None


def calculate_experience_months(
    start_str: str,
    end_str: Optional[str] = None,
    current: bool = False,
    now_year: int = 2026,
    now_month: int = 10,
) -> int:
    """Calculate duration of a single experience record in months."""
    start_ym = parse_date_to_year_month(start_str, now_year, now_month)
    if not start_ym:
        return 0

    if current or not end_str or end_str.strip().lower() in ["present", "current", "now"]:
        end_ym = (now_year, now_month)
    else:
        end_ym = parse_date_to_year_month(end_str, now_year, now_month)
        if not end_ym:
            end_ym = start_ym

    start_y, start_m = start_ym
    end_y, end_m = end_ym

    diff = (end_y - start_y) * 12 + (end_m - start_m) + 1
    return max(1, diff)


def extract_candidate_data_from_profile(profile_model: Any) -> CandidateData:
    """
    Extract structured candidate data from the CandidateProfile SQLAlchemy model.
    Treats CandidateProfile as the single source of truth.
    Candidate actual experience is derived exclusively from Experience records.
    """
    candidate_id = profile_model.id
    candidate_name = profile_model.name

    # 1. Career Preferences
    pref = profile_model.preference_record
    target_roles = pref.target_roles if pref and pref.target_roles else [
        "AI Engineer",
        "ML Engineer",
        "Backend Engineer",
        "Forward Deployed Engineer (FDE)",
        "Technical Consultant",
    ]
    role_priority = pref.role_priority if pref and pref.role_priority else target_roles

    preferred_locations = pref.preferred_locations if pref and pref.preferred_locations else [
        "Remote",
        "Uttar Pradesh",
        "Anywhere in India",
    ]
    location_priority = pref.location_priority if pref and pref.location_priority else preferred_locations

    work_modes = pref.work_modes if pref and pref.work_modes else ["Remote", "Hybrid", "On-site"]
    min_salary = float(pref.minimum_salary) if pref and pref.minimum_salary is not None else 350000.0
    salary_currency = pref.currency if pref and pref.currency else "INR"
    salary_status = pref.salary_status if pref and pref.salary_status else "NEEDS_CONFIRMATION"
    employment_types = pref.employment_types if pref and pref.employment_types else ["Full-time", "Internship", "Contract"]
    relocation = pref.relocation_allowed if pref is not None else True

    # 2. Actual Experience from Experience records
    total_months = 0
    exp_summary: List[Dict[str, Any]] = []

    for exp in (profile_model.experiences or []):
        months = calculate_experience_months(
            start_str=exp.start_date,
            end_str=exp.end_date,
            current=exp.current,
        )
        total_months += months
        exp_summary.append({
            "title": exp.title,
            "company": exp.company,
            "duration_months": months,
            "employment_type": exp.employment_type,
        })

    # Convert to years with 1 decimal precision
    actual_exp_years = round(total_months / 12.0, 1)

    # 3. Canonical Skills
    canonical_skills: List[CanonicalSkill] = []
    canonical_names_set: Set[str] = set()

    for s in (profile_model.skills or []):
        norm = normalize_skill(s.name)
        canonical_skills.append(norm)
        canonical_names_set.add(norm.canonical_name.lower())

    # 4. Education Records
    educations: List[Dict[str, Any]] = []
    for edu in (profile_model.educations or []):
        educations.append({
            "degree": edu.degree,
            "field": edu.field,
            "institution": edu.institution,
        })

    return CandidateData(
        id=candidate_id,
        name=candidate_name,
        target_roles=target_roles,
        role_priority=role_priority,
        preferred_locations=preferred_locations,
        location_priority=location_priority,
        work_modes=work_modes,
        minimum_salary=min_salary,
        salary_currency=salary_currency,
        salary_status=salary_status,
        actual_experience_years=actual_exp_years,
        experience_records_summary=exp_summary,
        skills=canonical_skills,
        skill_names_canonical=canonical_names_set,
        educations=educations,
        employment_types=employment_types,
        relocation_allowed=relocation,
    )


# Convenient alias
extract_candidate_data = extract_candidate_data_from_profile
