from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.matching import MatchResult
from app.models.job import Job
from app.models.profile import CandidateProfile
from app.schemas.matching import BulkMatchResponse, MatchResultResponse
from app.intelligence import (
    extract_candidate_data_from_profile,
    extract_job_requirements,
    match_job_against_candidate,
    ENGINE_VERSION,
)
from app.core.logging import logger


def get_default_candidate(db: Session, candidate_id: Optional[str] = None) -> CandidateProfile:
    """Retrieve the target candidate profile or fallback to the primary candidate."""
    if candidate_id:
        candidate = db.query(CandidateProfile).filter(CandidateProfile.id == candidate_id).first()
        if not candidate:
            raise ValueError(f"Candidate profile with ID '{candidate_id}' not found.")
        return candidate

    candidate = db.query(CandidateProfile).first()
    if not candidate:
        raise ValueError("No candidate profile found in database. Please create a profile first.")
    return candidate


def get_job_match(
    db: Session,
    job_id: str,
    candidate_id: Optional[str] = None,
) -> Optional[MatchResult]:
    """Retrieve the existing persistent MatchResult for a job and candidate, if any."""
    candidate = get_default_candidate(db, candidate_id)
    return db.query(MatchResult).filter(
        and_(
            MatchResult.job_id == job_id,
            MatchResult.candidate_id == candidate.id,
        )
    ).first()


def is_match_stale(match: MatchResult, job: Job, candidate: CandidateProfile) -> bool:
    """
    Check if an existing match result is stale due to:
    - Engine version mismatch
    - Job updated after match was calculated
    - Candidate profile updated after match was calculated
    """
    if match.engine_version != ENGINE_VERSION:
        return True

    # Compare UTC timestamps
    calculated_at = match.calculated_at
    if calculated_at.tzinfo is None:
        calculated_at = calculated_at.replace(tzinfo=timezone.utc)

    job_updated = job.updated_at
    if job_updated and job_updated.tzinfo is None:
        job_updated = job_updated.replace(tzinfo=timezone.utc)

    if job_updated and job_updated > calculated_at:
        return True

    cand_updated = candidate.updated_at
    if cand_updated and cand_updated.tzinfo is None:
        cand_updated = cand_updated.replace(tzinfo=timezone.utc)

    if cand_updated and cand_updated > calculated_at:
        return True

    return False


