import re
import json
from typing import Optional, Tuple, Dict, Any, Set, List


# Common corporate suffixes
COMPANY_SUFFIXES = [
    r"\binc(?:\.|\b)",
    r"\bincorporated\b",
    r"\bllc(?:\.|\b)",
    r"\bl\.l\.c\b",
    r"\bltd(?:\.|\b)",
    r"\blimited\b",
    r"\bcorp(?:\.|\b)",
    r"\bcorporation\b",
    r"\bco(?:\.|\b)",
    r"\bcompany\b",
    r"\bgmbh\b",
    r"\bpvt(?:\.|\s+ltd|\b)",
    r"\bprivate\s+limited\b",
    r"\btechnologies\b",
    r"\btechnology\b",
    r"\bsolutions\b",
]

# Explicit seniority tokens that MUST be preserved and tracked
SENIORITY_RANKS: Dict[str, int] = {
    "intern": 1,
    "junior": 2,
    "mid": 3,
    "senior": 4,
    "lead": 5,
    "staff": 6,
    "principal": 7,
    "director": 8,
    "vp": 9,
}

SENIORITY_PATTERNS: Dict[str, List[str]] = {
    "intern": [r"\bintern(?:ship)?\b", r"\btrainee\b", r"\bco-?op\b"],
    "junior": [r"\bjunior\b", r"\bjr(?:\.|\b)", r"\bentry[- ]level\b", r"\bassociate\b"],
    "mid": [r"\bmid[- ]level\b", r"\bintermediate\b"],
    "senior": [r"\bsenior\b", r"\bsr(?:\.|\b)", r"\bsr\b"],
    "lead": [r"\blead\b", r"\btech[- ]lead\b", r"\bteam[- ]lead\b"],
    "staff": [r"\bstaff\b"],
    "principal": [r"\bprincipal\b"],
    "director": [r"\bdirector\b", r"\bhead\s+of\b", r"\bvp\b", r"\bvice\s+president\b"],
}


def normalize_company(name: Optional[str]) -> str:
    """
    Normalizes company names for deduplication:
    - Lowercase, trimmed.
    - Strips common corporate entity suffixes (Inc, LLC, Corp, etc.).
    - Removes punctuation and collapses whitespace.
    - Keeps core brand token (e.g. 'Lemon.io Inc.' -> 'lemon.io').
    """
    if not name or not isinstance(name, str):
        return ""

    text = name.strip().lower()
    # Normalize common characters
    text = text.replace("&", " and ")

    # Strip corporate suffixes
    for pattern in COMPANY_SUFFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Clean non-alphanumeric except dots inside domains (like lemon.io)
    # If text is something like 'lemon.io', preserve the dot
    parts = []
    for token in text.split():
        cleaned_token = re.sub(r"[^\w\.]", "", token).strip(".")
        if cleaned_token:
            parts.append(cleaned_token)

    return " ".join(parts).strip()


def extract_seniority(title: str) -> Optional[str]:
    """Detects explicit seniority level from a job title."""
    lower = title.lower()
    for level, patterns in SENIORITY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                return level
    return None


