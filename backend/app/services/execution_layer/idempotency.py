from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.models.application import Application
from app.models.execution import ApplicationExecution
from app.services.execution_layer.models import ExecutionStatus


class DuplicateSubmissionGuard:
    """
    Prevents accidental double submissions and ensures idempotency.
    Enforces that an application cannot be automatically submitted twice.
    """

    @classmethod
    def check_application_eligibility(
        cls,
        db: Session,
        application_id: str,
        allow_force: bool = False,
    ) -> Tuple[bool, str, Optional[ApplicationExecution]]:
        """
        Validates whether an application can safely begin or continue an execution attempt.
        Returns: (is_eligible, reason, prior_successful_execution)
        """
        app_record = db.query(Application).filter(Application.id == application_id).first()
        if not app_record:
            return False, f"Application with ID '{application_id}' does not exist.", None

        # 1. Check if application status is already marked as submitted
        if app_record.status == "submitted" and not allow_force:
            # Look for prior successful execution
            prior_exec = db.query(ApplicationExecution).filter(
                ApplicationExecution.application_id == application_id,
                ApplicationExecution.status == ExecutionStatus.SUBMITTED.value,
            ).first()
            return (
                False,
                f"Application is already marked as 'submitted' on {app_record.applied_at or 'record'}. "
                "Automatic re-submission is strictly blocked to prevent double applications.",
                prior_exec
            )

        # 2. Check if any prior execution attempt for this application reached SUBMITTED
        successful_exec = db.query(ApplicationExecution).filter(
            ApplicationExecution.application_id == application_id,
            ApplicationExecution.status == ExecutionStatus.SUBMITTED.value,
        ).first()

        if successful_exec and not allow_force:
            return (
                False,
                f"Execution attempt #{successful_exec.attempt_number} already successfully submitted this application. "
                "Duplicate execution blocked.",
                successful_exec
            )

        # 3. Check for sibling applications on the same canonical job
        if app_record.job_id:
            sibling_submitted = db.query(Application).filter(
                Application.job_id == app_record.job_id,
                Application.candidate_id == app_record.candidate_id,
                Application.id != app_record.id,
                Application.status == "submitted",
            ).first()
            if sibling_submitted and not allow_force:
                return (
                    False,
                    f"Candidate has already submitted application '{sibling_submitted.id}' for this job. Duplicate prevented.",
                    None
                )

        return True, "Application is eligible for execution.", None
