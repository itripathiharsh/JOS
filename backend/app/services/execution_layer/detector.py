import re
from typing import List, Dict, Any, Tuple, Optional
from bs4 import BeautifulSoup
from app.services.execution_layer.models import FormFieldDetection, BlockerType


class HtmlFormDetector:
    """
    Parses HTML documents to detect form inputs, bot challenges (CAPTCHA/Cloudflare),
    login requirements, and submission elements.
    """

    CAPTCHA_INDICATORS = [
        re.compile(r"g-recaptcha|recaptcha", re.IGNORECASE),
        re.compile(r"h-captcha|hcaptcha", re.IGNORECASE),
        re.compile(r"cf-turnstile|turnstile", re.IGNORECASE),
        re.compile(r"challenge-platform|cloudflare|waf", re.IGNORECASE),
        re.compile(r"perimeterx|datadome|arkoselabs|geetest", re.IGNORECASE),
        re.compile(r"verify you are human|security verification|checking your browser", re.IGNORECASE),
    ]

    LOGIN_INDICATORS = [
        re.compile(r"sign in to apply|login to apply|log in to apply|please sign in", re.IGNORECASE),
        re.compile(r"create an account to continue|authentication required", re.IGNORECASE),
    ]

    @classmethod
    def detect_challenges(cls, html: str) -> Optional[BlockerType]:
        """
        Scans HTML content for anti-bot barriers or mandatory login gates.
        Returns BlockerType if detected, otherwise None.
        """
        if not html:
            return None

        # Check for CAPTCHA / bot challenge
        for pattern in cls.CAPTCHA_INDICATORS:
            if pattern.search(html):
                return BlockerType.CAPTCHA_DETECTED

        # Check for Login wall
        for pattern in cls.LOGIN_INDICATORS:
            if pattern.search(html):
                return BlockerType.LOGIN_REQUIRED

        return None

    @classmethod
    def extract_form_fields(cls, html: str) -> List[FormFieldDetection]:
        """
        Extracts all interactable application form fields from HTML string.
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        detected_fields: List[FormFieldDetection] = []

        # Find forms or general container
        inputs = soup.find_all(["input", "textarea", "select"])

        for idx, el in enumerate(inputs):
            tag_name = el.name.lower()
            input_type = el.get("type", "text").lower() if tag_name == "input" else tag_name

            # Skip hidden, submit, button, reset
            if input_type in {"hidden", "submit", "button", "reset", "image"}:
                continue

            field_id = el.get("id", f"field_{idx}")
            name = el.get("name", field_id)
            placeholder = el.get("placeholder", "")
            aria_label = el.get("aria-label", "")
            autocomplete = el.get("autocomplete", "")
            is_required = el.has_attr("required") or "required" in el.get("class", [])

            # Extract associated label
            label = ""
            if field_id:
                label_el = soup.find("label", attrs={"for": field_id})
                if label_el:
                    label = label_el.get_text(strip=True)

            if not label:
                # Check parent or surrounding label
                parent_label = el.find_parent("label")
                if parent_label:
                    label = parent_label.get_text(strip=True)

            if not label:
                label = placeholder or aria_label or name

            # Options for select
            options = []
            if tag_name == "select":
                for opt in el.find_all("option"):
                    opt_val = opt.get("value") or opt.get_text(strip=True)
                    if opt_val:
                        options.append(opt_val)

            selector = f"{tag_name}#{field_id}" if el.get("id") else f"{tag_name}[name='{name}']"

            detected_fields.append(
                FormFieldDetection(
                    field_id=field_id,
                    name=name,
                    label=label,
                    input_type=input_type,
                    placeholder=placeholder,
                    aria_label=aria_label,
                    autocomplete=autocomplete,
                    options=options,
                    is_required=is_required,
                    selector=selector,
                )
            )

        return detected_fields

    @classmethod
    def detect_submission_evidence(cls, html: str, url: str) -> Tuple[bool, str, Optional[str]]:
        """
        Inspects page content and URL to verify whether an application was truly submitted.
        Returns: (is_confirmed, evidence_type, confirmation_number)
        """
        if not html and not url:
            return False, "NONE", None

        # Check URL patterns
        url_lower = url.lower()
        if any(term in url_lower for term in ["/thank-you", "/thanks", "/success", "/confirmation", "/submitted", "/applied"]):
            return True, "URL_TRANSITION", None

        # Check page text for confirmation keywords
        confirm_patterns = [
            re.compile(r"thank you for applying|application (has been )?submitted|application received|we have received your application", re.IGNORECASE),
            re.compile(r"application reference|confirmation number|tracking id|application id:\s*([A-Za-z0-9-_]+)", re.IGNORECASE),
            re.compile(r"your application was sent successfully", re.IGNORECASE),
        ]

        for pat in confirm_patterns:
            match = pat.search(html)
            if match:
                ref_num = match.group(1) if match.lastindex and match.lastindex >= 1 else None
                return True, "CONFIRMATION_TEXT", ref_num

        return False, "NONE", None
