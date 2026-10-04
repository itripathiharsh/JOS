from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.schemas.matching import (
    MatchResultResponse,
    BulkMatchRequest,
    BulkMatchResponse,
)
from app.services.matching_service import (
    calculate_or_get_job_match,
    get_job_match,
    bulk_match_jobs,
)

router = APIRouter()


@router.post("/jobs/{job_id}/match", response_model=MatchResultResponse)
def analyze_job_match(
    job_id: str,
    force: bool = Query(False, description="Force recomputation of match even if cached result is fresh"),
    candidate_id: Optional[str] = Query(None, description="Target candidate profile ID (defaults to primary candidate)"),
    db: Session = Depends(get_db),
):
    """
    Deterministically analyze and save profile match for a specific stored job.
    Reuses cached MatchResult if valid and force is False.
    """
    try:
        match_result, was_reused = calculate_or_get_job_match(
            db=db,
            job_id=job_id,
            candidate_id=candidate_id,
            force_recompute=force,
        )
        return match_result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Matching calculation error: {str(exc)}",
        )


@router.get("/jobs/{job_id}/match", response_model=MatchResultResponse)
def get_existing_job_match(
    job_id: str,
    candidate_id: Optional[str] = Query(None, description="Target candidate profile ID (defaults to primary candidate)"),
    db: Session = Depends(get_db),
):
    """Retrieve existing persistent MatchResult for a job without recomputing."""
    try:
        match_result = get_job_match(
            db=db,
            job_id=job_id,
            candidate_id=candidate_id,
        )
        if not match_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No match result found for job '{job_id}'. Run POST /api/jobs/{job_id}/match first.",
            )
        return match_result
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving match: {str(exc)}",
        )


@router.post("/jobs/match/bulk", response_model=BulkMatchResponse)
def bulk_analyze_stored_jobs(
    request: BulkMatchRequest,
    candidate_id: Optional[str] = Query(None, description="Target candidate profile ID (defaults to primary candidate)"),
    db: Session = Depends(get_db),
):
    """
    Bulk analyze multiple existing jobs stored in PostgreSQL against candidate profile.
    Reuses valid cached matches where possible unless force_recompute is True.
    """
    try:
        return bulk_match_jobs(
            db=db,
            limit=request.limit,
            force_recompute=request.force_recompute,
            candidate_id=candidate_id,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk matching error: {str(exc)}",
        )