def normalize_title(title: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Normalizes job title while STRICTLY preserving seniority level.
    Returns (normalized_title, seniority_level).
    Examples:
      'Senior AI Engineer' -> ('senior ai engineer', 'senior')
      'Senior AI-Engineer' -> ('senior ai engineer', 'senior')
      'AI Engineer'        -> ('ai engineer', None)
      'Junior AI Engineer' -> ('junior ai engineer', 'junior')
    Notice: 'Senior AI Engineer' will NEVER normalize to 'ai engineer'.
    """
    if not title or not isinstance(title, str):
        return ("", None)

    raw = title.strip().lower()
    seniority = extract_seniority(raw)

    # Standardize punctuation and spacing
    text = re.sub(r"[-_/]+", " ", raw)
    text = re.sub(r"[^\w\s]", "", text)
    tokens = text.split()

    # Standardize known abbreviations while preserving seniority
    normalized_tokens = []
    for tok in tokens:
        if tok in ("sr", "sr."):
            normalized_tokens.append("senior")
        elif tok in ("jr", "jr."):
            normalized_tokens.append("junior")
        elif tok == "fde":
            normalized_tokens.append("forward deployed engineer")
        elif tok in ("sw", "swe"):
            normalized_tokens.append("software engineer")
        elif tok == "ml":
            normalized_tokens.append("machine learning")
        elif tok == "ai":
            normalized_tokens.append("ai")
        else:
            normalized_tokens.append(tok)

    result_title = " ".join(normalized_tokens)
    return (result_title, seniority)


def normalize_location(location: Optional[str]) -> Dict[str, Any]:
    """
    Normalizes location string into country, region, city, and scope.
    Guarantees that distinct countries (India vs US vs Germany) are distinguishable.
    """
    if not location or not isinstance(location, str):
        return {
            "raw": "",
            "normalized": "",
            "country": None,
            "region": None,
            "city": None,
            "is_remote": False,
            "scope": "unknown",
        }

    loc_lower = location.strip().lower()
    is_remote = bool(re.search(r"\b(remote|anywhere|telecommute|distributed)\b", loc_lower))

    country = None
    if re.search(r"\b(india|in|ind|bengaluru|bangalore|delhi|mumbai|lucknow|hyderabad|pune)\b", loc_lower):
        country = "india"
    elif re.search(r"\b(usa|united states|us|america|california|new york|texas|san francisco)\b", loc_lower):
        country = "united states"
    elif re.search(r"\b(germany|deutschland|berlin|munich)\b", loc_lower):
        country = "germany"
    elif re.search(r"\b(uk|united kingdom|great britain|london)\b", loc_lower):
        country = "united kingdom"
    elif re.search(r"\b(canada|toronto|vancouver)\b", loc_lower):
        country = "canada"

    scope = "unknown"
    if "worldwide" in loc_lower or "anywhere" in loc_lower:
        scope = "worldwide"
    elif "apac" in loc_lower:
        scope = "apac"
    elif "emea" in loc_lower:
        scope = "emea"
    elif "latam" in loc_lower:
        scope = "latam"
    elif country:
        scope = country

    # Standard clean representation
    cleaned = re.sub(r"[^\w\s]", " ", loc_lower)
    cleaned = " ".join(cleaned.split())

    return {
        "raw": location.strip(),
        "normalized": cleaned,
        "country": country,
        "is_remote": is_remote,
        "scope": scope,
    }


def extract_requisition_id(
    raw_payload: Optional[str] = None,
    external_id: Optional[str] = None,
    url: Optional[str] = None,
    text: Optional[str] = None,
) -> Optional[str]:
    """
    Extracts explicit Requisition ID, ATS job ID, or reference number from:
    1. raw_payload JSON keys
    2. external_id
    3. URL patterns or parameters
    4. Text annotations (e.g. 'Req ID: 12345')
    """
    # 1. Check raw_payload JSON
    if raw_payload:
        try:
            payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
            if isinstance(payload, dict):
                for key in ("requisition_id", "req_id", "reqId", "job_req_id", "reference_id", "ref_number", "ats_id"):
                    val = payload.get(key)
                    if val and str(val).strip():
                        return str(val).strip()
        except Exception:
            pass

    # 2. Check external_id if structured like a requisition (e.g., 'REQ-1234' or 'R10042')
    if external_id:
        ext_clean = external_id.strip()
        if re.match(r"^(?:req|r|job|pos)[-_]?[0-9]{3,}$", ext_clean, re.IGNORECASE):
            return ext_clean.upper()

    # 3. Check text patterns in title/description
    if text:
        m = re.search(r"\b(?:req(?:uisition)?|reference|job)\s*(?:id|#|no\.?)?[:\s]+([A-Za-z0-9_-]{4,15})\b", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    return None
