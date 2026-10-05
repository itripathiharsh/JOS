"""
Job Operating System - Open-Ended Government Search Engine Discovery
Generates targeted queries and parses public search results across .gov.in, .nic.in,
.res.in, .ac.in, and Indian state/UT portals.
Operates 100% locally with zero-cost HTTP clients.
"""
import re
import urllib.parse
import logging
import time
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup

from app.services.government.seed_registry import INDIAN_STATES, INDIAN_UTS

logger = logging.getLogger(__name__)

# Official Indian Government Domain Suffixes & Top-Level Domains
GOVERNMENT_TLD_PATTERNS = [
    r"\.gov\.in$",
    r"\.nic\.in$",
    r"\.res\.in$",
    r"\.ac\.in$",
    r"\.edu\.in$",
    r"\.org\.in$",
]

# Hiring & Contractual Patterns
HIRING_TERMS = [
    "recruitment", "vacancy", "careers", "engagement", "consultant",
    "contractual", '"contract basis"', '"temporary position"',
    '"project associate"', '"young professional"', '"technical consultant"',
    '"project staff"', '"walk-in interview"', '"advertisement for engagement"',
    '"inviting applications"', '"short term contract"', '"fixed term"', '"empanelment"'
]

# Technical Keywords
TECH_TERMS = [
    "AI", "Artificial Intelligence", "Machine Learning", "Data Science",
    "Data Analyst", "Python", "Software Developer", "Software Engineer",
    "Backend", "Developer", "Technology", "IT", "Information Technology",
    "Digital", "Analytics", "Cloud", "Cybersecurity", "Computer Science",
    "Consultant", "Young Professional", "Project", "Research"
]


