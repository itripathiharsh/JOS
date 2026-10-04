from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.services.execution_layer.models import (
    ExecutorCapabilities,
    ExecutionStatus,
    SubmissionEvidence,
)
from app.models.execution import ApplicationExecution


class BaseApplicationExecutor(ABC):
    """
    Abstract base class for all application execution adapters.
    Declares capabilities, execution steps, and submission boundaries.
    """

    source_name: str = "generic_web"
    capabilities: ExecutorCapabilities = ExecutorCapabilities()

    @abstractmethod
    def start_execution(
        self,
        execution: ApplicationExecution,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Initiates the execution attempt."""
        pass

    @abstractmethod
    def resume_execution(
        self,
        execution: ApplicationExecution,
        user_inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resumes execution after user intervention or review."""
        pass

    @abstractmethod
    def approve_and_submit(
        self,
        execution: ApplicationExecution,
        context: Dict[str, Any],
    ) -> SubmissionEvidence:
        """Executes final submission after explicit human approval."""
        pass
