from typing import Dict, Any, Tuple
from app.models.job import Job
from app.services.deduplication.url_normalizer import extract_domain


# Source hierarchy: Direct ATS / Company > Curated Feeds > General Aggregators
SOURCE_AUTHORITY_SCORES: Dict[str, int] = {
    # Direct Company ATS (Tier 1)
    "company_ats": 300,
    "greenhouse": 280,
    "lever": 280,
    "workday": 280,
    "ashby": 280,
    "smartrecruiters": 280,
    # Curated remote-first job boards (Tier 2)
    "remotive": 200,
    "arbeitnow": 190,
    "jobicy": 190,
    # Aggregators and general feeds (Tier 3)
    "aggregator": 100,
    "feed": 100,
    "manual": 50,
}


def score_job_completeness_and_authority(job: Job) -> float:
    """
    Computes a deterministic authority and quality score for a job record:
    1. Source Authority Tier (50-300 points)
    2. URL Stability (direct career page domain vs aggregator) (0-30 points)
    3. Record Completeness (salary, description depth, requirements, etc.) (0-100 points)
    """
    score = 0.0

    # 1. Source Authority
    source_key = (job.source or "").lower().strip()
    score += SOURCE_AUTHORITY_SCORES.get(source_key, 120)

    # 2. URL Stability & Direct Career Site
    if job.application_url:
        domain = extract_domain(job.application_url) or ""
        if any(ats in domain for ats in ("greenhouse.io", "lever.co", "workday.com", "ashbyhq.com")):
            score += 30.0
        elif "remotive.com" in domain:
            score += 15.0
        else:
            score += 10.0

    # 3. Content Completeness
    # Description depth
    desc_len = len(job.description or "")
    if desc_len > 1000:
        score += 30.0
    elif desc_len > 300:
        score += 20.0
    elif desc_len > 50:
        score += 10.0

    # Requirements & Responsibilities
    if job.requirements:
        score += 15.0
    if job.responsibilities:
        score += 15.0

    # Salary information
    if job.salary_min is not None or job.salary_max is not None:
        score += 20.0

    # Location & Work Mode
    if job.location:
        score += 10.0
    if job.work_mode and job.work_mode != "unknown":
        score += 10.0

    return score


def select_canonical_record(job_a: Job, job_b: Job) -> Tuple[Job, Job]:
    """
    Deterministically selects which record should be CANONICAL and which should be DUPLICATE.
    Returns (canonical_job, duplicate_job).
    
    Tie-breaking hierarchy:
    1. Highest Authority & Completeness Score
    2. Earliest discovered_at timestamp
    3. Earliest created_at timestamp
    4. Lexicographical ID order (absolute determinism)
    """
    score_a = score_job_completeness_and_authority(job_a)
    score_b = score_job_completeness_and_authority(job_b)

    if score_a > score_b:
        return (job_a, job_b)
    elif score_b > score_a:
        return (job_b, job_a)

    # Tie-breaker 1: Earliest discovered timestamp
    disc_a = job_a.discovered_at or job_a.created_at
    disc_b = job_b.discovered_at or job_b.created_at
    if disc_a < disc_b:
        return (job_a, job_b)
    elif disc_b < disc_a:
        return (job_b, job_a)

    # Tie-breaker 2: Earliest created timestamp
    if job_a.created_at < job_b.created_at:
        return (job_a, job_b)
    elif job_b.created_at < job_a.created_at:
        return (job_b, job_a)

    # Final Tie-breaker: Lexicographical ID
    if str(job_a.id) <= str(job_b.id):
        return (job_a, job_b)
    else:
        return (job_b, job_a)
