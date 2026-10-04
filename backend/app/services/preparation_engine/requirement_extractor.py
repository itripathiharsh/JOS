import re
from typing import Optional, List, Dict, Set
from app.models.job import Job
from intelligence.extractor import (
    extract_job_requirements,
    REQUIRED_SECTION_PATTERNS,
    PREFERRED_SECTION_PATTERNS,
    EXCLUDED_SECTION_PATTERNS,
)
from app.services.preparation_engine.models import ExtractedJobRequirements


RESPONSIBILITY_SECTION_PATTERNS = [
    r"responsibilities",
    r"what you(?:'ll|\s+will)\s+do",
    r"your\s+role",
    r"what you will be doing",
    r"core\s+responsibilities",
    r"duties",
    r"about the role",
    r"the role",
    r"day to day",
    r"your mission",
]

# Noise / Stopwords to exclude from extracted ATS keywords
EXCLUDED_KEYWORDS = {
    "and", "the", "with", "for", "you", "our", "will", "are", "team", "role",
    "work", "company", "years", "experience", "looking", "join", "opportunity",
    "skills", "ability", "must", "have", "preferred", "qualifications", "strong",
    "working", "remote", "candidate", "position", "plus", "help", "build", "create",
}


def clean_bullet(line: str) -> str:
    """Strips bullet symbols, numbers, and excess whitespace."""
    cleaned = re.sub(r"^[\s*\-•–—#\d\.\)]+", "", line).strip()
    return cleaned


def extract_section_lines(text: str, target_headers: List[str], stop_headers: List[str]) -> List[str]:
    """Extracts bullet lines belonging to a specific named section."""
    if not text:
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    in_target_section = False
    result: List[str] = []

    for line in lines:
        lower_line = line.lower()
        is_target = any(re.search(rf"\b{p}\b", lower_line) for p in target_headers)
        is_stop = any(re.search(rf"\b{p}\b", lower_line) for p in stop_headers)

        if is_target and len(line) < 70:
            in_target_section = True
            continue

        if in_target_section:
            if is_stop and len(line) < 70:
                in_target_section = False
                break
            cleaned = clean_bullet(line)
            if cleaned and len(cleaned) > 15:
                result.append(cleaned)

    return result


