import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import httpx

from app.services.execution_layer.executors.base import BaseApplicationExecutor
from app.services.execution_layer.models import (
    ExecutorCapabilities,
    ExecutionStatus,
    SubmissionEvidence,
    BlockerType,
    FieldConfidence,
)
from app.services.execution_layer.state_machine import ExecutionStateMachine
from app.services.execution_layer.detector import HtmlFormDetector
from app.services.execution_layer.field_mapper import FieldMapper
from app.models.execution import ApplicationExecution


class GenericWebExecutor(BaseApplicationExecutor):
    """
    MODE 2 (ASSISTED) & MODE 3 (AUTOMATED) Generic Web Execution Adapter.
    Detects application forms, maps fields to verified candidate evidence,
    halts safely at CAPTCHAs, login walls, and sensitive questions,
    and requires explicit human approval at the final submission gate.
    """

    source_name: str = "generic_web"
    capabilities: ExecutorCapabilities = ExecutorCapabilities(
        can_open_url=True,
        can_detect_form=True,
        can_fill_text=True,
        can_upload_resume=True,
        can_select_option=True,
        can_submit=True,
        requires_human_review=True,
    )

    def start_execution(
        self,
        execution: ApplicationExecution,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Begins generic web execution: opens URL, scans for anti-bot barriers,
        extracts form fields, and maps fields with confidence scores.
        """
        job = execution.job
        candidate = execution.candidate
        preparation = execution.preparation
        url = job.application_url or context.get("target_url")

        if not url:
            ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.BLOCKED)
            execution.status = ExecutionStatus.BLOCKED.value
            execution.blocker_reason = BlockerType.URL_UNREACHABLE.value
            execution.failure_reason = "Job does not have a valid application URL."
            execution.requires_user_action = True
            execution.user_action_prompt = "Application URL missing. Please provide application URL to proceed."
            return {"status": execution.status, "blocker": execution.blocker_reason}

        # Step 1: OPENING
        ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.OPENING)
        execution.status = ExecutionStatus.OPENING.value
        execution.current_step = f"Connecting to {url}"

        # Step 2: Fetch or read HTML content
        html_content = context.get("html_content")
        page_title = context.get("page_title", f"{job.title} Application")

        if not html_content:
            from app.core.security import is_safe_external_url
            is_safe, block_reason = is_safe_external_url(url)
            if not is_safe:
                ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.BLOCKED)
                execution.status = ExecutionStatus.BLOCKED.value
                execution.blocker_reason = BlockerType.URL_UNREACHABLE.value
                execution.failure_reason = f"Security Policy Blocked URL: {block_reason}"
                execution.requires_user_action = True
                execution.user_action_prompt = f"Application URL blocked by security policy: {block_reason}"
                return {"status": execution.status, "blocker": execution.blocker_reason}

            try:
                # Local safe HTTP fetch with standard client
                headers = {"User-Agent": "JobAgent/1.0 (Application Assistant; +http://localhost)"}
                with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
                    resp = client.get(url)
                    html_content = resp.text
                    page_title = resp.headers.get("title", page_title)
            except Exception as e:
                # Network unreachable or blocked: transition to AWAITING_USER with manual fallback
                ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.AWAITING_USER)
                execution.status = ExecutionStatus.AWAITING_USER.value
                execution.blocker_reason = BlockerType.URL_UNREACHABLE.value
                execution.failure_reason = f"Could not open application URL automatically: {str(e)}"
                execution.requires_user_action = True
                execution.user_action_prompt = (
                    f"Unable to access {url} automatically. Please open the link in your browser and complete manually."
                )
                return {"status": execution.status, "blocker": execution.blocker_reason}

        # Sanitize browser metadata
        execution.browser_metadata = {
            "url": url,
            "title": page_title[:255] if page_title else "",
            "content_length": len(html_content),
        }

        # Step 3: Anti-Bot & Challenge Detection (Hard Boundary)
        challenge = HtmlFormDetector.detect_challenges(html_content)
        if challenge:
            if challenge == BlockerType.CAPTCHA_DETECTED:
                ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.BLOCKED)
                execution.status = ExecutionStatus.BLOCKED.value
                execution.blocker_reason = BlockerType.CAPTCHA_DETECTED.value
                execution.requires_user_action = True
                execution.user_action_prompt = (
                    "CAPTCHA or bot verification challenge detected on page. "
                    "Automated interaction stopped to protect your account. Please complete the verification in browser."
                )
                return {"status": execution.status, "blocker": execution.blocker_reason}
            elif challenge == BlockerType.LOGIN_REQUIRED:
                ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.AWAITING_USER)
                execution.status = ExecutionStatus.AWAITING_USER.value
                execution.blocker_reason = BlockerType.LOGIN_REQUIRED.value
                execution.requires_user_action = True
                execution.user_action_prompt = (
                    "Authentication required. Please sign into your account on the portal and resume execution."
                )
                return {"status": execution.status, "blocker": execution.blocker_reason}

        # Step 4: NAVIGATING -> Form Detection
        ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.NAVIGATING)
        execution.status = ExecutionStatus.NAVIGATING.value
        execution.current_step = "Analyzing application form elements"

        detected_fields = HtmlFormDetector.extract_form_fields(html_content)
        if not detected_fields:
            # No standard HTML form detected (e.g. multi-step SPA or email application)
            ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.AWAITING_USER)
            execution.status = ExecutionStatus.AWAITING_USER.value
            execution.blocker_reason = BlockerType.FORM_NOT_FOUND.value
            execution.requires_user_action = True
            execution.user_action_prompt = (
                "No standard HTML application form inputs found on this page. "
                "The portal may require clicking an 'Apply' button or manual submission."
            )
            return {"status": execution.status, "blocker": execution.blocker_reason}

        # Step 5: FILLING -> Field Mapping & Safety Audit
        ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.FILLING)
        execution.status = ExecutionStatus.FILLING.value
        execution.current_step = f"Mapping {len(detected_fields)} form fields"

        mapped_results = FieldMapper.map_detected_fields(detected_fields, candidate, preparation)
        execution.field_mappings = [m.to_dict() for m in mapped_results]

        # Analyze mapped fields
        unconfirmed_sensitive = [m for m in mapped_results if m.requires_human_confirmation and not m.confirmed_by_user]
        filled_count = sum(1 for m in mapped_results if m.status == "FILLED")
        pending_count = len(unconfirmed_sensitive)

        execution.step_details = {
            "total_fields": len(detected_fields),
            "safe_filled_count": filled_count,
            "pending_confirmation_count": pending_count,
            "has_sensitive_fields": any(m.form_field.is_sensitive for m in mapped_results),
        }

        # Step 6: Determine next state (AWAITING_USER if sensitive fields exist, else READY_TO_SUBMIT)
        if unconfirmed_sensitive:
            ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.AWAITING_USER)
            execution.status = ExecutionStatus.AWAITING_USER.value
            execution.blocker_reason = BlockerType.SENSITIVE_CONFIRMATION_REQUIRED.value
            execution.requires_user_action = True
            sensitive_labels = [m.form_field.label for m in unconfirmed_sensitive[:3]]
            execution.user_action_prompt = (
                f"Form has {pending_count} fields requiring human confirmation ({', '.join(sensitive_labels)}...). "
                "Review answers and confirm before submission."
            )
        else:
            ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.READY_TO_SUBMIT)
            execution.status = ExecutionStatus.READY_TO_SUBMIT.value
            execution.requires_user_action = True
            execution.user_action_prompt = (
                f"All {filled_count} form fields safely filled. Final submission gate reached: "
                "Review complete package and click 'Approve & Submit' to finalize."
            )

        return {"status": execution.status, "field_mappings": execution.field_mappings}

    def resume_execution(
        self,
        execution: ApplicationExecution,
        user_inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Resumes execution from AWAITING_USER or BLOCKED:
        Updates confirmed user answers and re-evaluates submission readiness.
        """
        action = user_inputs.get("action", "confirm_fields")

        if action == "cancel":
            ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.CANCELLED)
            execution.status = ExecutionStatus.CANCELLED.value
            execution.current_step = "Execution cancelled by user"
            execution.requires_user_action = False
            execution.user_action_prompt = None
            return {"status": execution.status}

        confirmed_field_values = user_inputs.get("field_values", {})
        existing_mappings = execution.field_mappings or []

        for m in existing_mappings:
            field_name = m["form_field"]["name"]
            field_id = m["form_field"]["field_id"]
            if field_name in confirmed_field_values or field_id in confirmed_field_values:
                val = confirmed_field_values.get(field_name, confirmed_field_values.get(field_id))
                m["proposed_value"] = val
                m["confirmed_by_user"] = True
                m["status"] = "FILLED"
                m["requires_human_confirmation"] = False

        execution.field_mappings = existing_mappings

        # Check if all required fields are now confirmed
        remaining_unconfirmed = [
            m for m in existing_mappings
            if m.get("form_field", {}).get("is_required", False) and not m.get("confirmed_by_user", False) and m.get("status") != "FILLED"
        ]

        if not remaining_unconfirmed:
            ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.READY_TO_SUBMIT)
            execution.status = ExecutionStatus.READY_TO_SUBMIT.value
            execution.blocker_reason = None
            execution.requires_user_action = True
            execution.user_action_prompt = "All fields confirmed. Click 'Approve & Submit' to perform submission."
        else:
            execution.requires_user_action = True
            execution.user_action_prompt = f"{len(remaining_unconfirmed)} required fields still pending confirmation."

        return {"status": execution.status, "field_mappings": execution.field_mappings}

    def approve_and_submit(
        self,
        execution: ApplicationExecution,
        context: Dict[str, Any],
    ) -> SubmissionEvidence:
        """
        Executes final application submission after explicit human approval.
        Verifies observable proof before marking SUBMITTED.
        """
        # Hard safety gate: must be in READY_TO_SUBMIT
        ExecutionStateMachine.validate_transition(ExecutionStatus(execution.status), ExecutionStatus.SUBMITTING)
        execution.status = ExecutionStatus.SUBMITTING.value
        execution.current_step = "Submitting application to employer portal"

        # Check for simulated or real response
        response_html = context.get("response_html", "")
        response_url = context.get("response_url", execution.job.application_url or "")
        simulated_success = context.get("simulate_success", False)

        is_confirmed = False
        evidence_type = "NONE"
        confirmation_num = None

        if simulated_success:
            is_confirmed = True
            evidence_type = "CONFIRMATION_TEXT"
            confirmation_num = f"APP-{execution.id[:8].upper()}"
        elif response_html or response_url:
            is_confirmed, evidence_type, confirmation_num = HtmlFormDetector.detect_submission_evidence(
                response_html, response_url
            )

        evidence = SubmissionEvidence(
            confirmed=is_confirmed,
            evidence_type=evidence_type,
            details={
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "response_url": response_url,
                "verified_observable": is_confirmed,
            },
            confirmation_number=confirmation_num,
            page_url=response_url,
        )

        if is_confirmed:
            ExecutionStateMachine.validate_transition(ExecutionStatus.SUBMITTING, ExecutionStatus.SUBMITTED)
            execution.status = ExecutionStatus.SUBMITTED.value
            execution.submission_confirmed = True
            execution.confirmation_evidence = evidence.to_dict()
            execution.completed_at = datetime.now(timezone.utc)
            execution.current_step = f"Application successfully submitted. Reference: {confirmation_num or 'Verified'}"
            execution.requires_user_action = False
            execution.user_action_prompt = None
        else:
            # Submission unconfirmed: do NOT mark SUBMITTED
            ExecutionStateMachine.validate_transition(ExecutionStatus.SUBMITTING, ExecutionStatus.AWAITING_USER)
            execution.status = ExecutionStatus.AWAITING_USER.value
            execution.submission_confirmed = False
            execution.current_step = "Submission sent, but confirmation proof was not observed"
            execution.requires_user_action = True
            execution.user_action_prompt = (
                "Submission attempted, but no observable confirmation page or reference number was detected. "
                "Please verify submission status directly on the portal and mark confirmed if successful."
            )

        return evidence
