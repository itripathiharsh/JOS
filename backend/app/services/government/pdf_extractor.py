"""
Job Operating System - PDF-First Government Recruitment Parser
Treats PDFs as first-class recruitment notices.
Extracts structured vacancy attributes from public notices using pypdf,
calculates SHA-256 for change/corrigendum detection, and gracefully handles non-text scans.
"""
import io
import re
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import httpx
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def parse_date_candidate(text: str) -> Optional[datetime]:
    """Attempts to parse common Indian recruitment date formats into timezone-aware datetime."""
    if not text:
        return None
    # Strip prefixes
    cleaned = re.sub(r"^(?:last\s+date|closing\s+date|deadline|apply\s+before|for\s+submission\s+of\s+application)?\s*[:\-\s]*", "", text, flags=re.IGNORECASE).strip()
    
    # Formats: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, DD Mon YYYY, DD Month YYYY
    date_patterns = [
        (r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", "%d/%m/%Y"),
        (r"(\d{1,2})[./-](\d{1,2})[./-](\d{2})", "%d/%m/%y"),
        (r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})", "%d %b %Y"),
    ]
    for pat, fmt in date_patterns:
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            try:
                matched_str = m.group(0).replace(".", "/").replace("-", "/")
                if "%b" in fmt:
                    # e.g. 12 Oct 2026
                    parts = m.groups()
                    dt = datetime.strptime(f"{parts[0]} {parts[1][:3].title()} {parts[2]}", "%d %b %Y")
                else:
                    dt = datetime.strptime(matched_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return None

# Maximum PDF size to process safely in memory (15 MB)
MAX_PDF_SIZE_BYTES = 15 * 1024 * 1024

POSITION_PATTERNS = [
    r"(Senior\s+Consultant|Junior\s+Consultant|Consultant)",
    r"(Young\s+Professional(\s+[I|II])?)",
    r"(Project\s+Associate(\s+[I|II])?|Project\s+Assistant|Project\s+Scientist|Project\s+Manager)",
    r"(Technical\s+Consultant|IT\s+Consultant|Technical\s+Assistant)",
    r"(Software\s+Developer|Software\s+Engineer|Programmer|Backend\s+Developer|Data\s+Analyst|Database\s+Administrator)",
    r"(Research\s+Associate|Research\s+Assistant|Fellow|Fellowship)",
    r"(Programme\s+Manager|Programme\s+Associate)",
]

SALARY_PATTERNS = [
    r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\s*-\s*[\d,]+)?)\s*(?:/-\s*)?(?:per\s+month|p\.?m\.?|consolidated|\+?\s*HRA)?",
    r"(?:Level\s*-\s*\d+|Pay\s+Matrix\s+Level\s*\d+|Pay\s+Scale\s*:\s*[^\n]+)",
    r"(?:Remuneration|Emoluments|Stipend)\s*:\s*(?:Rs\.?|INR|₹)?\s*([\d,]+[^\n]+)",
]

DEADLINE_PATTERNS = [
    r"(?:last\s+date|closing\s+date|deadline|apply\s+before)\s*(?:for\s+submission\s+of\s+application)?\s*:\s*([^\n\.;]{5,35})",
    r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
]

DURATION_PATTERNS = [
    r"(?:period\s+of|duration\s+of|initially\s+for)\s*([^\n\.;]{4,50}(?:year|month|renewable|co-terminus))",
]

AGE_PATTERNS = [
    r"(?:upper\s+age\s+limit|maximum\s+age|age\s+limit)\s*(?:shall\s+be)?\s*:\s*([^\n\.;]{3,30})",
    r"(?:not\s+exceeding|below)\s*(\d{2}\s*years)",
]

VACANCY_COUNT_PATTERNS = [
    r"(?:no\.\s*of\s*(?:posts?|positions?|vacanc(?:y|ies)))\s*:\s*(\d+)",
    r"(\d+)\s*(?:posts?|positions?|vacanc(?:y|ies))",
]


