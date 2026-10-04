import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Optional, Set


# Common marketing/analytics tracking query parameters to safely remove
TRACKING_PARAMS: Set[str] = {
    # UTM parameters
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_reader",
    "utm_place",
    "utm_cid",
    # Referral and source trackers
    "ref",
    "referrer",
    "ref_id",
    "source",
    "src",
    "from",
    "trk",
    "tracking_id",
    "session_id",
    # Ad network click identifiers
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "msclkid",
    "twclid",
    # Email and marketing automation
    "mc_cid",
    "mc_eid",
    "_hsenc",
    "_hsmi",
    "mkt_tok",
    "oly_enc_id",
    "oly_anon_id",
    # Generic affiliate / campaign trackers
    "aff_id",
    "affiliate",
    "partner",
    "campaign_id",
    "channel",
}

# Parameters that typically identify a specific job posting and must NEVER be stripped
JOB_IDENTIFIER_PARAMS: Set[str] = {
    "gh_jid",           # Greenhouse job ID
    "jobid",
    "job_id",
    "jid",
    "id",
    "req_id",
    "reqid",
    "requisition_id",
    "requisitionid",
    "pos_id",
    "position_id",
    "posting_id",
    "p",
    "v",
}


def normalize_url(url: Optional[str]) -> Optional[str]:
    """
    Safely normalizes an application/job URL for duplicate comparison:
    1. Strips leading/trailing whitespace.
    2. Converts scheme and domain to lowercase.
    3. Removes standard default ports (:80, :443).
    4. Removes fragments (#apply, #details, etc.).
    5. Strips trailing slashes from the path (unless root path).
    6. Strips known marketing/analytics tracking parameters.
    7. Preserves functional and job-identifying query parameters.
    8. Sorts query parameters deterministically.
    """
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()
    if not cleaned:
        return None

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return cleaned

    # Scheme
    scheme = parsed.scheme.lower() if parsed.scheme else "https"

    # Netloc (host + port)
    netloc = parsed.netloc.lower()
    # Strip standard ports
    if netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Path normalization
    path = parsed.path
    if path:
        # Collapse multiple slashes
        path = re.sub(r"/+", "/", path)
        # Strip trailing slash unless root '/'
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")
    else:
        path = ""

    # Query normalization
    query_str = ""
    if parsed.query:
        query_dict = parse_qs(parsed.query, keep_blank_values=False)
        cleaned_query = {}
        for key, values in query_dict.items():
            k_lower = key.lower()
            if k_lower in TRACKING_PARAMS:
                continue
            cleaned_query[key] = values

        if cleaned_query:
            # Deterministic sorting of query parameters
            sorted_items = sorted(cleaned_query.items(), key=lambda x: x[0])
            query_str = urlencode(sorted_items, doseq=True)

    # Reconstruct normalized URL without fragment
    normalized = urlunparse((scheme, netloc, path, "", query_str, ""))
    return normalized


def extract_domain(url: Optional[str]) -> Optional[str]:
    """Extract registered domain or hostname from URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return None


def extract_url_job_identifier(url: Optional[str]) -> Optional[str]:
    """
    Extracts an embedded job identifier from URL path or query params if evident.
    e.g., /jobs/12345, /requisitions/REQ-88, ?gh_jid=9988
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
        # 1. Check query parameters
        if parsed.query:
            params = parse_qs(parsed.query)
            for k in JOB_IDENTIFIER_PARAMS:
                if k in params and params[k]:
                    return str(params[k][0]).strip()

        # 2. Check path patterns
        path = parsed.path
        # Pattern: /jobs/(number or alphanumeric req id)
        m = re.search(r"/(?:jobs|requisitions|positions|openings)/(?:view/)?([A-Za-z0-9_-]{4,})", path, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return None
