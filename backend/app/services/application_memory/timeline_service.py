from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.application import Application, ApplicationEvent, ApplicationNote, ApplicationOverride
from app.models.preparation import ApplicationPreparation
from app.models.execution import ApplicationExecution
from app.models.decision import ApplicationDecision
from app.services.application_memory.models import TimelineItem, TimelineEventType


class TimelineService:
    """
    Step 10: Chronological Timeline Service.
    Reconstructs the full end-to-end provenance and history of an application
    from creation to decision, preparation, execution, user notes, overrides,
    and post-application interview/offer/rejection outcomes.
    """

    @staticmethod
    def get_application_timeline(db: Session, application_id: str) -> List[TimelineItem]:
        """
        Gathers all events, notes, overrides, and execution milestones for an application,
        sorting them chronologically to show complete provenance.
        """
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            return []

        timeline: List[TimelineItem] = []

        # 1. Base Application Creation
        timeline.append(
            TimelineItem(
                id=f"app-created-{app.id}",
                timestamp=app.created_at,
                event_type=TimelineEventType.APPLICATION_CREATED.value,
                title="Application Record Initialized",
                description=f"Application tracking initialized (Source: {app.source or 'Direct'}).",
                actor="user" if app.source == "manual" else "system",
                provenance="USER_CONFIRMED" if app.source == "manual" else "SYSTEM_DETECTED",
                metadata={"status": app.status, "lifecycle_stage": app.lifecycle_stage},
            )
        )

        # 2. Decision Record (if job_id and candidate_id exist)
        if app.job_id and app.candidate_id:
            decision = (
                db.query(ApplicationDecision)
                .filter_by(job_id=app.job_id, candidate_id=app.candidate_id)
                .first()
            )
            if decision:
                timeline.append(
                    TimelineItem(
                        id=f"decision-{decision.id}",
                        timestamp=decision.decided_at or decision.created_at,
                        event_type=TimelineEventType.DECISION_EVALUATED.value,
                        title=f"Decision Evaluated: {decision.decision}",
                        description=f"Decision Engine recommended {decision.decision} (Confidence: {int(decision.confidence_score * 100)}%, Risk: {decision.risk_level}).",
                        actor="system",
                        provenance="SYSTEM_DETECTED",
                        metadata={
                            "decision": decision.decision,
                            "reasons": decision.reasons or [],
                            "risk_level": decision.risk_level,
                            "engine_version": decision.engine_version,
                        },
                    )
                )

        # 3. Preparation Package Milestones
        if app.preparation:
            prep = app.preparation
            timeline.append(
                TimelineItem(
                    id=f"prep-{prep.id}",
                    timestamp=prep.prepared_at or prep.created_at,
                    event_type=TimelineEventType.PREPARATION_GENERATED.value,
                    title=f"Preparation Package Ready ({prep.readiness_status})",
                    description=f"Generated tailored materials (Score: {prep.readiness_score:.1f}/100, Version: {prep.version}).",
                    actor="system",
                    provenance="SYSTEM_DETECTED",
                    metadata={
                        "readiness_status": prep.readiness_status,
                        "readiness_score": prep.readiness_score,
                        "resume": prep.resume_recommendation.get("selected_resume") if prep.resume_recommendation else None,
                        "version": prep.version,
                    },
                )
            )

        # 4. Executions Milestones
        executions = (
            db.query(ApplicationExecution)
            .filter_by(application_id=app.id)
            .order_by(ApplicationExecution.attempt_number)
            .all()
        )
        for ex in executions:
            timeline.append(
                TimelineItem(
                    id=f"exec-{ex.id}-start",
                    timestamp=ex.started_at,
                    event_type=TimelineEventType.EXECUTION_ATTEMPT.value,
                    title=f"Execution Attempt #{ex.attempt_number} ({ex.mode})",
                    description=f"Started application execution via {ex.source} adapter in {ex.mode} mode. Status: {ex.status}.",
                    actor="user" if ex.mode == "MANUAL" else "system",
                    provenance="USER_CONFIRMED" if ex.mode == "MANUAL" else "SYSTEM_DETECTED",
                    metadata={
                        "attempt": ex.attempt_number,
                        "mode": ex.mode,
                        "status": ex.status,
                        "blocker": ex.blocker_reason,
                    },
                )
            )
            if ex.completed_at and ex.submission_confirmed:
                timeline.append(
                    TimelineItem(
                        id=f"exec-{ex.id}-submitted",
                        timestamp=ex.completed_at,
                        event_type=TimelineEventType.APPLICATION_SUBMITTED.value,
                        title=f"Submission Confirmed (Attempt #{ex.attempt_number})",
                        description="Application successfully submitted and verified with positive confirmation evidence.",
                        actor="user",
                        provenance="USER_CONFIRMED",
                        metadata={
                            "attempt": ex.attempt_number,
                            "evidence": ex.confirmation_evidence or {},
                        },
                    )
                )

        # 5. Application Events Log
        events = (
            db.query(ApplicationEvent)
            .filter_by(application_id=app.id)
            .order_by(ApplicationEvent.created_at)
            .all()
        )
        for ev in events:
            # Skip duplicates of basic creation if already captured
            if ev.event_type == "application_created":
                continue
            timeline.append(
                TimelineItem(
                    id=f"event-{ev.id}",
                    timestamp=ev.created_at,
                    event_type=ev.event_type,
                    title=f"Event: {ev.event_type.replace('_', ' ').title()}",
                    description=ev.description or "Application lifecycle event recorded.",
                    actor=ev.actor or "system",
                    provenance=ev.provenance or "SYSTEM_DETECTED",
                    metadata=ev.event_metadata or {},
                )
            )

        # 6. User Notes
        notes = (
            db.query(ApplicationNote)
            .filter_by(application_id=app.id)
            .order_by(ApplicationNote.created_at)
            .all()
        )
        for note in notes:
            timeline.append(
                TimelineItem(
                    id=f"note-{note.id}",
                    timestamp=note.created_at,
                    event_type=TimelineEventType.USER_NOTE_ADDED.value,
                    title=f"Note ({note.category.title()})",
                    description=note.content,
                    actor=note.author or "user",
                    provenance="USER_CONFIRMED",
                    metadata={"category": note.category, "author": note.author},
                )
            )

        # 7. User Decision Overrides
        overrides = (
            db.query(ApplicationOverride)
            .filter_by(application_id=app.id)
            .order_by(ApplicationOverride.created_at)
            .all()
        )
        for ov in overrides:
            timeline.append(
                TimelineItem(
                    id=f"override-{ov.id}",
                    timestamp=ov.created_at,
                    event_type=TimelineEventType.USER_OVERRIDE_RECORDED.value,
                    title=f"Decision Override: {ov.original_decision} → {ov.override_decision}",
                    description=f"User manually overrode system recommendation. Reason: {ov.reason or 'No reason specified'}",
                    actor="user",
                    provenance="USER_CONFIRMED",
                    metadata={
                        "original_decision": ov.original_decision,
                        "override_decision": ov.override_decision,
                        "override_type": ov.override_type,
                        "reason": ov.reason,
                    },
                )
            )

        # 8. Sort Chronologically (oldest to newest)
        timeline.sort(key=lambda item: item.timestamp)
        return timeline
