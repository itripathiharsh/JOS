from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.schemas.discovery import (
    DiscoveryConfig,
    DiscoveryPreviewResponse,
    DiscoveryRunRequest,
    DiscoveryRunSummary,
    DiscoveryRunListResponse,
)
from app.services.discovery_service import (
    preview_discovery,
    execute_discovery_run,
    get_discovery_runs,
    get_discovery_run_by_id,
)

router = APIRouter(prefix="/discovery")


@router.post("/preview", response_model=DiscoveryPreviewResponse)
def preview_search_strategies(
    request: Optional[DiscoveryConfig] = None,
    source: str = Query("remotive", description="Target job source identifier"),
    db: Session = Depends(get_db)
):
    """
    Generate and preview search strategies derived from candidate profile and preferences.
    Executes entirely in-memory without network calls or modifying database state.
    """
    try:
        return preview_discovery(db=db, config=request, source_name=source)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate search strategy preview: {str(exc)}"
        )


@router.post("/run", response_model=DiscoveryRunSummary)
def run_discovery(
    request: DiscoveryRunRequest,
    db: Session = Depends(get_db)
):
    """
    Manually trigger a bounded job discovery run.
    Expands candidate preferences into prioritized queries and executes them through the source layer.
    """
    try:
        return execute_discovery_run(
            db=db,
            source_name=request.source,
            config=request.config,
            dry_run=request.dry_run,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discovery run execution failed: {str(exc)}"
        )


@router.get("/runs", response_model=DiscoveryRunListResponse)
def list_discovery_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List historical discovery runs ordered by newest first."""
    return get_discovery_runs(db=db, skip=skip, limit=limit)


@router.get("/runs/{run_id}", response_model=DiscoveryRunSummary)
def get_discovery_run_detail(
    run_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve detailed telemetry and execution stats for a specific discovery run."""
    run = get_discovery_run_by_id(db=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery run '{run_id}' not found."
        )
    return run
