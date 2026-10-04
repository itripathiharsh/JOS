from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.db.session import get_db
from app.models.application import Application
from app.schemas.memory import (
    OutcomeUpdateRequest,
    NoteCreateRequest,
    NoteResponse,
    OverrideCreateRequest,
    OverrideResponse,
    TimelineItemResponse,
    ApplicationMemoryResponse,
)
from app.services.application_memory import (
    TimelineService,
    OutcomeService,
    NotesService,
    OverrideService,
    ApplicationFeedbackEngine,
)

router = APIRouter()


@router.get("/applications/{application_id}/memory", response_model=ApplicationMemoryResponse)
def get_application_memory(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Step 10: Reconstructs complete application memory including immutable snapshots
    (candidate, job, decision, artifacts), append-only notes, decision overrides,
    and unified chronological timeline.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID '{application_id}' not found."
        )

    # Ensure snapshots are populated
    OutcomeService.ensure_snapshots(db, app)
    db.refresh(app)

    notes = NotesService.get_notes(db, application_id)
    overrides = OverrideService.get_overrides(db, application_id)
    timeline = TimelineService.get_application_timeline(db, application_id)

    return ApplicationMemoryResponse(
        id=app.id,
        job_id=app.job_id,
        candidate_id=app.candidate_id,
        lifecycle_stage=app.lifecycle_stage,
        status=app.status,
        source=app.source,
        application_url=app.application_url,
        outcome_category=app.outcome_category,
        outcome_provenance=app.outcome_provenance,
        rejection_category=app.rejection_category,
        rejection_reason=app.rejection_reason,
        last_outcome_date=app.last_outcome_date,
        candidate_snapshot=app.candidate_snapshot,
        job_snapshot=app.job_snapshot,
        decision_snapshot=app.decision_snapshot,
        artifacts_snapshot=app.artifacts_snapshot,
        notes=[NoteResponse.model_validate(n) for n in notes],
        overrides=[OverrideResponse.model_validate(o) for o in overrides],
        timeline=[TimelineItemResponse.model_validate(t.model_dump()) for t in timeline],
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.get("/applications/{application_id}/timeline", response_model=List[TimelineItemResponse])
def get_application_timeline(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the chronological audit timeline for an application.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID '{application_id}' not found."
        )

    timeline = TimelineService.get_application_timeline(db, application_id)
    return [TimelineItemResponse.model_validate(t.model_dump()) for t in timeline]


@router.post("/applications/{application_id}/outcome", response_model=ApplicationMemoryResponse)
def update_application_outcome(
    application_id: str,
    payload: OutcomeUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Updates application lifecycle stage and outcome attributes with explicit provenance.
    """
    app = OutcomeService.update_outcome(
        db=db,
        application_id=application_id,
        lifecycle_stage=payload.lifecycle_stage,
        provenance=payload.provenance,
        rejection_category=payload.rejection_category,
        rejection_reason=payload.rejection_reason,
        notes=payload.notes,
        actor="user",
    )

    notes = NotesService.get_notes(db, application_id)
    overrides = OverrideService.get_overrides(db, application_id)
    timeline = TimelineService.get_application_timeline(db, application_id)

    return ApplicationMemoryResponse(
        id=app.id,
        job_id=app.job_id,
        candidate_id=app.candidate_id,
        lifecycle_stage=app.lifecycle_stage,
        status=app.status,
        source=app.source,
        application_url=app.application_url,
        outcome_category=app.outcome_category,
        outcome_provenance=app.outcome_provenance,
        rejection_category=app.rejection_category,
        rejection_reason=app.rejection_reason,
        last_outcome_date=app.last_outcome_date,
        candidate_snapshot=app.candidate_snapshot,
        job_snapshot=app.job_snapshot,
        decision_snapshot=app.decision_snapshot,
        artifacts_snapshot=app.artifacts_snapshot,
        notes=[NoteResponse.model_validate(n) for n in notes],
        overrides=[OverrideResponse.model_validate(o) for o in overrides],
        timeline=[TimelineItemResponse.model_validate(t.model_dump()) for t in timeline],
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.post("/applications/{application_id}/notes", response_model=NoteResponse)
def add_application_note(
    application_id: str,
    payload: NoteCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Appends a timestamped note to the application memory log.
    """
    note = NotesService.add_note(
        db=db,
        application_id=application_id,
        content=payload.content,
        category=payload.category,
        author=payload.author,
    )
    return NoteResponse.model_validate(note)


@router.get("/applications/{application_id}/notes", response_model=List[NoteResponse])
def get_application_notes(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Lists all append-only notes for an application.
    """
    notes = NotesService.get_notes(db, application_id)
    return [NoteResponse.model_validate(n) for n in notes]


@router.post("/applications/{application_id}/override", response_model=OverrideResponse)
def record_application_override(
    application_id: str,
    payload: OverrideCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Records a user decision override while preserving original system recommendation.
    """
    override = OverrideService.record_override(
        db=db,
        application_id=application_id,
        override_decision=payload.override_decision,
        original_decision=payload.original_decision,
        override_type=payload.override_type,
        reason=payload.reason,
    )
    return OverrideResponse.model_validate(override)


@router.get("/applications/{application_id}/override", response_model=List[OverrideResponse])
def get_application_overrides(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Lists all decision overrides for an application.
    """
    overrides = OverrideService.get_overrides(db, application_id)
    return [OverrideResponse.model_validate(o) for o in overrides]


@router.get("/analytics/application-memory")
def get_memory_feedback_analytics(
    candidate_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Step 10: Returns deterministic feedback analytics, conversion funnels,
    role breakdown, rejection patterns, and decision alignment observations.
    """
    return ApplicationFeedbackEngine.get_feedback_report(db, candidate_id=candidate_id)
