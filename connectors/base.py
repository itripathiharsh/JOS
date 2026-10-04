from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from connectors.models import NormalizedJob, SourceHealth, SourceCapabilities
from connectors.exceptions import (
    SourceException,
    SourceConnectionError,
    SourceRateLimitError,
    SourceResponseError,
    SourceValidationError,
)


class JobSource(ABC):
    """
    Common pluggable interface for all job discovery sources (Remotive, Greenhouse, Lever, etc.).
    All connectors must implement search, fetch_job, health_check, and normalize_job.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name for this source connector (e.g. 'remotive')."""
        pass

    @property
    def source_type(self) -> str:
        """Source type category: 'api', 'board', 'ats', 'aggregator'."""
        return "api"

    @property
    def capabilities(self) -> SourceCapabilities:
        """Declared features and limitations of this source connector."""
        return SourceCapabilities()

    @property
    def source_metadata(self) -> Dict[str, Any]:
        """Human-readable metadata and operational notes about this source."""
        return {
            "name": self.name,
            "type": self.source_type,
            "cost": "₹0",
            "auth_required": False,
        }

    @abstractmethod
    def search(
        self,
        query: str,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        limit: int = 20,
        **kwargs
    ) -> List[NormalizedJob]:
        """
        Execute a search query against the source and return normalized jobs.
        Must raise typed SourceException subclasses (SourceConnectionError, SourceRateLimitError,
        SourceResponseError) on actual network/protocol failures so ingestion can record status cleanly.
        """
        pass

    @abstractmethod
    def fetch_job(self, external_id: str) -> Optional[NormalizedJob]:
        """
        Retrieve a single job posting by its external identifier.
        Returns None if not found or unavailable.
        """
        pass

    @abstractmethod
    def health_check(self) -> SourceHealth:
        """
        Verify connector connectivity, responsiveness, and rate limit status.
        """
        pass

    @abstractmethod
    def normalize_job(self, raw: Dict[str, Any]) -> Optional[NormalizedJob]:
        """
        Transform a single raw record from this source into a NormalizedJob.
        Returns None if the raw payload cannot be parsed or lacks mandatory identifiers.
        """
        pass
