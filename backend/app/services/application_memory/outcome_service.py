from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.models.profile import CandidateProfile
from app.models.decision import ApplicationDecision
from app.models.matching import MatchResult
from app.models.preparation import ApplicationPreparation
from app.models.execution import ApplicationExecution
from app.services.application_memory.models import (
    LifecycleStage,
    OutcomeCategory,
    OutcomeProvenance,
    RejectionCategory,
)
from app.services.application_memory.snapshot_service import SnapshotService


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OutcomeService:
    """
    Step 10: Structured Outcome and Provenance Management.
    Enforces deterministic validation of application outcomes, provenance tracking,
    rejection categorization, and append-only event logging.
    Guards strictly against confusing 'NO_RESPONSE' with 'REJECTED'.
    """

    POSITIVE_STAGES = {
        LifecycleStage.SCREENING.value,
        LifecycleStage.INTERVIEW.value,
        LifecycleStage.OFFER.value,
        LifecycleStage.ACCEPTED.value,
    }

    NEGATIVE_STAGES = {
        LifecycleStage.REJECTED.value,
        LifecycleStage.WITHDRAWN.value,
        LifecycleStage.EXPIRED.value,
    }

    PENDING_STAGES = {
        LifecycleStage.NOT_STARTED.value,
        LifecycleStage.PREPARED.value,
        LifecycleStage.IN_PROGRESS.value,
        LifecycleStage.AWAITING_USER.value,
        LifecycleStage.SUBMITTED.value,
        LifecycleStage.ACKNOWLEDGED.value,
        LifecycleStage.NO_RESPONSE.value,
    }

    @classmethod
    def determine_outcome_category(cls, stage: str) -> str:
        if stage in cls.POSITIVE_STAGES:
            return OutcomeCategory.POSITIVE.value
        elif stage in cls.NEGATIVE_STAGES:
            return OutcomeCategory.NEGATIVE.value
        return OutcomeCategory.PENDING.value

    @classmethod
    def ensure_snapshots(cls, db: Session, application: Application) -> None:
        """
        Ensures that immutable context snapshots exist on the Application record.
        Captures point-in-time candidate profile, job posting, decision, and artifacts
        if they were not already captured.
        """
        updated = False

        if not application.job_snapshot and application.job_id:
            job = db.query(Job).filter(Job.id == application.job_id).first()
            if job:
                application.job_snapshot = SnapshotService.capture_job_snapshot(job)
                updated = True

        if not application.candidate_snapshot and application.candidate_id:
            candidate = db.query(CandidateProfile).filter(CandidateProfile.id == application.candidate_id).first()
            if candidate:
                application.candidate_snapshot = SnapshotService.capture_candidate_snapshot(candidate)
                updated = True

        if not application.decision_snapshot and application.job_id and application.candidate_id:
            decision = (
                db.query(ApplicationDecision)
                .filter_by(job_id=application.job_id, candidate_id=application.candidate_id)
                .first()
            )
            match = (
                db.query(MatchResult)
                .filter_by(job_id=application.job_id, candidate_id=application.candidate_id)
                .first()
            )
            application.decision_snapshot = SnapshotService.capture_decision_snapshot(decision, match)
            updated = True

        if not application.artifacts_snapshot:
            prep = (
                db.query(ApplicationPreparation)
                .filter_by(application_id=application.id)
                .first()
            )
            latest_exec = (
                db.query(ApplicationExecution)
                .filter_by(application_id=application.id)
                .order_by(ApplicationExecution.attempt_number.desc())
                .first()
            )
            application.artifacts_snapshot = SnapshotService.capture_artifacts_snapshot(prep, latest_exec)
            updated = True

        if updated:
            db.flush()

    @classmethod
    def update_outcome(
        cls,
        db: Session,
        application_id: str,
        lifecycle_stage: str,
        provenance: str = OutcomeProvenance.USER_CONFIRMED.value,
        rejection_category: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        notes: Optional[str] = None,
        actor: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Application:
        """
        Updates application lifecycle stage and outcome attributes while preserving
        full auditability and provenance.
        """
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' not found.",
            )

        # 1. Validate Lifecycle Stage Enum
        valid_stages = {s.value for s in LifecycleStage}
        if lifecycle_stage not in valid_stages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid lifecycle stage '{lifecycle_stage}'. Valid options: {sorted(valid_stages)}",
            )

        # 2. Validate Provenance Enum
        valid_provenances = {p.value for p in OutcomeProvenance}
        if provenance not in valid_provenances:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provenance '{provenance}'. Valid options: {sorted(valid_provenances)}",
            )

        # 3. Validate Rejection Category if stage is REJECTED
        if lifecycle_stage == LifecycleStage.REJECTED.value:
            valid_rejection_cats = {r.value for r in RejectionCategory}
            if rejection_category and rejection_category not in valid_rejection_cats:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid rejection category '{rejection_category}'. Valid options: {sorted(valid_rejection_cats)}",
                )
            if not rejection_category:
                rejection_category = RejectionCategory.UNKNOWN.value
        else:
            # Not a rejection; clear rejection fields unless explicitly provided for history
            if lifecycle_stage != LifecycleStage.REJECTED.value and not rejection_category:
                rejection_category = None
                rejection_reason = None

        # 4. Guarantee Initial Snapshots exist
        cls.ensure_snapshots(db, app)

        old_stage = app.lifecycle_stage
        old_status = app.status

        # 5. Apply State Updates
        app.lifecycle_stage = lifecycle_stage
        app.outcome_category = cls.determine_outcome_category(lifecycle_stage)
        app.outcome_provenance = provenance
        app.rejection_category = rejection_category
        app.rejection_reason = rejection_reason
        app.last_outcome_date = get_utc_now()
        app.updated_at = get_utc_now()

        # Update legacy status for backward compatibility
        legacy_map = {
            LifecycleStage.NOT_STARTED.value: "draft",
            LifecycleStage.PREPARED.value: "preparation",
            LifecycleStage.IN_PROGRESS.value: "preparation",
            LifecycleStage.AWAITING_USER.value: "human_action_required",
            LifecycleStage.SUBMITTED.value: "submitted",
            LifecycleStage.ACKNOWLEDGED.value: "submitted",
            LifecycleStage.SCREENING.value: "assessment",
            LifecycleStage.INTERVIEW.value: "interview",
            LifecycleStage.OFFER.value: "offer",
            LifecycleStage.ACCEPTED.value: "offer",
            LifecycleStage.REJECTED.value: "rejected",
            LifecycleStage.WITHDRAWN.value: "rejected",
            LifecycleStage.EXPIRED.value: "rejected",
            LifecycleStage.NO_RESPONSE.value: "submitted",
        }
        app.status = legacy_map.get(lifecycle_stage, app.status)

        # 6. Append Immutable ApplicationEvent
        event_meta = metadata or {}
        event_meta.update({
            "previous_lifecycle_stage": old_stage,
            "new_lifecycle_stage": lifecycle_stage,
            "previous_status": old_status,
            "new_status": app.status,
            "outcome_category": app.outcome_category,
            "provenance": provenance,
            "rejection_category": rejection_category,
            "rejection_reason": rejection_reason,
            "notes": notes,
        })

        event = ApplicationEvent(
            application_id=app.id,
            event_type="OUTCOME_RECORDED",
            description=f"Lifecycle transition from {old_stage} to {lifecycle_stage} recorded ({provenance}).",
            actor=actor,
            provenance=provenance,
            event_metadata=event_meta,
        )
        db.add(event)
        db.commit()
        db.refresh(app)
        return app
