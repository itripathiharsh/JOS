from typing import List, Optional, Any, Dict
from app.services.deduplication.normalizers import (
    extract_seniority,
    normalize_location,
    extract_requisition_id,
)


def check_contradictions(
    job_a_data: Dict[str, Any],
    job_b_data: Dict[str, Any],
) -> List[str]:
    """
    Evaluates two job records for explicit contradictions.
    Returns a list of contradiction messages. If the list is non-empty,
    automatic deduplication is strictly BLOCKED.
    """
    contradictions: List[str] = []

    # 1. Location / Country Contradiction
    loc_a = normalize_location(job_a_data.get("location"))
    loc_b = normalize_location(job_b_data.get("location"))

    if loc_a["country"] and loc_b["country"] and loc_a["country"] != loc_b["country"]:
        contradictions.append(
            f"Different country locations: '{loc_a['country'].title()}' vs '{loc_b['country'].title()}'"
        )
    elif loc_a["scope"] != "unknown" and loc_b["scope"] != "unknown":
        if loc_a["scope"] != loc_b["scope"] and loc_a["scope"] != "worldwide" and loc_b["scope"] != "worldwide":
            contradictions.append(
                f"Conflicting geographic scopes: '{loc_a['scope']}' vs '{loc_b['scope']}'"
            )

    # 2. Seniority Contradiction
    sen_a = extract_seniority(job_a_data.get("title", ""))
    sen_b = extract_seniority(job_b_data.get("title", ""))

    if sen_a and sen_b and sen_a != sen_b:
        contradictions.append(
            f"Different seniority levels: '{sen_a.title()}' vs '{sen_b.title()}'"
        )
    elif (sen_a is not None) != (sen_b is not None):
        # One explicitly says Senior / Lead / Principal / Intern while the other has no seniority
        # E.g. 'Senior AI Engineer' vs 'AI Engineer' or 'Intern AI Engineer' vs 'AI Engineer'
        # These are distinct job vacancies!
        contradictions.append(
            f"Asymmetric seniority: '{sen_a or 'unspecified'}' vs '{sen_b or 'unspecified'}'"
        )

    # 3. Explicit Requisition ID Contradiction
    req_a = extract_requisition_id(
        raw_payload=job_a_data.get("raw_payload"),
        external_id=job_a_data.get("external_job_id"),
        url=job_a_data.get("application_url"),
        text=job_a_data.get("description"),
    )
    req_b = extract_requisition_id(
        raw_payload=job_b_data.get("raw_payload"),
        external_id=job_b_data.get("external_job_id"),
        url=job_b_data.get("application_url"),
        text=job_b_data.get("description"),
    )

    if req_a and req_b and req_a.upper() != req_b.upper():
        contradictions.append(
            f"Different requisition / job reference IDs: '{req_a}' vs '{req_b}'"
        )

    # 4. Work Mode Contradiction (Strict on-site vs strictly remote)
    wm_a = (job_a_data.get("work_mode") or "").strip().lower()
    wm_b = (job_b_data.get("work_mode") or "").strip().lower()
    if wm_a and wm_b:
        if (wm_a == "on-site" and wm_b == "remote") or (wm_a == "remote" and wm_b == "on-site"):
            contradictions.append(
                f"Conflicting work modes: '{wm_a}' vs '{wm_b}'"
            )

    # 5. Salary Band Contradiction (strictly non-overlapping in same currency)
    curr_a = job_a_data.get("currency") or "USD"
    curr_b = job_b_data.get("currency") or "USD"
    min_a = job_a_data.get("salary_min")
    max_a = job_a_data.get("salary_max")
    min_b = job_b_data.get("salary_min")
    max_b = job_b_data.get("salary_max")

    if curr_a == curr_b and min_a is not None and max_a is not None and min_b is not None and max_b is not None:
        try:
            val_min_a, val_max_a = float(min_a), float(max_a)
            val_min_b, val_max_b = float(min_b), float(max_b)
            # Check for non-overlap with at least 20% margin
            if val_max_a < val_min_b * 0.8 or val_max_b < val_min_a * 0.8:
                contradictions.append(
                    f"Non-overlapping salary bands in {curr_a}: [{val_min_a}-{val_max_a}] vs [{val_min_b}-{val_max_b}]"
                )
        except (ValueError, TypeError):
            pass

    return contradictions
