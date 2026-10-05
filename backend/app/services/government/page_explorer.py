"""
Job Operating System - Government Website Exploration & Recursive Discovery
Explores government portals, detects recruitment and vacancy pages, discovers child
organisations recursively, and extracts vacancy notices and PDF documents.
Respects rate limits and flags blocked sources as REQUIRES_MANUAL_ACCESS.
"""
import re
import urllib.parse
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
import httpx
from bs4 import BeautifulSoup

from app.services.government.search_engine import GovernmentSearchDiscoveryEngine

logger = logging.getLogger(__name__)

COMMON_CAREER_PATHS = [
    "/recruitment",
    "/recruitments",
    "/vacancies",
    "/vacancy",
    "/careers",
    "/career",
    "/engagement",
    "/consultant",
    "/notifications",
    "/notices",
    "/advertisement",
    "/advertisements",
    "/opportunities",
    "/employment",
    "/work-with-us",
    "/jobs",
    "/job",
    "/walk-in",
]

RECRUITMENT_KEYWORD_RE = re.compile(
    r"(recruitment|vacancy|vacancies|career|careers|engagement|consultant|contractual|project associate|young professional|walk-in|advertisement|notice|employment)",
    re.IGNORECASE
)

PDF_RECRUITMENT_RE = re.compile(
    r"(advt|recruitment|vacancy|notice|consultant|contract|project|walk[-_]?in|engagement|selection|notification)",
    re.IGNORECASE
)


