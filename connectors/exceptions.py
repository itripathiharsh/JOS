"""
Standardized exceptions for job source connectors.
Ensures network, rate limit, HTTP, and data errors are explicitly typed and handled.
"""

class SourceException(Exception):
    """Base exception for all job source connector errors."""
    def __init__(self, message: str, source: str = "unknown", details: dict = None):
        super().__init__(message)
        self.message = message
        self.source = source
        self.details = details or {}


class SourceConnectionError(SourceException):
    """Raised when connector encounters network timeouts, DNS failures, or connection errors."""
    pass


class SourceRateLimitError(SourceException):
    """Raised when connector exceeds source rate limits (e.g. HTTP 429)."""
    pass


class SourceResponseError(SourceException):
    """Raised when connector receives an unexpected, error, or unparseable HTTP response."""
    pass


class SourceValidationError(SourceException):
    """Raised when a source payload is fundamentally malformed or fails validation."""
    pass
