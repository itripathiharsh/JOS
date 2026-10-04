import re
import html
import time
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
import httpx

from connectors.base import JobSource
from connectors.models import NormalizedJob, SourceHealth, SourceCapabilities
from connectors.exceptions import (
    SourceConnectionError,
    SourceRateLimitError,
    SourceResponseError,
)

logger = logging.getLogger(__name__)


class RemotiveSource(JobSource):
    """
    Production connector for Remotive Public Jobs API.
    - Endpoint: https://remotive.com/api/remote-jobs
    - Cost: ₹0 (Official public developer API)
    - Authentication: None required
    - Automated Access: Permitted public endpoint for job aggregators and personal tooling
    """

    BASE_URL = "https://remotive.com/api/remote-jobs"
    DEFAULT_TIMEOUT_SEC = 15.0
    USER_AGENT = "JobApplicationAgent/1.0 (Personal Job Operating System; Harsh Tripathi)"

    @property
    def name(self) -> str:
        return "remotive"

    @property
    def source_type(self) -> str:
        return "api"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_search=True,
            supports_location_filter=True,
            supports_remote_filter=True,
            supports_pagination=True,
            max_limit=100,
        )

    @property
    def source_metadata(self) -> Dict[str, Any]:
        return {
            "name": "Remotive",
            "type": "api",
            "url": self.BASE_URL,
            "cost": "₹0",
            "auth_required": False,
            "rate_limit": "Public developer endpoint, max limit 100 per call",
            "description": "Public remote developer and tech job board API",
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
        Search Remotive remote job listings.
        Remotive supports ?search=<query>&limit=<limit>.
        Raises typed exceptions on network/protocol failures.
        """
        params: Dict[str, Any] = {}
        if query and query.strip():
            params["search"] = query.strip()
        if limit and limit > 0:
            params["limit"] = min(limit, 100)

        headers = {"User-Agent": self.USER_AGENT}

        try:
            with httpx.Client(timeout=self.DEFAULT_TIMEOUT_SEC, headers=headers) as client:
                response = client.get(self.BASE_URL, params=params)

                if response.status_code == 429:
                    logger.warning("Remotive API rate limited (HTTP 429).")
                    raise SourceRateLimitError(
                        "Remotive API rate limit reached (HTTP 429).",
                        source=self.name,
                        details={"status_code": 429}
                    )

                if response.status_code != 200:
                    err_msg = f"Remotive API error: HTTP {response.status_code} - {response.text[:200]}"
                    logger.error(err_msg)
                    raise SourceResponseError(
                        err_msg,
                        source=self.name,
                        details={"status_code": response.status_code}
                    )

                try:
                    payload = response.json()
                except Exception as json_err:
                    err_msg = f"Failed to parse Remotive JSON response: {json_err}"
                    logger.error(err_msg)
                    raise SourceResponseError(err_msg, source=self.name)

        except httpx.TimeoutException as exc:
            err_msg = f"Remotive API timed out after {self.DEFAULT_TIMEOUT_SEC}s: {exc}"
            logger.error(err_msg)
            raise SourceConnectionError(err_msg, source=self.name)
        except httpx.RequestError as exc:
            err_msg = f"Remotive network request failed: {exc}"
            logger.error(err_msg)
            raise SourceConnectionError(err_msg, source=self.name)

        if not isinstance(payload, dict):
            raise SourceResponseError(f"Remotive response is not a JSON object: {type(payload)}", source=self.name)

        raw_jobs = payload.get("jobs", [])
        if not isinstance(raw_jobs, list):
            raise SourceResponseError(f"Remotive payload 'jobs' is not a list: {type(raw_jobs)}", source=self.name)

        normalized_jobs: List[NormalizedJob] = []
        for raw in raw_jobs:
            try:
                job = self.normalize_job(raw)
                if job:
                    # Client-side location filtering if requested
                    if location and location.strip() and job.location:
                        loc_clean = location.strip().lower()
                        if loc_clean not in job.location.lower():
                            continue
                    normalized_jobs.append(job)
                    if len(normalized_jobs) >= limit:
                        break
            except Exception as e:
                logger.warning(f"Failed to normalize Remotive job {raw.get('id')}: {e}")

        logger.info(f"Remotive search '{query}' returned {len(normalized_jobs)} normalized jobs (raw: {len(raw_jobs)}).")
        return normalized_jobs

    def fetch_job(self, external_id: str) -> Optional[NormalizedJob]:
        """
        Retrieve a specific job from Remotive by external ID.
        """
        if not external_id or not str(external_id).strip():
            return None

        # Search Remotive by query or fetch recent jobs to locate matching ID
        try:
            jobs = self.search(query="", limit=100)
            for j in jobs:
                if str(j.external_job_id) == str(external_id).strip():
                    return j
        except Exception as exc:
            logger.error(f"Failed to fetch job {external_id} from Remotive: {exc}")
        return None

    def health_check(self) -> SourceHealth:
        """
        Perform a ping / lightweight check against Remotive API.
        """
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=10.0, headers={"User-Agent": self.USER_AGENT}) as client:
                res = client.get(self.BASE_URL, params={"limit": 1})
                latency = round((time.perf_counter() - start) * 1000, 2)
                if res.status_code == 200:
                    return SourceHealth(
                        healthy=True,
                        message="Remotive API is reachable and responding with 200 OK.",
                        latency_ms=latency,
                        details={"status_code": 200, "jobs_sample": len(res.json().get("jobs", []))}
                    )
                else:
                    return SourceHealth(
                        healthy=False,
                        message=f"Remotive API responded with HTTP {res.status_code}",
                        latency_ms=latency,
                        details={"status_code": res.status_code}
                    )
        except Exception as exc:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return SourceHealth(
                healthy=False,
                message=f"Remotive API unreachable: {exc}",
                latency_ms=latency
            )

    def normalize_job(self, raw: Dict[str, Any]) -> Optional[NormalizedJob]:
        """
        Adapt a raw Remotive dictionary into a NormalizedJob model.
        Validates required fields: title, company, source, external_job_id.
        """
        raw_id = raw.get("id")
        title = raw.get("title")
        company = raw.get("company_name")

        # Validation of required fields
        if not raw_id or not title or not company:
            logger.warning(f"Rejecting malformed Remotive job missing required fields: id={raw_id}, title={title}, company={company}")
            return None

        external_id = str(raw_id).strip()
        title_clean = str(title).strip()
        company_clean = str(company).strip()

        # HTML cleaning & section splitting
        raw_desc = raw.get("description") or ""
        clean_desc = self._clean_html(raw_desc)
        requirements, responsibilities = self._extract_sections(clean_desc)

        # Salary parsing
        salary_raw = raw.get("salary")
        salary_min, salary_max, currency = self._parse_salary(salary_raw)

        # Date parsing
        posted_at = self._parse_date(raw.get("publication_date"))

        # Location & work mode
        candidate_loc = raw.get("candidate_required_location")
        location = candidate_loc.strip() if candidate_loc else "Worldwide"
        work_mode = "remote"  # Remotive is by design a remote job board

        # Employment type & tags / skills
        job_type = raw.get("job_type")
        employment_type = str(job_type).strip().lower() if job_type else None

        raw_tags = raw.get("tags") or []
        skills = [str(t).strip() for t in raw_tags if t and str(t).strip()] if isinstance(raw_tags, list) else []

        # Application URL
        url = raw.get("url")

        return NormalizedJob(
            source=self.name,
            external_job_id=external_id,
            url=url,
            title=title_clean,
            company=company_clean,
            location=location,
            work_mode=work_mode,
            employment_type=employment_type,
            skills=skills,
            description=clean_desc,
            requirements=requirements,
            responsibilities=responsibilities,
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            posted_at=posted_at,
            expires_at=None,
            raw_payload={
                "category": raw.get("category"),
                "tags": skills,
                "job_type": employment_type,
                "company_logo": raw.get("company_logo"),
                "raw_salary": salary_raw,
            }
        )

    def _clean_html(self, raw_html: str) -> str:
        """Strip HTML tags and convert entities to clean readable plain text with preserved linebreaks."""
        if not raw_html:
            return ""
        # Convert <br>, </p>, </li>, </div> to newlines
        text = re.sub(r'<(?:br|/p|/li|/div|/h\d)[^>]*>', '\n', raw_html, flags=re.IGNORECASE)
        # Strip all other HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Unescape HTML entities (&nbsp;, &amp;, etc.)
        text = html.unescape(text)
        # Collapse multiple empty lines
        lines = [line.strip() for line in text.split('\n')]
        cleaned_lines = []
        consecutive_empty = 0
        for line in lines:
            if not line:
                consecutive_empty += 1
                if consecutive_empty <= 1:
                    cleaned_lines.append("")
            else:
                consecutive_empty = 0
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    def _extract_sections(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Heuristically extract Requirements and Responsibilities sections if present in text.
        """
        requirements: Optional[str] = None
        responsibilities: Optional[str] = None

        req_patterns = [
            r'(?:requirements|what you need|qualifications|what we are looking for|who you are)[:\s]+(.*?)(?=(?:responsibilities|what you\'ll do|what you will do|benefits|about us|how to apply|\Z))',
        ]
        resp_patterns = [
            r'(?:responsibilities|what you\'ll do|what you will do|the role|your mission)[:\s]+(.*?)(?=(?:requirements|what you need|qualifications|benefits|about us|how to apply|\Z))',
        ]

        for pat in req_patterns:
            m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
            if m and len(m.group(1).strip()) > 20:
                requirements = m.group(1).strip()
                break

        for pat in resp_patterns:
            m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
            if m and len(m.group(1).strip()) > 20:
                responsibilities = m.group(1).strip()
                break

        return requirements, responsibilities

    def _parse_salary(self, salary_str: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Safely parse salary strings without inventing values.
        Supports:
          "$90k - $120k", "$80,000 - $100,000", "€60k - €80k", "100000 USD", etc.
        """
        if not salary_str or not str(salary_str).strip():
            return None, None, None

        s = str(salary_str).strip()
        curr = "USD"
        if "€" in s or "EUR" in s.upper():
            curr = "EUR"
        elif "£" in s or "GBP" in s.upper():
            curr = "GBP"
        elif "₹" in s or "INR" in s.upper():
            curr = "INR"
        elif "CAD" in s.upper():
            curr = "CAD"
        elif "AUD" in s.upper():
            curr = "AUD"

        # Regex matching numbers with optional k/K suffix
        matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*(k|K)?', s)
        nums: List[float] = []
        for num_str, is_k in matches:
            try:
                val = float(num_str.replace(",", ""))
                if is_k:
                    val *= 1000.0
                if val > 100:  # Ignore hourly rates or tiny indices
                    nums.append(val)
            except ValueError:
                pass

        if not nums:
            return None, None, None

        if len(nums) == 1:
            return nums[0], nums[0], curr
        return min(nums), max(nums), curr

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 string to timezone-aware UTC datetime."""
        if not date_str or not str(date_str).strip():
            return None
        try:
            dt = datetime.fromisoformat(str(date_str).strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
