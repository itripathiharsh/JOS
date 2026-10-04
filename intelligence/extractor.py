import re
from typing import Optional, List, Tuple, Dict, Set
from intelligence.models import JobRequirements, CanonicalSkill, NormalizedRole
from intelligence.normalization import normalize_skill, normalize_role, CANONICAL_SKILL_MAP

# Ordered list of skill search patterns to check against text (longest first to avoid partial prefix collisions)
SORTED_SKILL_KEYS = sorted(CANONICAL_SKILL_MAP.keys(), key=lambda k: len(k), reverse=True)

# Context-sensitive skills that need strict regex boundaries
STRICT_SKILL_PATTERNS: Dict[str, str] = {
    "c": r"\b(c\s*(?:language|programming)|\bc\s*/\s*c\+\+|\bc\s*,\s*c\+\+)\b",
    "go": r"\b(golang|go\s+language|\bgo\b\s+(?:developer|engineer|backend|programming))\b",
    "r": r"\b(r\s+(?:language|programming|scripts?))\b",
    "sql": r"\bsql\b",
    "js": r"\bjs\b",
    "ts": r"\bts\b",
    "rest": r"\b(rest\s*(?:api|apis|services?|endpoints?|architecture)|restful)\b",
    "cv": r"\b(computer\s+vision|cv\s+(?:engineer|developer|algorithms?|models?)|opencv)\b",
}


def build_skill_regex(skill_key: str) -> re.Pattern:
    """Build a regex pattern for a canonical skill alias."""
    if skill_key in STRICT_SKILL_PATTERNS:
        return re.compile(STRICT_SKILL_PATTERNS[skill_key], re.IGNORECASE)
    # Standard word-boundary match
    escaped = re.escape(skill_key)
    return re.compile(rf"\b{escaped}\b", re.IGNORECASE)


COMPILED_SKILL_PATTERNS: List[Tuple[str, re.Pattern]] = [
    (key, build_skill_regex(key)) for key in SORTED_SKILL_KEYS
]


# Experience extraction regex patterns
EXP_RANGE_PATTERN = re.compile(r"(\d+)\+?\s*(?:to|-)\s*(\d+)\+?\s*(?:years?|yrs?)", re.IGNORECASE)
EXP_MIN_PATTERN = re.compile(r"(?:at least|minimum|min|with|\+)\s*(\d+)\+?\s*(?:years?|yrs?)", re.IGNORECASE)
EXP_PLUS_PATTERN = re.compile(r"(\d+)\+\s*(?:years?|yrs?)", re.IGNORECASE)
EXP_GENERAL_PATTERN = re.compile(
    r"(\d+)\s*(?:years?|yrs?)(?:\s*of)?\s*(?:commercial|professional|industry|relevant|software|hands-on|practical)?\s*experience",
    re.IGNORECASE
)

# Section detection patterns
REQUIRED_SECTION_PATTERNS = [
    r"requirements",
    r"what we(?:'re|\s+are)\s+looking\s+for",
    r"what you(?:'ll|\s+will)\s+bring",
    r"must\s+have",
    r"required\s+qualifications",
    r"basic\s+qualifications",
    r"who\s+you\s+are",
    r"qualifications",
    r"what you need",
]

PREFERRED_SECTION_PATTERNS = [
    r"nice\s+to\s+have",
    r"preferred\s+qualifications",
    r"bonus(?:\s+points)?",
    r"good\s+to\s+have",
    r"plus(?:es)?",
    r"preferred",
    r"extra credit",
]

EXCLUDED_SECTION_PATTERNS = [
    r"not your tech stack",
    r"not your stack",
    r"other roles",
    r"we(?:'re|\s+are)\s+also\s+hiring",
    r"we work with developers from",
    r"about the company",
    r"equal opportunity",
]

# In-line indicator patterns
INLINE_PREFERRED_PATTERNS = re.compile(r"\b(?:is a plus|nice to have|preferred|bonus|optional)\b", re.IGNORECASE)
INLINE_REQUIRED_PATTERNS = re.compile(r"\b(?:is a must|required|mandatory|essential)\b", re.IGNORECASE)