class GovernmentSearchDiscoveryEngine:
    """
    Autonomous search engine discovery agent that discovers previously unknown
    Indian government websites, departments, institutes, and vacancy pages.
    """

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    # Rotation state index
    _rotation_index: int = 0

    @classmethod
    def generate_search_queries(
        cls,
        scope: str = "ALL",
        state_filter: Optional[str] = None,
        state: Optional[str] = None,
        max_queries: int = 30,
        **kwargs
    ) -> List[str]:
        """
        Generates rotated, high-yield search queries targeting central, state, UT,
        PSU, and research hiring notices with continuous query rotation (Section 18).
        """
        target_state = state_filter or state
        queries: List[str] = []

        # Core Government Hiring Patterns
        core_patterns = [
            'site:gov.in recruitment',
            'site:gov.in vacancy',
            'site:gov.in consultant',
            'site:gov.in "contract basis"',
            'site:gov.in "young professional"',
            'site:gov.in "project associate"',
            'site:gov.in "project staff"',
            'site:gov.in "technical consultant"',
            'site:gov.in "walk-in interview"',
            'site:gov.in "engagement"',
            'site:gov.in "empanelment"',
            'site:gov.in "inviting applications"',
            'site:nic.in recruitment',
            'site:nic.in "contract basis"',
            'site:res.in "project associate"',
            'site:res.in "walk-in interview"',
            'site:ac.in recruitment "project staff"',
        ]

        # Technical Keywords for Combination
        tech_keywords = [
            "AI", "ML", "Python", "software", "data", "technology", "IT",
            "analytics", "developer", "engineer", "technical", "consultant",
            "project", "research"
        ]

        # 1. Non-technical organisation discovery queries (discover bodies before determining tech vacancies)
        non_tech_queries = [
            'site:gov.in "about us" ministry OR department',
            'site:gov.in "autonomous bodies" OR "attached offices"',
            'site:gov.in "subordinate offices" OR "public sector undertakings"',
            'site:nic.in "portal of india" directory',
            'site:res.in "research laboratory" OR "national institute"',
        ]

        # 2. Combined Core + Tech Queries with Rotation
        combined_queries = []
        offset = cls._rotation_index % len(tech_keywords)
        cls._rotation_index += 1

        for i, core in enumerate(core_patterns):
            tech_kw = tech_keywords[(offset + i) % len(tech_keywords)]
            combined_queries.append(f'{core} {tech_kw}')

        # 3. State / UT Specific Queries with Rotation
        all_regions = INDIAN_STATES + INDIAN_UTS
        if target_state:
            target_regions = [target_state]
        else:
            reg_offset = (cls._rotation_index * 5) % len(all_regions)
            target_regions = all_regions[reg_offset:reg_offset + 8]
            if len(target_regions) < 8:
                target_regions.extend(all_regions[:8 - len(target_regions)])

        region_queries = []
        for reg in target_regions:
            region_queries.append(f'site:gov.in "{reg}" recruitment OR vacancy')
            region_queries.append(f'site:nic.in "{reg}" "contract basis" OR "consultant"')

        # Ordering based on scope
        scope_upper = scope.upper()
        if scope_upper == "STATE" or target_state:
            queries.extend(region_queries)
            queries.extend(combined_queries)
            queries.extend(core_patterns)
        elif scope_upper == "CONTRACTUAL":
            contract_patterns = [p for p in core_patterns if "contract" in p or "consultant" in p or "young professional" in p or "project" in p]
            queries.extend(contract_patterns)
            queries.extend(combined_queries)
            queries.extend(region_queries)
        else:
            # Interleave to ensure breadth
            queries.extend(non_tech_queries[:3])
            queries.extend(combined_queries)
            queries.extend(core_patterns[:5])
            queries.extend(region_queries)

        # Deduplicate while preserving order & cap to max_queries
        unique_queries = list(dict.fromkeys(queries))
        return unique_queries[:max_queries]

    def execute_search_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Executes a query against public search endpoints and returns structured result items.
        Extracts real target URLs by unwrapping DuckDuckGo redirection parameters.
        """
        encoded_query = urllib.parse.quote_plus(query)
        search_urls = [
            f"https://html.duckduckgo.com/html/?q={encoded_query}",
            f"https://lite.duckduckgo.com/lite/?q={encoded_query}",
        ]

        discovered_items: List[Dict[str, Any]] = []

        for search_url in search_urls:
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    resp = client.get(search_url, headers=self.headers)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    results = soup.find_all("div", class_="result") or soup.find_all("tr")

                    for res in results:
                        link_tag = res.find("a", class_="result__url") or res.find("a")
                        snippet_tag = res.find("a", class_="result__snippet") or res.find("td", class_="result-snippet")
                        title_tag = res.find("h2") or res.find("a", class_="result__a")

                        if not link_tag or not link_tag.get("href"):
                            continue

                        raw_href = link_tag.get("href")
                        unwrapped_url = self._unwrap_search_url(raw_href)
                        if not unwrapped_url:
                            continue

                        domain = self.extract_domain(unwrapped_url)
                        if not self.is_government_domain(domain):
                            continue

                        title = title_tag.get_text(strip=True) if title_tag else ""
                        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                        discovered_items.append({
                            "url": unwrapped_url,
                            "domain": domain,
                            "title": title,
                            "snippet": snippet,
                            "query": query,
                        })

                    if discovered_items:
                        break  # Successfully fetched from this engine

            except Exception as e:
                logger.warning(f"Search endpoint {search_url} failed for query '{query}': {e}")
                time.sleep(1.0)

        return discovered_items

    @staticmethod
    def _unwrap_search_url(raw_url: str) -> Optional[str]:
        """Unwraps duckduckgo.com/l/?uddg=<actual_target_url>."""
        if not raw_url:
            return None
        if "uddg=" in raw_url:
            try:
                parsed = urllib.parse.urlparse(raw_url)
                qs = urllib.parse.parse_qs(parsed.query)
                target = qs.get("uddg", [None])[0]
                if target:
                    return target
            except Exception:
                pass
        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            return raw_url
        return None

    @staticmethod
    def extract_domain(url: str) -> str:
        """Extracts lowercase hostname without port or www prefix."""
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.netloc.split(":")[0].lower()
            if host.startswith("www."):
                host = host[4:]
            return host
        except Exception:
            return ""

    @classmethod
    def is_government_domain(cls, domain: str) -> bool:
        """
        Validates if domain belongs to official Indian government, PSU,
        research, or autonomous university network.
        """
        if not domain:
            return False
        domain_clean = domain.lower().strip()
        for pat in GOVERNMENT_TLD_PATTERNS:
            if re.search(pat, domain_clean):
                return True
        # Explicit known PSU/Gov domains without standard TLDs
        known_gov_domains = [
            "cdac.in", "stpi.in", "ernet.in", "bis.gov.in", "bel-india.in",
            "bhel.com", "ongcindia.com", "iocl.com", "ntpc.co.in", "hal-india.co.in",
            "aiims.edu", "iisc.ac.in", "iitd.ac.in", "iitk.ac.in", "iitb.ac.in"
        ]
        return any(domain_clean == kd or domain_clean.endswith("." + kd) for kd in known_gov_domains)

    @classmethod
    def infer_organisation_metadata(
        cls,
        domain: str,
        title: str = "",
        snippet: str = ""
    ) -> Dict[str, Any]:
        """
        Infers organisation type, government level, state, and name from domain and snippets.
        """
        text = f"{title} {snippet} {domain}".lower()
        level = "central"
        state = None
        org_type = "other"

        # State detection
        for s in INDIAN_STATES:
            if s.lower() in text or f".{s.lower().replace(' ', '')}." in domain or f"{s.lower().replace(' ', '')}.gov.in" in domain:
                level = "state"
                state = s
                break
        if not state:
            for ut in INDIAN_UTS:
                if ut.lower() in text or ut.lower().replace(" ", "") in domain:
                    level = "ut"
                    state = ut
                    break

        # Organisation Type detection
        if any(w in text for w in ["ministry", "mantralaya"]):
            org_type = "ministry"
        elif any(w in text for w in ["department", "directorate", "commissionerate"]):
            org_type = "department"
        elif any(w in text for w in ["iit", "nit", "iiit", "iiser", "university", "vidyalaya", "college"]):
            org_type = "university"
        elif any(w in text for w in ["csir", "icmr", "drdo", "isro", "research", "laboratory", "tifr", "lab"]):
            org_type = "research_institute"
        elif any(w in text for w in ["limited", "corporation", "psu", "cdac", "bel", "bhel", "ongc", "ntpc"]):
            org_type = "psu"
        elif any(w in text for w in ["aiims", "hospital", "medical college", "health mission", "nhm"]):
            org_type = "hospital"
        elif any(w in text for w in ["authority", "commission", "regulator", "tribunal", "trai", "sebi", "rbi", "uidai"]):
            org_type = "regulator"
        elif any(w in text for w in ["mission", "project", "digital india", "smart city", "jal jeevan"]):
            org_type = "mission"
        elif any(w in text for w in ["district", "collectorate", "dm office", "zp"]):
            org_type = "district_administration"

        # Clean Organisation Name
        org_name = title.split("-")[0].split("|")[0].split("::")[0].strip()
        if not org_name or len(org_name) < 4:
            parts = domain.split(".")
            org_name = parts[0].upper() + " Government Portal"

        return {
            "organisation_name": org_name[:255],
            "organisation_type": org_type,
            "government_level": level,
            "state": state,
        }


# Aliases
GovernmentSearchEngine = GovernmentSearchDiscoveryEngine


def is_valid_indian_gov_url(url: str) -> bool:
    """Convenience function checking if a URL belongs to official Indian government network."""
    domain = GovernmentSearchEngine.extract_domain(url)
    return GovernmentSearchEngine.is_government_domain(domain)


def generate_search_queries(
    scope: str = "ALL",
    state: Optional[str] = None,
    state_filter: Optional[str] = None,
    max_queries: int = 25
) -> List[str]:
    """Convenience function generating targeted government search queries."""
    sf = state_filter or state
    return GovernmentSearchDiscoveryEngine.generate_search_queries(
        scope=scope,
        state_filter=sf,
        max_queries=max_queries
    )
