from abc import ABC, abstractmethod
from typing import Dict, Any


class ApplicationPreparation(ABC):
    """Abstract interface for preparing application packages (resumes, answers, cover letters)."""
    @abstractmethod
    def prepare(self, job_id: str, candidate_id: str) -> Dict[str, Any]:
        pass


class ApplicationExecution(ABC):
    """Abstract interface for submitting or staging applications."""
    @abstractmethod
    def submit(self, application_package: Dict[str, Any]) -> Dict[str, Any]:
        pass


class ApplicationTracker(ABC):
    """Abstract interface for tracking state and events across application lifecycle."""
    @abstractmethod
    def record_event(self, application_id: str, event_type: str, details: Dict[str, Any]) -> None:
        pass