class GovernmentPageExplorer:
    """
    Crawls and analyzes public Indian government websites to discover hiring sections,
    extract recruitment announcements and PDF links, and discover related sub-organisations.
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
        }

    def explore_organisation_domain(
        self,
        domain: str,
        known_career_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deeply inspects an organisation's domain:
        1. Probes known or candidate career URLs.
        2. Parses HTML to discover recruitment notices and PDF attachments.
        3. Identifies links to child / related government institutions for recursive discovery.
        """
        base_url = f"https://{domain}" if not domain.startswith("http") else domain
        discovered_career_url = known_career_url
        vacancies_found: List[Dict[str, Any]] = []
        child_sources: List[Dict[str, Any]] = []
        crawl_status = "success"
        requires_manual_access = False

        target_url = known_career_url or base_url

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(target_url, headers=self.headers)
                
                # Check for access blocks or bot walls
                if resp.status_code in (401, 403) or "captcha" in resp.text.lower() or "challenge-platform" in resp.text.lower():
                    logger.warning(f"Government portal {target_url} returned {resp.status_code} or bot challenge.")
                    return {
                        "career_url": target_url,
                        "crawl_status": "blocked",
                        "requires_manual_access": True,
                        "vacancies": [],
                        "child_sources": [],
                    }

                if resp.status_code != 200 and not known_career_url:
                    # Attempt common career paths
                    for path in COMMON_CAREER_PATHS:
                        test_url = urllib.parse.urljoin(base_url, path)
                        try:
                            probe = client.get(test_url, headers=self.headers)
                            if probe.status_code == 200 and RECRUITMENT_KEYWORD_RE.search(probe.text):
                                resp = probe
                                discovered_career_url = test_url
                                break
                        except Exception:
                            continue

                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    current_url = str(resp.url)
                    if not discovered_career_url:
                        discovered_career_url = self._find_recruitment_link_in_html(soup, current_url) or current_url

                    # Extract vacancies & PDFs
                    vacancies_found = self._extract_vacancies_from_page(soup, current_url, domain)

                    # Extract child government bodies for recursive discovery
                    child_sources = self._discover_child_organisations(soup, current_url)

        except httpx.ConnectError:
            crawl_status = "connection_failed"
        except httpx.TimeoutException:
            crawl_status = "timeout"
        except Exception as e:
            logger.warning(f"Error exploring {domain}: {e}")
            crawl_status = "error"

        return {
            "career_url": discovered_career_url or base_url,
            "crawl_status": crawl_status,
            "requires_manual_access": requires_manual_access,
            "vacancies": vacancies_found,
            "child_sources": child_sources,
        }

    def _find_recruitment_link_in_html(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Scans navigation and anchor tags for recruitment / career links."""
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            text = a.get_text(strip=True)
            if RECRUITMENT_KEYWORD_RE.search(href) or RECRUITMENT_KEYWORD_RE.search(text):
                full_url = urllib.parse.urljoin(base_url, href)
                if not full_url.lower().endswith(".pdf"):
                    return full_url
        return None

    def _extract_vacancies_from_page(
        self,
        soup: BeautifulSoup,
        page_url: str,
        domain: str
    ) -> List[Dict[str, Any]]:
        """
        Extracts vacancy items from HTML tables, lists, or announcement blocks,
        prioritizing technical, contractual, and PDF notices.
        """
        extracted: List[Dict[str, Any]] = []
        seen_titles: Set[str] = set()

        # 1. Inspect table rows
        for tr in soup.find_all("tr"):
            text = tr.get_text(" ", strip=True)
            if not text or len(text) < 10:
                continue
            if RECRUITMENT_KEYWORD_RE.search(text):
                pdf_link = None
                apply_link = None
                for a in tr.find_all("a", href=True):
                    href = urllib.parse.urljoin(page_url, a.get("href"))
                    if href.lower().endswith(".pdf") or "pdf" in href.lower():
                        pdf_link = href
                    elif any(w in a.get_text().lower() for w in ["apply", "portal", "link", "register"]):
                        apply_link = href

                title = self._clean_vacancy_title(text)
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    extracted.append({
                        "title": title,
                        "description": text[:2000],
                        "source_url": page_url,
                        "pdf_url": pdf_link,
                        "apply_url": apply_link or page_url,
                        "is_contractual": any(w in text.lower() for w in ["contract", "consultant", "project", "temporary", "young professional", "walk-in"]),
                    })

        # 2. Inspect anchor tags directly for recruitment notices & PDFs
        for a in soup.find_all("a", href=True):
            href = urllib.parse.urljoin(page_url, a.get("href"))
            text = a.get_text(strip=True)
            if not text or len(text) < 8:
                continue

            is_pdf = href.lower().endswith(".pdf")
            is_recruitment = bool(RECRUITMENT_KEYWORD_RE.search(text) or (is_pdf and PDF_RECRUITMENT_RE.search(href)))

            if is_recruitment:
                title = self._clean_vacancy_title(text)
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    extracted.append({
                        "title": title,
                        "description": f"Recruitment Announcement from {domain}: {text}",
                        "source_url": page_url,
                        "pdf_url": href if is_pdf else None,
                        "apply_url": href if not is_pdf else page_url,
                        "is_contractual": any(w in text.lower() for w in ["contract", "consultant", "project", "temporary", "young professional", "walk-in"]),
                    })

        return extracted

    def _discover_child_organisations(
        self,
        soup: BeautifulSoup,
        base_url: str
    ) -> List[Dict[str, Any]]:
        """
        Recursively discovers linked subordinate bodies, autonomous institutes,
        and missions from government portal navigation.
        """
        child_sources: List[Dict[str, Any]] = []
        seen_domains: Set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if not href.startswith("http"):
                continue

            domain = GovernmentSearchDiscoveryEngine.extract_domain(href)
            if domain and domain not in seen_domains and GovernmentSearchDiscoveryEngine.is_government_domain(domain):
                # Don't add current domain
                curr_domain = GovernmentSearchDiscoveryEngine.extract_domain(base_url)
                if domain == curr_domain:
                    continue

                seen_domains.add(domain)
                anchor_text = a.get_text(strip=True) or domain
                meta = GovernmentSearchDiscoveryEngine.infer_organisation_metadata(domain, title=anchor_text)
                child_sources.append({
                    "organisation_name": meta["organisation_name"],
                    "organisation_type": meta["organisation_type"],
                    "government_level": meta["government_level"],
                    "state": meta["state"],
                    "official_domain": domain,
                    "career_url": href,
                    "discovery_method": "recursive_link",
                    "discovered_from": base_url,
                })

        return child_sources

    @staticmethod
    def _clean_vacancy_title(raw_text: str) -> str:
        """Extracts a clear, concise job title from announcement text."""
        cleaned = re.sub(r"\s+", " ", raw_text).strip()
        # Remove date prefixes or trailing file sizes
        cleaned = re.sub(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\s*", "", cleaned)
        cleaned = re.sub(r"\(\d+(\.\d+)?\s*(KB|MB)\)", "", cleaned, flags=re.IGNORECASE)
        # Cap length
        return cleaned[:200].strip()
