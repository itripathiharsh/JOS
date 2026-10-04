import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.application import Application, ApplicationEvent
from app.models.preparation import ApplicationPreparation
from app.models.profile import CandidateProfile
from app.models.job import Job
from app.models.automation import ApplicationApproval

logger = logging.getLogger(__name__)


def get_utc_now():
    return datetime.now(timezone.utc)


class ApplicationApprovalService:
    """
    Step 12: Human-in-the-loop Submission Approval Gate.
    Ensures that background automation can NEVER submit an application without
    explicit, unexpired, version-bound human approval.
    """

    @classmethod
    def request_approval(
        cls,
        db: Session,
        application_id: str,
        candidate_id: str,
        notes: Optional[str] = None,
    ) -> ApplicationApproval:
        """
        Creates or retrieves a PENDING approval request for an application.
        """
        app_record = db.query(Application).filter(Application.id == application_id).first()
        if not app_record:
            raise ValueError(f"Application {application_id} not found.")

        prep = db.query(ApplicationPreparation).filter(
            ApplicationPreparation.application_id == application_id
        ).first()

        prep_version = prep.version if prep else 1
        prep_id = prep.id if prep else None

        existing = db.query(ApplicationApproval).filter(
            ApplicationApproval.application_id == application_id,
            ApplicationApproval.approval_status == "PENDING",
            ApplicationApproval.preparation_version == prep_version,
        ).first()

        if existing:
            return existing

        approval = ApplicationApproval(
            application_id=application_id,
            job_id=app_record.job_id or "",
            candidate_id=candidate_id,
            preparation_id=prep_id,
            preparation_version=prep_version,
            approved_by="candidate",
            approval_scope="SINGLE_SUBMISSION",
            approval_status="PENDING",
            notes=notes,
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        return approval

    @classmethod
    def grant_approval(
        cls,
        db: Session,
        application_id: str,
        candidate_id: str,
        scope: str = "SINGLE_SUBMISSION",
        expires_hours: int = 48,
        notes: Optional[str] = None,
    ) -> ApplicationApproval:
        """
        Explicitly grants human approval to submit an application.
        Strictly binds to the current version of the preparation package.
        """
        app_record = db.query(Application).filter(Application.id == application_id).first()
        if not app_record:
            raise ValueError(f"Application {application_id} not found.")

        prep = db.query(ApplicationPreparation).filter(
            ApplicationPreparation.application_id == application_id
        ).first()

        if not prep or prep.readiness_status != "READY":
            status_desc = prep.readiness_status if prep else "MISSING"
            raise ValueError(
                f"Cannot approve submission: Preparation package is not READY (current: '{status_desc}'). "
                "Resolve all review items before granting submission approval."
            )

        now = get_utc_now()
        expires_at = now + timedelta(hours=expires_hours)

        # Invalidate any prior pending or approved approvals
        prior_approvals = db.query(ApplicationApproval).filter(
            ApplicationApproval.application_id == application_id,
            ApplicationApproval.approval_status.in_(["PENDING", "APPROVED"]),
        ).all()
        for prior in prior_approvals:
            prior.approval_status = "REVOKED"
            prior.revoked_at = now

        approval = ApplicationApproval(
            application_id=application_id,
            job_id=app_record.job_id or "",
            candidate_id=candidate_id,
            preparation_id=prep.id,
            preparation_version=prep.version,
            approved_by="candidate",
            approved_at=now,
            approval_scope=scope,
            expires_at=expires_at,
            approval_status="APPROVED",
            notes=notes or "Candidate explicitly approved submission package.",
        )
        db.add(approval)

        # Audit event in application memory
        event = ApplicationEvent(
            application_id=application_id,
            event_type="SUBMISSION_APPROVAL_GRANTED",
            description=f"Candidate granted submission approval for preparation v{prep.version} (expires in {expires_hours}h).",
            actor="candidate",
            provenance="USER_CONFIRMED",
            event_metadata={
                "preparation_version": prep.version,
                "scope": scope,
                "expires_at": expires_at.isoformat(),
            },
        )
        db.add(event)

        db.commit()
        db.refresh(approval)
        logger.info(f"Human submission approval GRANTED for application {application_id} (prep v{prep.version}).")
        return approval

    @classmethod
    def revoke_approval(
        cls,
        db: Session,
        application_id: str,
        reason: str = "Candidate revoked approval",
    ) -> Optional[ApplicationApproval]:
        """Revokes any active submission approval for an application."""
        now = get_utc_now()
        approvals = db.query(ApplicationApproval).filter(
            ApplicationApproval.application_id == application_id,
            ApplicationApproval.approval_status == "APPROVED",
        ).all()

        last_revoked = None
        for approval in approvals:
            approval.approval_status = "REVOKED"
            approval.revoked_at = now
            approval.notes = reason
            last_revoked = approval

        if last_revoked:
            event = ApplicationEvent(
                application_id=application_id,
                event_type="SUBMISSION_APPROVAL_REVOKED",
                description=f"Submission approval revoked: {reason}",
                actor="candidate",
                provenance="USER_CONFIRMED",
            )
            db.add(event)
            db.commit()
            db.refresh(last_revoked)
            logger.info(f"Submission approval REVOKED for application {application_id}.")

        return last_revoked

    @classmethod
    def validate_approval_for_submission(
        cls,
        db: Session,
        application_id: str,
    ) -> Tuple[bool, str, Optional[ApplicationApproval]]:
        """
        CRITICAL SAFETY CHECK:
        Evaluates whether an application has valid, active, unexpired human approval
        that matches the current preparation package, candidate profile, and job.
        
        Returns: (is_valid: bool, reason: str, approval_record: Optional[ApplicationApproval])
        """
        approval = (
            db.query(ApplicationApproval)
            .filter(ApplicationApproval.application_id == application_id)
            .order_by(ApplicationApproval.created_at.desc())
            .first()
        )

        if not approval:
            return (
                False,
                "Submission strictly BLOCKED: No explicit human approval record exists for this application. "
                "Candidate must explicitly authorize submission.",
                None,
            )

        if approval.approval_status != "APPROVED":
            return (
                False,
                f"Submission strictly BLOCKED: Human approval status is '{approval.approval_status}'. "
                "Explicit candidate approval is required.",
                approval,
            )

        now = get_utc_now()

        # Check expiration
        if approval.expires_at and approval.expires_at < now:
            approval.approval_status = "EXPIRED"
            db.commit()
            return (
                False,
                f"Submission strictly BLOCKED: Human approval expired at {approval.expires_at.isoformat()}. "
                "Fresh authorization required.",
                approval,
            )

        # Check preparation version binding
        prep = db.query(ApplicationPreparation).filter(
            ApplicationPreparation.application_id == application_id
        ).first()

        if not prep:
            return (
                False,
                "Submission strictly BLOCKED: Preparation package not found.",
                approval,
            )

        if prep.version != approval.preparation_version:
            approval.approval_status = "EXPIRED"
            db.commit()
            return (
                False,
                f"Submission strictly BLOCKED: Preparation package was updated to v{prep.version} "
                f"(approved was v{approval.preparation_version}). Fresh approval is required for the new content.",
                approval,
            )

        # Check Candidate Profile freshness
        candidate = db.query(CandidateProfile).filter(CandidateProfile.id == approval.candidate_id).first()
        if candidate and candidate.updated_at and candidate.updated_at > approval.approved_at:
            approval.approval_status = "EXPIRED"
            db.commit()
            return (
                False,
                "Submission strictly BLOCKED: Candidate profile was updated after approval was granted. "
                "Fresh approval required to confirm alignment.",
                approval,
            )

        # Check Job freshness
        job = db.query(Job).filter(Job.id == approval.job_id).first()
        if job and job.updated_at and job.updated_at > approval.approved_at:
            approval.approval_status = "EXPIRED"
            db.commit()
            return (
                False,
                "Submission strictly BLOCKED: Job requirements were updated after approval was granted. "
                "Fresh approval required.",
                approval,
            )

        return (True, "Human approval is valid, active, and version-aligned.", approval)
