from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.application import Application
from app.schemas.application import ApplicationListResponse, ApplicationResponse, ApplicationCreate
from app.schemas.preparation import (
    PreparationRequest,
    PreparationUpdateRequest,
    ApplicationPreparationResponse,
)
from app.schemas.execution import (
    ExecutionStartRequest,
    ExecutionResumeRequest,
    ExecutionApproveRequest,
    ExecutionCancelRequest,
    ApplicationExecutionResponse,
    ApplicationExecutionListResponse,
)
from app.services.application_service import get_applications, create_application
from app.services.preparation_engine.engine import ApplicationPreparationEngine
from app.services.execution_layer.engine import ApplicationExecutionEngine

router = APIRouter()


@router.get("/applications", response_model=ApplicationListResponse)
def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return get_applications(db, skip=skip, limit=limit, status=status)


@router.post("/applications", response_model=ApplicationResponse)
def add_application(data: ApplicationCreate, db: Session = Depends(get_db)):
    return create_application(db, data)


# --- Step 8: Application Preparation Engine Endpoints ---

@router.post("/applications/{application_id}/prepare", response_model=ApplicationPreparationResponse)
def prepare_application_by_id(
    application_id: str,
    payload: Optional[PreparationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Step 8: Prepares an application package for an existing application record.
    Transforms Candidate Profile + Resume + Job + Match Intelligence + Decision into Application Package.
    Boundary: Preparation only. Never auto-submits.
    """
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID '{application_id}' not found."
        )

    if not app_record.job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application record is not linked to a valid job_id."
        )

    req_data = payload or PreparationRequest()
    prep = ApplicationPreparationEngine.prepare_application_for_job(
        db=db,
        job_id=app_record.job_id,
        candidate_id=req_data.candidate_id or app_record.candidate_id,
        application_id=app_record.id,
        force_regenerate=req_data.force_regenerate,
        allow_skip=req_data.allow_skip,
        user_overrides=req_data.user_overrides,
        user_notes=req_data.user_notes,
    )
    return prep


@router.get("/applications/{application_id}/preparation", response_model=ApplicationPreparationResponse)
def get_application_preparation_by_id(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the persisted preparation package for an application.
    """
    prep = ApplicationPreparationEngine.get_preparation_by_application_id(db, application_id)
    if not prep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No preparation package found for application ID '{application_id}'. Please run prepare first."
        )
    return prep


@router.post("/applications/{application_id}/preparation/regenerate", response_model=ApplicationPreparationResponse)
def regenerate_application_preparation_by_id(
    application_id: str,
    payload: Optional[PreparationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Regenerates application preparation package with version increment.
    Avoids creating uncontrolled duplicates.
    """
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID '{application_id}' not found."
        )

    if not app_record.job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application record is not linked to a valid job_id."
        )

    req_data = payload or PreparationRequest()
    prep = ApplicationPreparationEngine.prepare_application_for_job(
        db=db,
        job_id=app_record.job_id,
        candidate_id=req_data.candidate_id or app_record.candidate_id,
        application_id=app_record.id,
        force_regenerate=True,
        allow_skip=req_data.allow_skip,
        user_overrides=req_data.user_overrides,
        user_notes=req_data.user_notes,
    )
    return prep


@router.patch("/applications/{application_id}/preparation", response_model=ApplicationPreparationResponse)
def update_application_preparation_by_id(
    application_id: str,
    payload: PreparationUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Updates human confirmations and user notes on an application preparation package.
    """
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record or not app_record.job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID '{application_id}' not found."
        )

    prep = ApplicationPreparationEngine.update_user_overrides(
        db=db,
        job_id=app_record.job_id,
        user_overrides=payload.user_overrides,
        user_notes=payload.user_notes,
        candidate_id=payload.candidate_id,
    )
    return prep


# --- Step 9: Application Execution Layer Endpoints ---

@router.post("/applications/{application_id}/execute", response_model=ApplicationExecutionResponse)
def execute_application_by_id(
    application_id: str,
    payload: Optional[ExecutionStartRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Step 9: Initiates a controlled application execution attempt.
    Supports MANUAL, ASSISTED, and AUTOMATED modes.
    Enforces idempotency, stops at anti-bot/sensitive barriers, and halts before submission.
    """
    req_data = payload or ExecutionStartRequest()
    execution = ApplicationExecutionEngine.start_execution(
        db=db,
        application_id=application_id,
        mode=req_data.mode or "MANUAL",
        source=req_data.source or "generic_web",
        allow_force=req_data.allow_force or False,
        context=req_data.context,
    )
    return execution


@router.get("/applications/{application_id}/execution", response_model=ApplicationExecutionResponse)
def get_latest_application_execution_by_id(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the most recent execution attempt for an application.
    """
    execution = ApplicationExecutionEngine.get_latest_execution_for_application(db, application_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No execution attempt found for application ID '{application_id}'. Please execute first."
        )
    return execution


@router.get("/applications/{application_id}/executions", response_model=ApplicationExecutionListResponse)
def list_application_executions_by_id(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves all historical execution attempts for an application.
    """
    executions = ApplicationExecutionEngine.get_all_executions_for_application(db, application_id)
    return ApplicationExecutionListResponse(items=executions, total=len(executions))


@router.post("/applications/{application_id}/execution/{execution_id}/resume", response_model=ApplicationExecutionResponse)
def resume_application_execution(
    application_id: str,
    execution_id: str,
    payload: ExecutionResumeRequest,
    db: Session = Depends(get_db)
):
    """
    Resumes an execution attempt from AWAITING_USER or BLOCKED state with confirmed user inputs.
    """
    execution = ApplicationExecutionEngine.resume_execution(
        db=db,
        execution_id=execution_id,
        user_inputs=payload.user_inputs,
        context=payload.context,
        application_id=application_id,
    )
    return execution


@router.post("/applications/{application_id}/execution/{execution_id}/approve-submit", response_model=ApplicationExecutionResponse)
def approve_and_submit_application(
    application_id: str,
    execution_id: str,
    payload: Optional[ExecutionApproveRequest] = None,
    db: Session = Depends(get_db)
):
    """
    CRITICAL HUMAN SUBMISSION GATE:
    Executes final application submission ONLY after explicit human approval in READY_TO_SUBMIT state.
    """
    req_data = payload or ExecutionApproveRequest()
    execution = ApplicationExecutionEngine.approve_and_submit(
        db=db,
        execution_id=execution_id,
        context=req_data.context,
        application_id=application_id,
    )
    return execution


@router.post("/applications/{application_id}/execution/{execution_id}/cancel", response_model=ApplicationExecutionResponse)
def cancel_application_execution(
    application_id: str,
    execution_id: str,
    payload: Optional[ExecutionCancelRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Cancels an active execution attempt.
    """
    reason = payload.reason if payload else "User cancelled execution"
    execution = ApplicationExecutionEngine.cancel_execution(
        db=db,
        execution_id=execution_id,
        reason=reason,
        application_id=application_id,
    )
    return execution


@router.post("/applications/{application_id}/execution/{execution_id}/retry", response_model=ApplicationExecutionResponse)
def retry_application_execution(
    application_id: str,
    execution_id: str,
    payload: Optional[ExecutionStartRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Starts a new execution attempt (incrementing attempt_number) while preserving historical attempt logs.
    """
    req_data = payload or ExecutionStartRequest()
    execution = ApplicationExecutionEngine.start_execution(
        db=db,
        application_id=application_id,
        mode=req_data.mode or "MANUAL",
        source=req_data.source or "generic_web",
        allow_force=req_data.allow_force or False,
        context=req_data.context,
    )
    return execution

