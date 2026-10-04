import os
from typing import Dict, Any, Optional
from app.services.execution_layer.executors.base import BaseApplicationExecutor
from app.services.execution_layer.models import (
    ExecutorCapabilities,
    ExecutionStatus,
    SubmissionEvidence,
)
from app.services.execution_layer.state_machine import ExecutionStateMachine
from app.models.execution import ApplicationExecution


class ManualExecutor(BaseApplicationExecutor):
    """
    MODE 1: MANUAL Execution Adapter.
    Provides candidate with complete 'Manual Application Kit' containing prepared answers,
    resume file verification, tailored cover letter, and warnings.
    Candidate completes application on external portal, and system audits the workflow.
    """

    source_name: str = "manual"
    capabilities: ExecutorCapabilities = ExecutorCapabilities(
        can_open_url=True,
        can_detect_form=False,
        can_fill_text=False,
        can_upload_resume=False,
        can_select_option=False,
        can_submit=False,
        requires_human_review=True,
    )

    def start_execution(
        self,
        execution: ApplicationExecution,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepares the manual application kit and sets status to AWAITING_USER."""
        candidate = execution.candidate
        job = execution.job
        preparation = execution.preparation

        resume_path = None
        if preparation and preparation.resume_recommendation:
            resume_path = preparation.resume_recommendation.get("file_path")
        if not resume_path and candidate.documents:
            for d in candidate.documents:
                if d.type == "resume" or "resume" in d.name.lower():
                    resume_path = d.file_path
                    break

        resume_exists = bool(resume_path and os.path.exists(resume_path))

        manual_kit = {
            "job_url": job.application_url or f"https://remotive.com/remote-jobs/{job.id}",
            "job_title": job.title,
            "company": job.company,
            "candidate_facts": {
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone or "+91 95652 49247",
                "location": candidate.location or "Lucknow, India",
                "github": (candidate.links or {}).get("github", "https://github.com/itripathiharsh"),
                "linkedin": (candidate.links or {}).get("linkedin", "https://www.linkedin.com/in/iamharshvardhantripathi/"),
                "portfolio": (candidate.links or {}).get("portfolio", "https://harshtripathi.vercel.app/"),
                "experience_years": "2.0 years (verified across 4 industry roles)",
                "education": "B.Tech CSE (BBDITM) & BS Data Science (IIT Madras)",
            },
            "resume": {
                "name": "Harsh_Resume.pdf",
                "file_path": resume_path,
                "exists_on_disk": resume_exists,
                "verified": resume_exists,
            },
            "draft_materials": {
                "cover_letter": (preparation.generated_content or {}).get("cover_letter") if preparation else None,
                "application_summary": (preparation.generated_content or {}).get("application_summary") if preparation else None,
                "short_message": (preparation.generated_content or {}).get("short_message") if preparation else None,
            },
            "screening_answers": preparation.question_answers if preparation else [],
            "warnings": preparation.warnings if preparation else [],
            "human_confirmation_items": preparation.human_confirmation_required if preparation else [],
        }

        # Transition state: NOT_STARTED / READY -> OPENING -> AWAITING_USER
        ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.OPENING)
        execution.status = ExecutionStatus.OPENING.value
        execution.current_step = "Opening manual application portal"
        
        # Next transition to AWAITING_USER
        ExecutionStateMachine.validate_transition(ExecutionStatus.OPENING, ExecutionStatus.AWAITING_USER)
        execution.status = ExecutionStatus.AWAITING_USER.value
        execution.current_step = "Awaiting manual completion by candidate"
        execution.requires_user_action = True
        execution.user_action_prompt = (
            f"Open application URL for {job.title} @ {job.company}. Use the prepared Manual Kit "
            "to fill details, and click 'Confirm Submission' once submitted."
        )
        execution.step_details = {"manual_kit": manual_kit, "action": "manual_kit_ready"}

        return {"status": execution.status, "manual_kit": manual_kit}

    def resume_execution(
        self,
        execution: ApplicationExecution,
        user_inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resumes manual execution when candidate confirms submission or modifies state."""
        action = user_inputs.get("action", "")

        if action == "confirm_submitted":
            evidence = SubmissionEvidence(
                confirmed=True,
                evidence_type="MANUAL_CONFIRMATION",
                details={
                    "confirmed_by_user": True,
                    "submission_notes": user_inputs.get("notes", "Submitted manually by user via portal"),
                },
                confirmation_number=user_inputs.get("confirmation_number"),
                page_url=execution.job.application_url,
            )
            ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.SUBMITTED)
            execution.status = ExecutionStatus.SUBMITTED.value
            execution.current_step = "Application submitted manually and verified by candidate"
            execution.requires_user_action = False
            execution.user_action_prompt = None
            execution.submission_confirmed = True
            execution.confirmation_evidence = evidence.to_dict()
            return {"status": execution.status, "evidence": evidence.to_dict()}

        elif action == "cancel":
            ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.CANCELLED)
            execution.status = ExecutionStatus.CANCELLED.value
            execution.current_step = "Manual execution cancelled by user"
            execution.requires_user_action = False
            execution.user_action_prompt = None
            return {"status": execution.status}

        return {"status": execution.status, "message": "Manual execution awaiting user action"}

    def approve_and_submit(
        self,
        execution: ApplicationExecution,
        context: Dict[str, Any],
    ) -> SubmissionEvidence:
        """Manual executor marks submission as approved and confirmed."""
        evidence = SubmissionEvidence(
            confirmed=True,
            evidence_type="MANUAL_CONFIRMATION",
            details={"approved_by_user": True},
            page_url=execution.job.application_url,
        )
        ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.SUBMITTED)
        execution.status = ExecutionStatus.SUBMITTED.value
        execution.submission_confirmed = True
        execution.confirmation_evidence = evidence.to_dict()
        execution.requires_user_action = False
        return evidence