def extract_application_requirements(job: Job) -> ExtractedJobRequirements:
    """
    Deterministic extraction of job requirements, separating:
    - Required qualifications
    - Preferred qualifications
    - Responsibilities
    - ATS Keywords
    """
    # 1. Base Intelligence Extraction
    base_reqs = extract_job_requirements(
        title=job.title,
        description=job.description,
        requirements_text=job.requirements,
        responsibilities_text=job.responsibilities,
        location=job.location,
        work_mode=job.work_mode,
        salary_min=float(job.salary_min) if job.salary_min is not None else None,
        salary_max=float(job.salary_max) if job.salary_max is not None else None,
        currency=job.currency,
    )

    full_text = f"{job.title}\n{job.requirements or ''}\n{job.description or ''}\n{job.responsibilities or ''}"

    # 2. Extract Responsibilities
    responsibilities: List[str] = []
    if job.responsibilities:
        for line in job.responsibilities.splitlines():
            cleaned = clean_bullet(line)
            if cleaned and len(cleaned) > 15:
                responsibilities.append(cleaned)
    else:
        # Extract from description
        all_stop_headers = REQUIRED_SECTION_PATTERNS + PREFERRED_SECTION_PATTERNS + EXCLUDED_SECTION_PATTERNS
        responsibilities = extract_section_lines(
            job.description or "",
            RESPONSIBILITY_SECTION_PATTERNS,
            all_stop_headers,
        )

    # If still empty, formulate standard role responsibilities based on title and matched areas
    if not responsibilities:
        if "ai" in job.title.lower() or "ml" in job.title.lower() or "learning" in job.title.lower():
            responsibilities = [
                "Develop and optimize machine learning models, generative AI architectures, and prompt pipelines.",
                "Implement retrieval-augmented generation (RAG) and integrate vector search repositories.",
                "Collaborate with engineering teams to deploy AI solutions into reliable production environments.",
            ]
        elif "backend" in job.title.lower() or "software" in job.title.lower():
            responsibilities = [
                "Architect, build, and maintain robust, scalable backend services and REST APIs.",
                "Design schema migrations, relational database structures, and query optimizations.",
                "Implement testing, CI/CD integration, and high-performance server-side logic.",
            ]
        else:
            responsibilities = [
                f"Execute core software engineering and technical duties for the {job.title} role.",
                "Participate in agile development, code reviews, and cross-functional team delivery.",
            ]

    # Limit to top 6 crisp responsibility points
    responsibilities = responsibilities[:6]

    # 3. Extract Structured Required Qualifications
    required_quals: List[str] = []

    # Experience requirement
    if base_reqs.minimum_experience is not None:
        if base_reqs.maximum_experience is not None:
            required_quals.append(f"{int(base_reqs.minimum_experience)} to {int(base_reqs.maximum_experience)} years of practical software/engineering experience")
        else:
            required_quals.append(f"At least {int(base_reqs.minimum_experience)}+ years of relevant technical experience")
    else:
        required_quals.append("Demonstrated foundational engineering experience or relevant internship/project background")

    # Required Skills
    req_skills_list = [s.canonical_name for s in base_reqs.required_skills]
    if req_skills_list:
        required_quals.append(f"Core technical proficiency in: {', '.join(req_skills_list[:6])}")

    # Education
    if base_reqs.education_requirements:
        required_quals.append(f"Degree requirement: {', '.join(base_reqs.education_requirements)}")
    else:
        required_quals.append("Bachelor's degree in Computer Science, Data Science, Engineering, or equivalent practical experience")

    # Location / Work authorization
    if job.location:
        required_quals.append(f"Location / Timezone eligibility: {job.location}")
    if job.work_mode and job.work_mode.lower() != "unknown":
        required_quals.append(f"Work arrangement: {job.work_mode.title()}")

    # Raw requirement lines from text if available
    req_lines = extract_section_lines(
        job.requirements or job.description or "",
        REQUIRED_SECTION_PATTERNS,
        PREFERRED_SECTION_PATTERNS + RESPONSIBILITY_SECTION_PATTERNS + EXCLUDED_SECTION_PATTERNS,
    )
    for rline in req_lines[:3]:
        if not any(rline.lower() in q.lower() for q in required_quals):
            required_quals.append(rline)

    # 4. Extract Structured Preferred Qualifications
    preferred_quals: List[str] = []
    pref_skills_list = [s.canonical_name for s in base_reqs.preferred_skills]
    if pref_skills_list:
        preferred_quals.append(f"Preferred familiarity with: {', '.join(pref_skills_list[:6])}")

    pref_lines = extract_section_lines(
        job.requirements or job.description or "",
        PREFERRED_SECTION_PATTERNS,
        RESPONSIBILITY_SECTION_PATTERNS + EXCLUDED_SECTION_PATTERNS,
    )
    for pline in pref_lines[:3]:
        preferred_quals.append(pline)

    if not preferred_quals:
        preferred_quals.append("Experience with modern cloud platforms, containerization (Docker), and automated testing")

    # 5. Extract ATS Keywords (Normalized skills + title tokens + high-signal domain terms)
    keywords_set: Set[str] = set()

    for s in base_reqs.required_skills:
        keywords_set.add(s.canonical_name)
    for s in base_reqs.preferred_skills:
        keywords_set.add(s.canonical_name)

    # Title keywords
    for word in re.findall(r"[A-Za-z0-9+#.-]{2,}", job.title):
        clean_word = word.strip(".#")
        if clean_word.lower() not in EXCLUDED_KEYWORDS and len(clean_word) >= 2:
            keywords_set.add(clean_word)

    # Domain keywords in text
    domain_terms = [
        "RAG", "LLM", "LLMs", "FastAPI", "Python", "LangChain", "LangGraph", "ChromaDB",
        "Vector Search", "Docker", "Kubernetes", "PostgreSQL", "REST APIs", "Microservices",
        "CI/CD", "Machine Learning", "Deep Learning", "Transformers", "NLP", "Prompt Engineering",
        "Streamlit", "PyTorch", "TensorFlow", "Redis", "Cloud", "Git", "GitHub", "SQL",
    ]
    for term in domain_terms:
        if re.search(rf"\b{re.escape(term)}\b", full_text, re.IGNORECASE):
            keywords_set.add(term)

    keywords_list = sorted(list(keywords_set))

    return ExtractedJobRequirements(
        required_qualifications=required_quals,
        preferred_qualifications=preferred_quals,
        required_skills=req_skills_list,
        preferred_skills=pref_skills_list,
        responsibilities=responsibilities,
        keywords=keywords_list,
        min_experience_years=base_reqs.minimum_experience,
        max_experience_years=base_reqs.maximum_experience,
        required_degree=base_reqs.education_requirements[0] if base_reqs.education_requirements else "Bachelor's in CS / STEM",
        required_location=job.location,
        work_mode=job.work_mode,
        employment_type=base_reqs.employment_type or "Full-time",
    )