class GovernmentPdfExtractor:
    """
    Downloads, parses, and extracts structured job fields from official
    government recruitment notifications.
    """

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

    def process_pdf_url(self, pdf_url: str) -> Dict[str, Any]:
        """
        Fetches and extracts structured attributes from a recruitment PDF URL.
        Returns extracted text, SHA-256 hash, and parsed metadata fields.
        """
        result: Dict[str, Any] = {
            "pdf_url": pdf_url,
            "pdf_sha256": None,
            "pdf_extracted_text": "",
            "extraction_status": "not_applicable",
            "position": None,
            "salary": None,
            "application_deadline": None,
            "contract_duration": None,
            "age_limit": None,
            "number_of_positions": None,
            "application_email": None,
            "selection_process": None,
            "change_type": "new_vacancy",
            "corrigendum_details": None,
        }

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(pdf_url, headers=self.headers)
                if resp.status_code != 200:
                    result["extraction_status"] = "failed"
                    return result

                raw_bytes = resp.content
                if len(raw_bytes) > MAX_PDF_SIZE_BYTES:
                    logger.warning(f"PDF {pdf_url} exceeded size limit ({len(raw_bytes)} bytes).")
                    result["extraction_status"] = "failed"
                    return result

                # 1. Compute SHA-256 for exact versioning & change detection
                sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
                result["pdf_sha256"] = sha256_hash

                # 2. Extract text using pypdf
                extracted_pages = []
                try:
                    reader = PdfReader(io.BytesIO(raw_bytes))
                    for idx, page in enumerate(reader.pages):
                        text = page.extract_text() or ""
                        if text.strip():
                            extracted_pages.append(text.strip())
                except Exception as pdf_err:
                    logger.warning(f"pypdf extraction error on {pdf_url}: {pdf_err}")
                    result["extraction_status"] = "failed"
                    return result

                full_text = "\n\n".join(extracted_pages).replace("\x00", "")
                result["pdf_extracted_text"] = full_text[:20000]  # Cap storage to 20k chars

                if not full_text.strip():
                    result["extraction_status"] = "partial"  # likely scanned image
                    return result

                result["extraction_status"] = "success"

                # 3. Heuristic attribute parsing
                parsed = self.parse_text_heuristics(full_text)
                result.update(parsed)

        except Exception as e:
            logger.warning(f"Failed to fetch and process PDF {pdf_url}: {e}")
            result["extraction_status"] = "failed"

        return result

    @classmethod
    def parse_text_heuristics(cls, text: str) -> Dict[str, Any]:
        """
        Parses raw text of an advertisement to identify key contractual and eligibility fields.
        """
        parsed: Dict[str, Any] = {}

        # 1. Position / Designation
        for pat in POSITION_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                parsed["position"] = match.group(0).strip()
                break

        # 2. Salary / Remuneration
        for pat in SALARY_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                parsed["salary"] = match.group(0).strip()
                break

        # 3. Contract Duration
        for pat in DURATION_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                parsed["contract_duration"] = match.group(1).strip()
                break

        # 4. Age Limit
        for pat in AGE_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                parsed["age_limit"] = match.group(1).strip()
                break

        # 5. Number of positions
        for pat in VACANCY_COUNT_PATTERNS:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                try:
                    parsed["number_of_positions"] = int(match.group(1))
                    break
                except ValueError:
                    pass

        # 6. Contact Email for Application
        email_match = re.search(r"[\w\.-]+@(?:[\w-]+\.)+(?:gov\.in|nic\.in|ac\.in|res\.in|edu\.in|org\.in|com)", text)
        if email_match:
            parsed["application_email"] = email_match.group(0).strip()

        # 7. Selection Process
        if "walk-in" in text.lower():
            parsed["selection_process"] = "Walk-in Interview"
        elif "written test" in text.lower():
            parsed["selection_process"] = "Written Examination & Interview"
        elif "interview" in text.lower():
            parsed["selection_process"] = "Personal Interview"

        # 8. Application Deadline Extraction
        for pat in DEADLINE_PATTERNS:
            d_match = re.search(pat, text, re.IGNORECASE)
            if d_match:
                d_str = d_match.group(1).strip()
                parsed["deadline_str"] = d_str
                # Attempt to parse date
                dt = parse_date_candidate(d_str)
                if dt:
                    parsed["application_deadline"] = dt
                break

        # 9. Corrigendum / Addendum / Date Extension Detection
        if any(w in text.lower() for w in ["corrigendum", "amendment", "erratum"]):
            parsed["change_type"] = "corrigendum"
            parsed["corrigendum_details"] = "Corrigendum / Amendment issued on this notice."
        elif any(w in text.lower() for w in ["extension of last date", "date extended", "extended up to"]):
            parsed["change_type"] = "deadline_extended"
            parsed["corrigendum_details"] = "Submission deadline has been officially extended."
        elif any(w in text.lower() for w in ["cancelled", "withdrawn", "cancellation notice"]):
            parsed["change_type"] = "vacancy_cancelled"
            parsed["corrigendum_details"] = "Recruitment notification cancelled by hiring authority."

        return parsed


# Aliases & Top-Level Helper Functions
GovernmentPDFExtractor = GovernmentPdfExtractor


def extract_government_fields(text: str) -> Dict[str, Any]:
    """Extracts structured fields from advertisement text with standard keys."""
    fields = GovernmentPdfExtractor.parse_text_heuristics(text)
    remuneration = fields.get("salary")
    emp_type = "Contract" if any(w in text.lower() for w in ["contract", "consultant", "temporary", "project"]) else "Permanent"
    app_mode = "email" if fields.get("application_email") else ("walk_in" if "walk-in" in text.lower() else "online")

    return {
        "position": fields.get("position"),
        "salary": remuneration,
        "remuneration": remuneration,
        "contract_duration": fields.get("contract_duration"),
        "age_limit": fields.get("age_limit"),
        "application_deadline": fields.get("application_deadline"),
        "deadline": fields.get("application_deadline"),
        "application_email": fields.get("application_email"),
        "selection_process": fields.get("selection_process"),
        "employment_type": emp_type,
        "application_mode": app_mode,
        "corrigendum_details": fields.get("corrigendum_details"),
    }


def detect_corrigendum(text: str) -> Tuple[bool, Optional[str]]:
    """Detects whether text indicates a corrigendum, addendum, or deadline extension."""
    text_lower = text.lower()
    corrigendum_keywords = [
        "corrigendum", "addendum", "amendment", "erratum",
        "extension of last date", "date extended", "extended up to", "rescheduled"
    ]
    for kw in corrigendum_keywords:
        if kw in text_lower:
            start_idx = max(0, text_lower.find(kw) - 20)
            snippet = text[start_idx : start_idx + 150].strip()
            return True, snippet
    return False, None
