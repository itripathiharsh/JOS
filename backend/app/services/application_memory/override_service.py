from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.application import Application, ApplicationOverride, ApplicationEvent
from app.models.decision import ApplicationDecision


class OverrideService:
    """
    Step 10: User Decision Override Tracking Service.
    Records every instance where a candidate overrides the Decision Engine's recommendation
    (e.g., system recommended SKIP, but candidate decides to APPLY).
    Guarantees the original decision is NEVER erased or rewritten.
    """

    @staticmethod
    def record_override(
        db: Session,
        application_id: str,
        override_decision: str,
        original_decision: Optional[str] = None,
        override_type: str = "decision",
        reason: Optional[str] = None,
    ) -> ApplicationOverride:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' not found.",
            )

        # If original_decision not provided, look it up from ApplicationDecision or decision_snapshot
        if not original_decision:
            if app.decision_snapshot and "decision" in app.decision_snapshot:
                original_decision = app.decision_snapshot["decision"]
            elif app.job_id and app.candidate_id:
                dec = (
                    db.query(ApplicationDecision)
                    .filter_by(job_id=app.job_id, candidate_id=app.candidate_id)
                    .first()
                )
                if dec:
                    original_decision = dec.decision

        if not original_decision:
            original_decision = "REVIEW"

        override = ApplicationOverride(
            application_id=app.id,
            original_decision=original_decision,
            override_decision=override_decision,
            override_type=override_type,
            reason=reason,
        )
        db.add(override)
        db.flush()

        event = ApplicationEvent(
            application_id=app.id,
            event_type="USER_OVERRIDE_RECORDED",
            description=f"User override recorded: {original_decision} → {override_decision}.",
            actor="user",
            provenance="USER_CONFIRMED",
            event_metadata={
                "override_id": override.id,
                "original_decision": original_decision,
                "override_decision": override_decision,
                "override_type": override_type,
                "reason": reason,
            },
        )
        db.add(event)
        db.commit()
        db.refresh(override)
        return override

    @staticmethod
    def get_overrides(db: Session, application_id: str) -> List[ApplicationOverride]:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application with ID '{application_id}' not found.",
            )
        return (
            db.query(ApplicationOverride)
            .filter_by(application_id=application_id)
            .order_by(ApplicationOverride.created_at.desc())
            .all()
        )
