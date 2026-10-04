import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


def get_utc_now():
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class DiscoveryRun(Base):
    """
    Audit log entity for a batch job discovery execution.
    Tracks query strategy execution metrics, aggregate job discovery counts, and failure stats.
    """
    __tablename__ = "discovery_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    candidate_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(100), default="remotive", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="in_progress", index=True)  # in_progress, completed, failed

    queries_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    queries_executed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_queries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_queries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    jobs_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    duration_ms: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON config, limits
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
