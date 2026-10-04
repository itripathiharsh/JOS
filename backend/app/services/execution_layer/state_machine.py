from typing import Set, Dict, Tuple
from app.services.execution_layer.models import ExecutionStatus


class ExecutionStateMachine:
    """
    Enforces strict, auditable state transitions for application execution.
    Prevents bypassing human approval gates and protects against unverified submissions.
    """

    ALLOWED_TRANSITIONS: Dict[ExecutionStatus, Set[ExecutionStatus]] = {
        ExecutionStatus.NOT_STARTED: {
            ExecutionStatus.READY,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.BLOCKED,
        },
        ExecutionStatus.READY: {
            ExecutionStatus.AWAITING_APPROVAL,
            ExecutionStatus.OPENING,
            ExecutionStatus.AWAITING_USER,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.BLOCKED,
        },
        ExecutionStatus.AWAITING_APPROVAL: {
            ExecutionStatus.OPENING,
            ExecutionStatus.AWAITING_USER,
            ExecutionStatus.CANCELLED,
        },
        ExecutionStatus.OPENING: {
            ExecutionStatus.NAVIGATING,
            ExecutionStatus.AWAITING_USER,
            ExecutionStatus.BLOCKED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        },
        ExecutionStatus.NAVIGATING: {
            ExecutionStatus.FILLING,
            ExecutionStatus.AWAITING_USER,
            ExecutionStatus.READY_TO_SUBMIT,
            ExecutionStatus.BLOCKED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        },
        ExecutionStatus.FILLING: {
            ExecutionStatus.AWAITING_USER,
            ExecutionStatus.READY_TO_SUBMIT,
            ExecutionStatus.BLOCKED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        },
        ExecutionStatus.AWAITING_USER: {
            ExecutionStatus.OPENING,
            ExecutionStatus.NAVIGATING,
            ExecutionStatus.FILLING,
            ExecutionStatus.READY_TO_SUBMIT,
            ExecutionStatus.SUBMITTED,  # Allowed when user marks submitted manually
            ExecutionStatus.CANCELLED,
            ExecutionStatus.FAILED,
        },
        ExecutionStatus.READY_TO_SUBMIT: {
            ExecutionStatus.SUBMITTING,
            ExecutionStatus.SUBMITTED,  # When verified observable proof is confirmed directly
            ExecutionStatus.AWAITING_USER,
            ExecutionStatus.CANCELLED,
        },
        ExecutionStatus.SUBMITTING: {
            ExecutionStatus.SUBMITTED,
            ExecutionStatus.AWAITING_USER,  # If confirmation could not be verified automatically
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        },
        ExecutionStatus.FAILED: {
            ExecutionStatus.READY,
            ExecutionStatus.OPENING,
            ExecutionStatus.AWAITING_USER,
            ExecutionStatus.CANCELLED,
        },
        ExecutionStatus.BLOCKED: {
            ExecutionStatus.READY,
            ExecutionStatus.AWAITING_USER,
            ExecutionStatus.CANCELLED,
        },
        ExecutionStatus.SUBMITTED: set(),  # Terminal state
        ExecutionStatus.CANCELLED: set(),  # Terminal state
    }

    @classmethod
    def can_transition(cls, current: ExecutionStatus, target: ExecutionStatus) -> bool:
        """Check whether a transition is permitted by the state machine."""
        if current == target:
            return True
        allowed = cls.ALLOWED_TRANSITIONS.get(current, set())
        return target in allowed

    @classmethod
    def validate_transition(cls, current: ExecutionStatus, target: ExecutionStatus, reason: str = "") -> ExecutionStatus:
        """Validate and return target status or raise ValueError."""
        if not cls.can_transition(current, target):
            raise ValueError(
                f"Invalid execution state transition: Cannot transition from '{current.value}' to '{target.value}'. "
                f"Allowed target states: {[s.value for s in cls.ALLOWED_TRANSITIONS.get(current, set())]}. "
                f"{f'Reason: {reason}' if reason else ''}"
            )
        return target

    @classmethod
    def is_terminal(cls, status: ExecutionStatus) -> bool:
        """Terminal states cannot transition further."""
        return status in {ExecutionStatus.SUBMITTED, ExecutionStatus.CANCELLED}

    @classmethod
    def is_resumable(cls, status: ExecutionStatus) -> bool:
        """States from which execution can be resumed by the user."""
        return status in {
            ExecutionStatus.AWAITING_USER,
            ExecutionStatus.BLOCKED,
            ExecutionStatus.FAILED,
            ExecutionStatus.READY_TO_SUBMIT,
            ExecutionStatus.AWAITING_APPROVAL,
        }
