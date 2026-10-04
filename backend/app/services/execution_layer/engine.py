from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status

from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.models.profile import CandidateProfile
from app.models.preparation import ApplicationPreparation
from app.models.execution import ApplicationExecution
from app.models.decision import ApplicationDecision

from app.services.execution_layer.models import (
    ExecutionMode,
    ExecutionStatus,
    BlockerType,
    SubmissionEvidence,
)
from app.services.execution_layer.state_machine import ExecutionStateMachine
from app.services.execution_layer.idempotency import DuplicateSubmissionGuard
from app.services.execution_layer.executors.manual_executor import ManualExecutor
from app.services.execution_layer.executors.generic_web_executor import GenericWebExecutor
from app.services.execution_layer.executors.mock_executor import LocalMockExecutor
from app.services.execution_layer.executors.base import BaseApplicationExecutor


class ApplicationExecutionEngine:
    """
    Master Application Execution Layer Orchestrator.
    Controls application execution workflows (MANUAL, ASSISTED, AUTOMATED),
    enforces idempotency, halts safely at bot/sensitive barriers,
    and requires explicit human approval at the final submission gate.
    """

    @classmethod
    def _get_executor(cls, mode: str, source: str) -> BaseApplicationExecutor:
        """Resolves executor adapter for given mode and source."""
        if mode == ExecutionMode.MANUAL.value or source == "manual":
            return ManualExecutor()
        elif source == "mock":
            return LocalMockExecutor()
        return GenericWebExecutor()

    @classmethod
    def _record_event(
        cls,
        db: Session,
        application_id: str,
        event_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApplicationEvent:
        """
        Records an auditable application event with strict secret sanitization.
        Ensures NO passwords, tokens, or raw cookies are persisted.
        """
        sanitized_meta = dict(metadata or {})
        # Strip potential secret keys
        for key in ["password", "token", "cookie", "auth_header", "secret", "cvv"]:
            sanitized_meta.pop(key, None)

        event = ApplicationEvent(
            application_id=application_id,
            event_type=event_type,
            description=description,
            event_metadata=sanitized_meta,
        )
        db.add(event)
        return event

    @classmethod
    def start_execution(
        cls,
        db: Session,
        application_id: str,
        mode: str = "MANUAL",
        source: str = "generic_web",
        allow_force: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> ApplicationExecution:
        """
        Initiates an execution attempt for an approved application.
        Validates idempotency, readiness, and decision eligibility.
        """
        app_record = db.query(Application).filter(Application.id == application_id).first()
        if not app_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' not found."
            )

        job = db.query(Job).filter(Job.id == app_record.job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Application is not linked to a valid job."
            )

        # 1. Idempotency & Duplicate Submission Guard
        is_eligible, reason, prior_exec = DuplicateSubmissionGuard.check_application_eligibility(
            db, application_id, allow_force=allow_force
        )
        if not is_eligible:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=reason,
            )

        # 2. Check Preparation Package
        prep = db.query(ApplicationPreparation).filter(
            ApplicationPreparation.application_id == application_id
        ).first()

        if not prep:
            # Check by job and candidate
            prep = db.query(ApplicationPreparation).filter(
                ApplicationPreparation.job_id == app_record.job_id,
                ApplicationPreparation.candidate_id == app_record.candidate_id,
            ).first()

        if not prep:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No preparation package found for this application. Please run Step 8 preparation first.",
            )

        if prep.readiness_status == "BLOCKED" and not allow_force:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Preparation package is BLOCKED: {prep.readiness_reasons}. Execution cannot proceed without resolution.",
            )

        # 3. Check Decision Safety (SKIP jobs cannot execute unless forced)
        decision = db.query(ApplicationDecision).filter(
            ApplicationDecision.job_id == job.id,
            ApplicationDecision.candidate_id == app_record.candidate_id,
        ).first()

        if decision and decision.decision == "SKIP" and not allow_force:
            reason = decision.reasons[0] if decision.reasons else "Disqualified by Application Decision Engine."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job was evaluated as SKIP ({reason}). Execution is blocked by default.",
            )

        # 4. Calculate Attempt Number
        existing_attempts = db.query(ApplicationExecution).filter(
            ApplicationExecution.application_id == application_id
        ).count()
        attempt_number = existing_attempts + 1

        # 5. Create Execution Record
        execution = ApplicationExecution(
            application_id=app_record.id,
            job_id=job.id,
            candidate_id=app_record.candidate_id,
            preparation_id=prep.id,
            attempt_number=attempt_number,
            mode=mode.upper(),
            source=source.lower(),
            status=ExecutionStatus.NOT_STARTED.value,
            current_step="Initializing execution attempt",
        )
        db.add(execution)
        db.flush()

        # Update initial state to READY
        ExecutionStateMachine.validate_transition(ExecutionStatus.NOT_STARTED, ExecutionStatus.READY)
        execution.status = ExecutionStatus.READY.value

        # Record audit event
        cls._record_event(
            db,
            application_id=app_record.id,
            event_type="EXECUTION_STARTED",
            description=f"Execution attempt #{attempt_number} started in {mode.upper()} mode.",
            metadata={"mode": mode, "source": source, "attempt_number": attempt_number},
        )

        # 6. Execute via Source Adapter
        executor = cls._get_executor(mode.upper(), source.lower())
        exec_context = context or {}
        step_result = executor.start_execution(execution, exec_context)

        # Audit transition events
        if execution.status == ExecutionStatus.BLOCKED.value:
            cls._record_event(
                db,
                application_id=app_record.id,
                event_type="EXECUTION_BLOCKED",
                description=f"Execution blocked: {execution.blocker_reason}",
                metadata={"blocker_reason": execution.blocker_reason},
            )
        elif execution.status == ExecutionStatus.AWAITING_USER.value:
            cls._record_event(
                db,
                application_id=app_record.id,
                event_type="USER_INTERVENTION_REQUIRED",
                description=execution.user_action_prompt or "Human action required to proceed.",
                metadata={"status": execution.status},
            )
        elif execution.status == ExecutionStatus.READY_TO_SUBMIT.value:
            cls._record_event(
                db,
                application_id=app_record.id,
                event_type="FORM_DETECTED",
                description="Application form detected and mapped. Ready for user submission review.",
                metadata={"fields_mapped": len(execution.field_mappings or [])},
            )

        db.commit()
        db.refresh(execution)
        return execution

    @classmethod
    def resume_execution(
        cls,
        db: Session,
        execution_id: str,
        user_inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        application_id: Optional[str] = None,
    ) -> ApplicationExecution:
        """
        Resumes execution from AWAITING_USER or BLOCKED state.
        Allows user to confirm sensitive fields, provide missing values, or cancel.
        """
        execution = db.query(ApplicationExecution).filter(
            ApplicationExecution.id == execution_id
        ).first()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution record with ID '{execution_id}' not found.",
            )

        if application_id and execution.application_id != application_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution '{execution_id}' does not belong to application '{application_id}'.",
            )

        current_status = ExecutionStatus(execution.status)
        if not ExecutionStateMachine.is_resumable(current_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Execution in state '{current_status.value}' cannot be resumed.",
            )

        executor = cls._get_executor(execution.mode, execution.source)
        res = executor.resume_execution(execution, user_inputs, context or {})

        action = user_inputs.get("action", "confirm_fields")
        if action == "cancel":
            cls._record_event(
                db,
                application_id=execution.application_id,
                event_type="EXECUTION_CANCELLED",
                description=f"Execution attempt #{execution.attempt_number} was cancelled by candidate.",
            )
        elif execution.status == ExecutionStatus.SUBMITTED.value:
            cls._record_event(
                db,
                application_id=execution.application_id,
                event_type="SUBMISSION_CONFIRMED",
                description=f"Candidate manually confirmed submission on employer portal.",
                metadata=execution.confirmation_evidence,
            )
            # Update parent application
            app_rec = db.query(Application).filter(Application.id == execution.application_id).first()
            if app_rec:
                app_rec.status = "submitted"
                app_rec.applied_at = datetime.now(timezone.utc)
        else:
            cls._record_event(
                db,
                application_id=execution.application_id,
                event_type="USER_CONFIRMED_FIELD",
                description=f"Candidate confirmed form fields and updated execution state to {execution.status}.",
            )

        db.commit()
        db.refresh(execution)
        return execution

    @classmethod
    def approve_and_submit(
        cls,
        db: Session,
        execution_id: str,
        context: Optional[Dict[str, Any]] = None,
        application_id: Optional[str] = None,
    ) -> ApplicationExecution:
        """
        CRITICAL SUBMISSION GATE:
        Only executes final submission after explicit human approval in READY_TO_SUBMIT state.
        Verifies observable proof before updating status.
        """
        execution = db.query(ApplicationExecution).filter(
            ApplicationExecution.id == execution_id
        ).first()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution record with ID '{execution_id}' not found.",
            )

        if application_id and execution.application_id != application_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution '{execution_id}' does not belong to application '{application_id}'.",
            )

        current_status = ExecutionStatus(execution.status)
        if current_status != ExecutionStatus.READY_TO_SUBMIT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Submission cannot be approved from '{current_status.value}'. Must be in READY_TO_SUBMIT.",
            )

        # Audit human approval
        cls._record_event(
            db,
            application_id=execution.application_id,
            event_type="USER_APPROVED_SUBMISSION",
            description=f"Candidate explicitly approved final application submission for attempt #{execution.attempt_number}.",
        )
        cls._record_event(
            db,
            application_id=execution.application_id,
            event_type="SUBMISSION_STARTED",
            description=f"Dispatching application submission to {execution.job.company} portal.",
        )

        executor = cls._get_executor(execution.mode, execution.source)
        evidence = executor.approve_and_submit(execution, context or {})

        if evidence.confirmed:
            cls._record_event(
                db,
                application_id=execution.application_id,
                event_type="SUBMISSION_CONFIRMED",
                description=f"Submission confirmed with observable evidence: {evidence.evidence_type} (Ref: {evidence.confirmation_number or 'Verified'}).",
                metadata=evidence.to_dict(),
            )
            # Update parent application
            app_rec = db.query(Application).filter(Application.id == execution.application_id).first()
            if app_rec:
                app_rec.status = "submitted"
                app_rec.lifecycle_stage = "SUBMITTED"
                app_rec.outcome_provenance = "USER_CONFIRMED"
                app_rec.last_outcome_date = datetime.now(timezone.utc)
                app_rec.applied_at = datetime.now(timezone.utc)
                if execution.preparation and execution.preparation.resume_recommendation:
                    app_rec.resume_used = execution.preparation.resume_recommendation.get("document_name")
                from app.services.application_memory.outcome_service import OutcomeService
                OutcomeService.ensure_snapshots(db, app_rec)

        else:
            cls._record_event(
                db,
                application_id=execution.application_id,
                event_type="SUBMISSION_UNCONFIRMED",
                description="Submission request completed, but observable proof could not be automatically confirmed.",
                metadata=evidence.to_dict(),
            )

        db.commit()
        db.refresh(execution)
        return execution

    @classmethod
    def cancel_execution(
        cls,
        db: Session,
        execution_id: str,
        reason: str = "User cancelled execution",
        application_id: Optional[str] = None,
    ) -> ApplicationExecution:
        """Cancels an active execution attempt."""
        execution = db.query(ApplicationExecution).filter(
            ApplicationExecution.id == execution_id
        ).first()

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution with ID '{execution_id}' not found.",
            )

        if application_id and execution.application_id != application_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution '{execution_id}' does not belong to application '{application_id}'.",
            )

        ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.CANCELLED)
        execution.status = ExecutionStatus.CANCELLED.value
        execution.current_step = f"Cancelled: {reason}"
        execution.requires_user_action = False
        execution.user_action_prompt = None

        cls._record_event(
            db,
            application_id=execution.application_id,
            event_type="EXECUTION_CANCELLED",
            description=f"Execution cancelled: {reason}",
        )

        db.commit()
        db.refresh(execution)
        return execution

    @classmethod
    def get_latest_execution_for_application(
        cls,
        db: Session,
        application_id: str,
    ) -> Optional[ApplicationExecution]:
        """Retrieves the most recent execution attempt for an application."""
        return db.query(ApplicationExecution).filter(
            ApplicationExecution.application_id == application_id
        ).order_by(desc(ApplicationExecution.attempt_number)).first()

    @classmethod
    def get_all_executions_for_application(
        cls,
        db: Session,
        application_id: str,
    ) -> List[ApplicationExecution]:
        """Retrieves full historical list of execution attempts for an application."""
        return db.query(ApplicationExecution).filter(
            ApplicationExecution.application_id == application_id
        ).order_by(desc(ApplicationExecution.attempt_number)).all()

