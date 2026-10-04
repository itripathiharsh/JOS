"""
Validation module for normalized job listings.
Ensures data integrity before records reach the persistence layer.
"""
import re
from typing import Tuple, Optional
from connectors.models import NormalizedJob


def validate_normalized_job(job: NormalizedJob) -> Tuple[bool, Optional[str]]:
    """
    Validate a NormalizedJob entity before storage or upserting.
    Returns:
        (True, None) if the job passes validation.
        (False, error_reason) if the job is malformed or invalid.
    """
    if not job:
        return False, "Job object is None"

    # 1. Title validation
    if not job.title or not job.title.strip() or len(job.title.strip()) < 2:
        return False, f"Job title is missing or too short: '{job.title}'"

    # 2. Company validation
    if not job.company or not job.company.strip():
        return False, "Hiring company name is missing"

    # 3. Source identifier validation
    if not job.source or not job.source.strip():
        return False, "Source identifier is missing"

    # 4. External Job ID validation
    if not job.external_job_id or not str(job.external_job_id).strip():
        return False, "External job ID is missing or empty"

    # 5. Application URL validation (if provided)
    if job.url is not None:
        url_clean = str(job.url).strip()
        if url_clean and not (url_clean.startswith("http://") or url_clean.startswith("https://")):
            return False, f"Invalid application URL scheme: '{url_clean}'"

    # 6. Salary sanity validation
    if job.salary_min is not None and job.salary_min < 0:
        return False, f"Negative salary_min: {job.salary_min}"

    if job.salary_max is not None and job.salary_max < 0:
        return False, f"Negative salary_max: {job.salary_max}"

    if job.salary_min is not None and job.salary_max is not None:
        if job.salary_min > job.salary_max:
            return False, f"salary_min ({job.salary_min}) exceeds salary_max ({job.salary_max})"

    return True, None
