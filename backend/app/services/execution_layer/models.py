from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class ExecutionMode(str, Enum):
    MANUAL = "MANUAL"
    ASSISTED = "ASSISTED"
    AUTOMATED = "AUTOMATED"


class ExecutionStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    READY = "READY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    OPENING = "OPENING"
    NAVIGATING = "NAVIGATING"
    FILLING = "FILLING"
    AWAITING_USER = "AWAITING_USER"
    READY_TO_SUBMIT = "READY_TO_SUBMIT"
    SUBMITTING = "SUBMITTING"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class FieldConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class BlockerType(str, Enum):
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    SENSITIVE_CONFIRMATION_REQUIRED = "SENSITIVE_CONFIRMATION_REQUIRED"
    DUPLICATE_APPLICATION_RISK = "DUPLICATE_APPLICATION_RISK"
    URL_UNREACHABLE = "URL_UNREACHABLE"
    FORM_NOT_FOUND = "FORM_NOT_FOUND"
    RESUME_FILE_MISSING = "RESUME_FILE_MISSING"
    BOT_CHALLENGE = "BOT_CHALLENGE"
    PREPARATION_NOT_READY = "PREPARATION_NOT_READY"


@dataclass
class FormFieldDetection:
    """Detected input element from application page."""
    field_id: str
    name: str
    label: str
    input_type: str  # text, email, tel, file, select, textarea, radio, checkbox
    placeholder: str = ""
    aria_label: str = ""
    autocomplete: str = ""
    options: List[str] = field(default_factory=list)
    is_required: bool = False
    is_sensitive: bool = False
    selector: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_id": self.field_id,
            "name": self.name,
            "label": self.label,
            "input_type": self.input_type,
            "placeholder": self.placeholder,
            "aria_label": self.aria_label,
            "autocomplete": self.autocomplete,
            "options": self.options,
            "is_required": self.is_required,
            "is_sensitive": self.is_sensitive,
            "selector": self.selector,
        }


@dataclass
class FieldMappingResult:
    """Mapped field binding a form input to verified candidate evidence."""
    form_field: FormFieldDetection
    matched_key: str
    proposed_value: Any
    confidence: FieldConfidence
    requires_human_confirmation: bool
    confirmed_by_user: bool = False
    status: str = "PENDING"  # PENDING, FILLED, SKIPPED, AWAITING_CONFIRMATION
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "form_field": self.form_field.to_dict(),
            "matched_key": self.matched_key,
            "proposed_value": self.proposed_value,
            "confidence": self.confidence.value,
            "requires_human_confirmation": self.requires_human_confirmation,
            "confirmed_by_user": self.confirmed_by_user,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass
class SubmissionEvidence:
    """Observable evidence proving application submission occurred."""
    confirmed: bool = False
    evidence_type: str = "NONE"  # URL_TRANSITION, CONFIRMATION_TEXT, APPLICATION_NUMBER, NONE
    details: Dict[str, Any] = field(default_factory=dict)
    confirmation_number: Optional[str] = None
    page_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confirmed": self.confirmed,
            "evidence_type": self.evidence_type,
            "details": self.details,
            "confirmation_number": self.confirmation_number,
            "page_url": self.page_url,
        }


@dataclass
class ExecutorCapabilities:
    """Declared capabilities of an application source executor."""
    can_open_url: bool = True
    can_detect_form: bool = False
    can_fill_text: bool = False
    can_upload_resume: bool = False
    can_select_option: bool = False
    can_submit: bool = False
    requires_human_review: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_open_url": self.can_open_url,
            "can_detect_form": self.can_detect_form,
            "can_fill_text": self.can_fill_text,
            "can_upload_resume": self.can_upload_resume,
            "can_select_option": self.can_select_option,
            "can_submit": self.can_submit,
            "requires_human_review": self.requires_human_review,
        }
