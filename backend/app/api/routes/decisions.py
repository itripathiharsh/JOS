from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List

from app.db.session import get_db
from app.schemas.decision import (
    ApplicationDecisionResponse,
    DecisionBatchRequest,
    DecisionBatchResponse,
    DecisionListResponse,
)
from app.services.decision_engine import ApplicationDecisionEngine
from app.models.decision import ApplicationDecision
from app.services.matching_service import get_default_candidate

router = APIRouter()


@router.post("/jobs/{job_id}/decision", response_model=ApplicationDecisionResponse)
def evaluate_job_decision(
    job_id: str,
    force: bool = Query(False, description="Force recomputation of decision even if cached"),
    candidate_id: Optional[str] = Query(None, description="Target candidate profile ID (defaults to primary)"),
    db: Session = Depends(get_db),
):
    """
    Evaluates multi-dimensional application decision (APPLY, REVIEW, SKIP) for a specific job.
    Reuses existing fresh decision unless force is True.
    """
    try:
        decision, _ = ApplicationDecisionEngine.evaluate_and_persist(
            db=db,
            job_id=job_id,
            candidate_id=candidate_id,
            force=force,
        )
        return decision
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Application decision evaluation error: {str(exc)}",
        )


@router.get("/jobs/{job_id}/decision", response_model=ApplicationDecisionResponse)
def get_existing_job_decision(
    job_id: str,
    candidate_id: Optional[str] = Query(None, description="Target candidate profile ID (defaults to primary)"),
    db: Session = Depends(get_db),
):
    """Retrieves existing persistent ApplicationDecision for a job without recomputing."""
    try:
        decision = ApplicationDecisionEngine.get_decision_for_job(
            db=db,
            job_id=job_id,
            candidate_id=candidate_id,
        )
        if not decision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No decision found for job '{job_id}'. Run POST /api/jobs/{job_id}/decision first.",
            )
        return decision
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving decision: {str(exc)}",
        )


@router.post("/jobs/decisions/bulk", response_model=DecisionBatchResponse)
def bulk_evaluate_decisions(
    request: DecisionBatchRequest,
    candidate_id: Optional[str] = Query(None, description="Target candidate profile ID (defaults to primary)"),
    db: Session = Depends(get_db),
):
    """
    Bulk evaluates application decisions across stored jobs in PostgreSQL.
    Focuses on canonical jobs by default.
    """
    try:
        res = ApplicationDecisionEngine.bulk_evaluate(
            db=db,
            limit=request.limit,
            force=request.force_recompute,
            candidate_id=candidate_id,
            only_canonical=request.only_canonical,
        )
        return DecisionBatchResponse(
            processed=res["processed"],
            reused=res["reused"],
            new_or_updated=res["new_or_updated"],
            apply_count=res["apply_count"],
            review_count=res["review_count"],
            skip_count=res["skip_count"],
            items=[ApplicationDecisionResponse.model_validate(item) for item in res["items"]],
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk decision evaluation error: {str(exc)}",
        )


@router.get("/jobs/decisions", response_model=DecisionListResponse)
def list_decisions(
    decision: Optional[str] = Query(None, description="Filter by decision: APPLY, REVIEW, SKIP"),
    risk_level: Optional[str] = Query(None, description="Filter by risk: LOW, MEDIUM, HIGH"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lists application decisions with summary metrics and filtering."""
    query = db.query(ApplicationDecision)

    if decision and decision.lower() != "all":
        query = query.filter(ApplicationDecision.decision == decision.upper())

    if risk_level and risk_level.lower() != "all":
        query = query.filter(ApplicationDecision.risk_level == risk_level.upper())

    total = query.count()
    items = query.order_by(desc(ApplicationDecision.updated_at)).offset(skip).limit(limit).all()

    apply_count = db.query(ApplicationDecision).filter(ApplicationDecision.decision == "APPLY").count()
    review_count = db.query(ApplicationDecision).filter(ApplicationDecision.decision == "REVIEW").count()
    skip_count = db.query(ApplicationDecision).filter(ApplicationDecision.decision == "SKIP").count()

    return DecisionListResponse(
        total=total,
        items=[ApplicationDecisionResponse.model_validate(item) for item in items],
        apply_count=apply_count,
        review_count=review_count,
        skip_count=skip_count,
    )
