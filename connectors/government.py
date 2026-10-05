"""
Job Operating System - Government Job Source Connector
Pluggable JobSource implementation for Indian Public Sector, Ministries, PSUs,
Research Institutes, Academic bodies, and Contractual Missions.
Converts government recruitment notifications into NormalizedJob objects.
"""
import re
import hashlib
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from connectors.base import JobSource
from connectors.models import NormalizedJob, SourceHealth, SourceCapabilities

logger = logging.getLogger(__name__)


class GovernmentJobSource(JobSource):
    """
    Pluggable JobSource connector for Indian Government, PSU, and Contractual vacancies.
    Converts discovered portal notices and PDF extractions into standardized NormalizedJob records.
    """

    @property
    def name(self) -> str:
        return "government"

    @property
    def source_type(self) -> str:
        return "portal"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_search=True,
            supports_location_filter=True,
            supports_remote_filter=False,
            supports_pagination=True,
            max_limit=100,
        )

    @property
    def source_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Indian Government & Public Sector Jobs",
            "type": "portal",
            "cost": "₹0",
            "auth_required": False,
            "description": "Comprehensive autonomous discovery across Central, 28 States, 8 UTs, PSUs, and Research Bodies",
        }

    def search(
        self,
        query: str,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        limit: int = 20,
        **kwargs
    ) -> List[NormalizedJob]:
        """
        Executes search via the GovernmentDiscoveryEngine.
        Returns a list of NormalizedJob instances.
        """
        # Imported lazily to prevent circular dependencies
        from app.services.government.engine import GovernmentDiscoveryEngine
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            return GovernmentDiscoveryEngine.search_vacancies(
                db=db,
                query=query,
                location=location,
                limit=limit,
            )
        finally:
            db.close()

    def fetch_job(self, external_id: str) -> Optional[NormalizedJob]:
        """Retrieves a single vacancy by its government external ID."""
        from app.db.session import SessionLocal
        from app.models.job import Job

        db = SessionLocal()
        try:
            job = db.query(Job).filter(
                Job.source == self.name,
                Job.external_job_id == external_id
            ).first()
            if not job:
                return None
            return self.normalize_job({
                "id": job.external_job_id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "work_mode": job.work_mode,
                "description": job.description,
                "requirements": job.requirements,
                "responsibilities": job.responsibilities,
                "salary_min": float(job.salary_min) if job.salary_min else None,
                "salary_max": float(job.salary_max) if job.salary_max else None,
                "currency": job.currency,
                "application_url": job.application_url,
                "posted_at": job.posted_at,
                "expires_at": job.expires_at,
            })
        finally:
            db.close()

    def health_check(self) -> SourceHealth:
        """Verifies government source registry health and database connectivity."""
        from app.db.session import SessionLocal
        from app.models.government import GovernmentSource

        db = SessionLocal()
        try:
            count = db.query(GovernmentSource).count()
            return SourceHealth(
                healthy=True,
                message=f"Government Source Registry operational with {count} registered sources.",
                latency_ms=10.0,
                details={"sources_registered": count}
            )
        except Exception as e:
            return SourceHealth(
                healthy=False,
                message=f"Government health check failed: {str(e)}",
            )
        finally:
            db.close()

    def normalize_job(self, raw: Dict[str, Any]) -> Optional[NormalizedJob]:
        """
        Transforms raw government announcement or PDF extraction into NormalizedJob.
        """
        if not raw or not raw.get("title") or not raw.get("company"):
            return None

        title = str(raw["title"]).strip()
        company = str(raw["company"]).strip()
        external_id = str(raw.get("id") or raw.get("external_job_id") or "")
        if not external_id:
            raw_key = f"{company}_{title}_{raw.get('application_url', '')}"
            external_id = "gov_" + hashlib.md5(raw_key.encode("utf-8")).hexdigest()[:12]

        location = raw.get("location") or "India"
        work_mode = raw.get("work_mode", "onsite")
        url = raw.get("application_url") or raw.get("pdf_url") or raw.get("url")

        skills = raw.get("skills", [])
        if not skills and raw.get("description"):
            # Extract common technical skills from description
            desc_lower = raw["description"].lower()
            candidate_skills = ["python", "ai", "machine learning", "data science", "sql", "cloud", "api", "software development"]
            skills = [s.title() for s in candidate_skills if s in desc_lower]

        return NormalizedJob(
            source=self.name,
            external_job_id=external_id,
            url=url,
            title=title,
            company=company,
            location=location,
            work_mode=work_mode,
            employment_type=raw.get("employment_type", "contract"),
            skills=skills,
            description=raw.get("description"),
            requirements=raw.get("requirements"),
            responsibilities=raw.get("responsibilities"),
            salary_min=raw.get("salary_min"),
            salary_max=raw.get("salary_max"),
            currency=raw.get("currency", "INR"),
            posted_at=raw.get("posted_at"),
            expires_at=raw.get("expires_at"),
            raw_payload=raw,
        )