# Education detection patterns
DEGREE_PATTERN = re.compile(r"\b(bachelor(?:'s)?|master(?:'s)?|phd|doctorate|b\.?tech|b\.?s\.?|m\.?tech|m\.?s\.?|degree)\b", re.IGNORECASE)
STEM_PATTERN = re.compile(r"\b(computer science|data science|information technology|software engineering|stem|mathematics|engineering)\b", re.IGNORECASE)


def extract_job_requirements(
    title: str,
    description: Optional[str] = None,
    requirements_text: Optional[str] = None,
    responsibilities_text: Optional[str] = None,
    location: Optional[str] = None,
    work_mode: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    currency: Optional[str] = "USD",
    candidate_target_roles: Optional[List[str]] = None,
) -> JobRequirements:
    """
    Deterministically extracts normalized job requirements from job fields.
    Does not guess or hallucinate unmentioned fields.
    """
    clean_title = title.strip() if title else ""
    norm_role = normalize_role(clean_title, candidate_target_roles)

    # 1. Prepare text blocks for section parsing
    full_text = ""
    if requirements_text:
        full_text += requirements_text + "\n"
    if description:
        full_text += description + "\n"
    if responsibilities_text:
        full_text += responsibilities_text + "\n"

    # Split into lines
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]

    # 2. Extract Skills with Section Awareness (Required vs Preferred)
    required_skills_dict: Dict[str, CanonicalSkill] = {}
    preferred_skills_dict: Dict[str, CanonicalSkill] = {}

    current_section = "general"  # "required", "preferred", "general"

    for line in lines:
        lower_line = line.lower()

        # Check for section header change
        is_excl_header = any(re.search(rf"\b{p}\b", lower_line) for p in EXCLUDED_SECTION_PATTERNS)
        is_pref_header = any(re.search(rf"\b{p}\b", lower_line) for p in PREFERRED_SECTION_PATTERNS)
        is_req_header = any(re.search(rf"\b{p}\b", lower_line) for p in REQUIRED_SECTION_PATTERNS)

        if is_excl_header and len(line) < 70:
            current_section = "excluded"
            continue
        elif is_pref_header and len(line) < 60:
            current_section = "preferred"
            continue
        elif is_req_header and len(line) < 60:
            current_section = "required"
            continue

        if current_section == "excluded":
            continue

        # Check line content for skill matches
        line_is_preferred = (current_section == "preferred") or bool(INLINE_PREFERRED_PATTERNS.search(lower_line))

        for key, pattern in COMPILED_SKILL_PATTERNS:
            if pattern.search(line):
                canonical = normalize_skill(key)
                canon_key = canonical.canonical_name

                if line_is_preferred:
                    # Only add to preferred if not already in required
                    if canon_key not in required_skills_dict:
                        preferred_skills_dict[canon_key] = canonical
                else:
                    # Required takes precedence
                    required_skills_dict[canon_key] = canonical
                    # Remove from preferred if previously added
                    preferred_skills_dict.pop(canon_key, None)

    # 3. Extract Experience Requirements
    min_exp: Optional[float] = None
    max_exp: Optional[float] = None
    exp_snippet: Optional[str] = None

    # Focus search on requirements text, title, or description
    exp_search_text = f"{clean_title}\n{requirements_text or ''}\n{description or ''}"
    
    # Try range pattern first (e.g., "1-3 years")
    range_match = EXP_RANGE_PATTERN.search(exp_search_text)
    if range_match:
        try:
            min_exp = float(range_match.group(1))
            max_exp = float(range_match.group(2))
            exp_snippet = range_match.group(0)
        except ValueError:
            pass

    if min_exp is None:
        plus_match = EXP_PLUS_PATTERN.search(exp_search_text)
        if plus_match:
            try:
                min_exp = float(plus_match.group(1))
                exp_snippet = plus_match.group(0)
            except ValueError:
                pass

    if min_exp is None:
        min_match = EXP_MIN_PATTERN.search(exp_search_text)
        if min_match:
            try:
                min_exp = float(min_match.group(1))
                exp_snippet = min_match.group(0)
            except ValueError:
                pass

    if min_exp is None:
        gen_match = EXP_GENERAL_PATTERN.search(exp_search_text)
        if gen_match:
            try:
                min_exp = float(gen_match.group(1))
                exp_snippet = gen_match.group(0)
            except ValueError:
                pass

    # 4. Extract Education Requirements
    education_reqs: List[str] = []
    edu_match = DEGREE_PATTERN.search(exp_search_text)
    stem_match = STEM_PATTERN.search(exp_search_text)
    if edu_match:
        degree_found = edu_match.group(1)
        field_found = stem_match.group(1) if stem_match else "relevant field"
        education_reqs.append(f"{degree_found.title()} in {field_found.title()}")

    # 5. Extract Work Mode
    work_modes: List[str] = []
    if work_mode and work_mode.lower() != "unknown":
        work_modes.append(work_mode.lower())
    else:
        # Check text
        lower_loc = (location or "").lower()
        lower_all = f"{clean_title.lower()} {lower_loc} {full_text[:500].lower()}"
        if "remote" in lower_all or "anywhere" in lower_all or "worldwide" in lower_all:
            work_modes.append("remote")
        elif "hybrid" in lower_all:
            work_modes.append("hybrid")
        elif "on-site" in lower_all or "onsite" in lower_all or "in-office" in lower_all:
            work_modes.append("on-site")

    # 6. Extract Employment Type
    emp_type: Optional[str] = None
    lower_desc = full_text[:1000].lower()
    if "full-time" in lower_desc or "full time" in lower_desc:
        emp_type = "Full-time"
    elif "contract" in lower_desc or "freelance" in lower_desc:
        emp_type = "Contract"
    elif "internship" in lower_desc or "intern" in lower_desc or "intern" in clean_title.lower():
        emp_type = "Internship"
    elif "part-time" in lower_desc or "part time" in lower_desc:
        emp_type = "Part-time"

    # 7. Contextual Specialization for General Technical Roles
    # If the title is generic (e.g. "Software Engineer"), check if description heavily demands target skills
    if norm_role.relevance_tier == "TRANSFERABLE" and norm_role.concept in (
        "General Software Engineer", "General Software Developer", "Core Software Engineer"
    ):
        ai_ml_skills = {"LLMs", "RAG", "LangChain", "PyTorch", "TensorFlow", "Generative AI", "Machine Learning", "Deep Learning", "NLP", "Computer Vision"}
        backend_skills = {"FastAPI", "Django", "PostgreSQL", "REST APIs", "Redis", "Distributed Systems"}

        req_skill_names = {s.canonical_name for s in required_skills_dict.values()}
        has_ai_skill = bool(req_skill_names.intersection(ai_ml_skills))
        has_backend_skill = bool(req_skill_names.intersection(backend_skills))

        # Also check explicit text if few skills extracted
        if not has_ai_skill and any(k in lower_desc for k in ["machine learning", "large language model", "llm", "generative ai", "deep learning"]):
            has_ai_skill = True
        if not has_backend_skill and any(k in lower_desc for k in ["backend systems", "rest apis", "distributed systems", "database architecture"]):
            has_backend_skill = True

        if has_ai_skill:
            norm_role = NormalizedRole(
                concept="Software Engineer (AI/ML Specialization)",
                target_role="AI Engineer",
                priority_rank=1,
                fit_level="ADJACENT",
                score=78.0,
                explanation=f"Role '{clean_title}' is general software engineering, but requirements explicitly demand AI/ML specialization.",
                role_family="AI_ML",
                relevance_tier="ADJACENT",
                is_target_career_aligned=True,
            )
        elif has_backend_skill:
            norm_role = NormalizedRole(
                concept="Software Engineer (Backend Specialization)",
                target_role="Backend Engineer",
                priority_rank=3,
                fit_level="ADJACENT",
                score=75.0,
                explanation=f"Role '{clean_title}' is general software engineering, but requirements explicitly demand backend architecture.",
                role_family="BACKEND",
                relevance_tier="ADJACENT",
                is_target_career_aligned=True,
            )

    return JobRequirements(
        raw_title=clean_title,
        role=norm_role.concept,
        normalized_role=norm_role,
        required_skills=list(required_skills_dict.values()),
        preferred_skills=list(preferred_skills_dict.values()),
        minimum_experience=min_exp,
        maximum_experience=max_exp,
        experience_text=exp_snippet,
        location=location.strip() if location else None,
        work_modes=work_modes,
        employment_type=emp_type,
        salary_min=float(salary_min) if salary_min is not None else None,
        salary_max=float(salary_max) if salary_max is not None else None,
        currency=currency or "USD",
        education_requirements=education_reqs,
    )