def calculate_or_get_job_match(
    db: Session,
    job_id: str,
    candidate_id: Optional[str] = None,
    force_recompute: bool = False,
) -> Tuple[MatchResult, bool]:
    """
    Evaluates or reuses match between a job and candidate.
    Returns (MatchResult, was_reused: bool).
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job with ID '{job_id}' not found.")

    candidate = get_default_candidate(db, candidate_id)

    existing_match = db.query(MatchResult).filter(
        and_(
            MatchResult.job_id == job.id,
            MatchResult.candidate_id == candidate.id,
        )
    ).first()

    # Reuse cache if valid and force_recompute is False
    if existing_match and not force_recompute and not is_match_stale(existing_match, job, candidate):
        return existing_match, True

    # Extract candidate data
    cand_data = extract_candidate_data_from_profile(candidate)

    # Extract job requirements
    job_reqs = extract_job_requirements(
        title=job.title,
        description=job.description,
        requirements_text=job.requirements,
        responsibilities_text=job.responsibilities,
        location=job.location,
        work_mode=job.work_mode,
        salary_min=float(job.salary_min) if job.salary_min is not None else None,
        salary_max=float(job.salary_max) if job.salary_max is not None else None,
        currency=job.currency,
        candidate_target_roles=cand_data.target_roles,
    )

    # Run deterministic matching engine
    match_data = match_job_against_candidate(
        job_reqs=job_reqs,
        candidate=cand_data,
        engine_version=ENGINE_VERSION,
    )

    now = datetime.now(timezone.utc)

    if existing_match:
        # Update existing record in-place
        existing_match.engine_version = match_data.engine_version
        existing_match.overall_score = match_data.overall_score
        existing_match.fit_category = match_data.fit_category
        existing_match.has_hard_mismatch = match_data.has_hard_mismatch
        existing_match.hard_requirement_status = match_data.hard_requirement_status
        existing_match.hard_requirement_warnings = match_data.hard_requirement_warnings
        existing_match.role_score = match_data.role_score
        existing_match.skill_score = match_data.skill_score
        existing_match.experience_score = match_data.experience_score
        existing_match.location_score = match_data.location_score
        existing_match.work_mode_score = match_data.work_mode_score
        existing_match.salary_score = match_data.salary_score
        existing_match.education_score = match_data.education_score
        existing_match.employment_type_score = match_data.employment_type_score
        existing_match.matched_required_skills = match_data.matched_required_skills
        existing_match.missing_required_skills = match_data.missing_required_skills
        existing_match.matched_preferred_skills = match_data.matched_preferred_skills
        existing_match.missing_preferred_skills = match_data.missing_preferred_skills
        existing_match.dimension_details = match_data.dimension_details
        existing_match.concerns = match_data.concerns
        existing_match.explanations = match_data.explanations
        existing_match.data_completeness = match_data.data_completeness
        existing_match.data_completeness_level = match_data.data_completeness_level
        existing_match.calculated_at = now
        existing_match.updated_at = now
        db.commit()
        db.refresh(existing_match)
        return existing_match, False
    else:
        # Create new record
        new_match = MatchResult(
            job_id=job.id,
            candidate_id=candidate.id,
            engine_version=match_data.engine_version,
            overall_score=match_data.overall_score,
            fit_category=match_data.fit_category,
            has_hard_mismatch=match_data.has_hard_mismatch,
            hard_requirement_status=match_data.hard_requirement_status,
            hard_requirement_warnings=match_data.hard_requirement_warnings,
            role_score=match_data.role_score,
            skill_score=match_data.skill_score,
            experience_score=match_data.experience_score,
            location_score=match_data.location_score,
            work_mode_score=match_data.work_mode_score,
            salary_score=match_data.salary_score,
            education_score=match_data.education_score,
            employment_type_score=match_data.employment_type_score,
            matched_required_skills=match_data.matched_required_skills,
            missing_required_skills=match_data.missing_required_skills,
            matched_preferred_skills=match_data.matched_preferred_skills,
            missing_preferred_skills=match_data.missing_preferred_skills,
            dimension_details=match_data.dimension_details,
            concerns=match_data.concerns,
            explanations=match_data.explanations,
            data_completeness=match_data.data_completeness,
            data_completeness_level=match_data.data_completeness_level,
            calculated_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(new_match)
        db.commit()
        db.refresh(new_match)
        return new_match, False


def bulk_match_jobs(
    db: Session,
    limit: int = 50,
    force_recompute: bool = False,
    candidate_id: Optional[str] = None,
) -> BulkMatchResponse:
    """
    Bulk analyze existing stored jobs from the database.
    Does NOT fetch new jobs from external connectors.
    """
    candidate = get_default_candidate(db, candidate_id)
    jobs = db.query(Job).order_by(Job.discovered_at.desc()).limit(limit).all()

    processed = 0
    created = 0
    reused = 0
    results: List[MatchResultResponse] = []

    for job in jobs:
        try:
            match_res, was_reused = calculate_or_get_job_match(
                db=db,
                job_id=job.id,
                candidate_id=candidate.id,
                force_recompute=force_recompute,
            )
            processed += 1
            if was_reused:
                reused += 1
            else:
                created += 1
            results.append(MatchResultResponse.model_validate(match_res))
        except Exception as exc:
            logger.error(f"Error matching job {job.id}: {exc}", exc_info=True)

    return BulkMatchResponse(
        processed=processed,
        created=created,
        reused=reused,
        results=results,
    )
