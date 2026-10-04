import re
from typing import Optional, Tuple, Dict, List
from intelligence.models import CanonicalSkill, NormalizedRole

# Canonical skill aliases mapping
# Lowercase alias -> Official Canonical Name
CANONICAL_SKILL_MAP: Dict[str, str] = {
    # AI / Generative AI / LLMs
    "rag": "RAG",
    "retrieval-augmented generation": "RAG",
    "retrieval augmented generation": "RAG",
    "rag (retrieval-augmented generation)": "RAG",
    "llm": "LLMs",
    "llms": "LLMs",
    "large language models": "LLMs",
    "large language model": "LLMs",
    "generative ai": "Generative AI",
    "genai": "Generative AI",
    "prompt engineering": "Prompt Engineering",
    "agentic ai": "Agentic AI",
    "ai agents": "Agentic AI",
    "ai agent": "Agentic AI",
    "agentic workflows": "Agentic AI",
    "ai agent architecture": "Agentic AI",
    "ai automation architecture": "Agentic AI",
    "llm evaluation": "LLM Evaluation",
    "ai evaluation": "LLM Evaluation",
    "fine-tuning": "Fine-tuning",
    "finetuning": "Fine-tuning",
    "transfer learning": "Transfer Learning",
    
    # AI Frameworks & Libraries
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "transformers": "Hugging Face Transformers",
    "hugging face transformers": "Hugging Face Transformers",
    "huggingface transformers": "Hugging Face Transformers",
    "hugging face": "Hugging Face Transformers",
    "huggingface": "Hugging Face Transformers",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "scikit-learn": "Scikit-learn",
    "scikitlearn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "opencv": "OpenCV",
    "mediapipe": "MediaPipe",
    
    # NLP / Computer Vision
    "nlp": "NLP",
    "natural language processing": "NLP",
    "computer vision": "Computer Vision",
    "cv": "Computer Vision",
    "deep learning": "Deep Learning",
    "machine learning": "Machine Learning",
    "bert": "BERT",
    "bertweet": "BERTweet",
    "goemotions": "GoEmotions",
    "resnet": "ResNet",
    "tf-idf": "TF-IDF",
    "tfidf": "TF-IDF",
    
    # Vector Search & Retrieval
    "vector databases": "Vector Databases",
    "vector database": "Vector Databases",
    "vector db": "Vector Databases",
    "chromadb": "ChromaDB",
    "chroma": "ChromaDB",
    "pinecone": "Pinecone",
    "weaviate": "Weaviate",
    "qdrant": "Qdrant",
    "faiss": "FAISS",
    "vector embeddings": "Vector Embeddings",
    "embeddings": "Vector Embeddings",
    "semantic search": "Semantic Search",

    # Programming Languages
    "python": "Python",
    "python3": "Python",
    "sql": "SQL",
    "c": "C",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "golang": "Golang",
    "go": "Golang",
    "rust": "Rust",
    "java": "Java",
    "ruby": "Ruby",
    "php": "PHP",
    "scala": "Scala",

    # Backend / Databases
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "rest apis": "REST APIs",
    "rest api": "REST APIs",
    "rest": "REST APIs",
    "restful": "REST APIs",
    "restful apis": "REST APIs",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "firebase": "Firebase",
    "supabase": "Supabase",
    "prisma": "Prisma",
    "redis": "Redis",
    "mongodb": "MongoDB",

    # Cloud / DevOps / Infrastructure
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "ci/cd": "CI/CD",
    "github actions": "GitHub Actions",
    "aws": "AWS",
    "amazon web services": "AWS",
    "google cloud": "Google Cloud",
    "gcp": "Google Cloud",
    "google cloud platform": "Google Cloud",
    "render": "Render",
    "vercel": "Vercel",
    "terraform": "Terraform",
    "linux": "Linux",

    # Frontend (for context recognition)
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "vue": "Vue",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "angular": "Angular",
    "svelte": "Svelte",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "streamlit": "Streamlit",

    # Engineering Practices
    "system design": "System Design",
    "backend architecture": "Backend Architecture",
    "api integration": "API Integration",
    "production deployment": "Production Deployment",
    "reliability engineering": "Reliability Engineering",
    "performance optimization": "Performance Optimization",
    "testing": "Testing",
    "technical leadership": "Technical Leadership",
    "cross-functional collaboration": "Cross-functional Collaboration",
    "data science": "Data Science",
    "data engineering": "Data Engineering",
    "data analysis": "Data Analysis",
    "mlops": "MLOps",
}


def normalize_skill(skill_str: str) -> CanonicalSkill:
    """
    Normalize a raw skill string to its canonical concept without loss of provenance.
    Preserves source_name and canonical_name.
    """
    cleaned = skill_str.strip()
    key = cleaned.lower()

    # Direct map lookup
    if key in CANONICAL_SKILL_MAP:
        return CanonicalSkill(source_name=cleaned, canonical_name=CANONICAL_SKILL_MAP[key])

    # Stripped parentheses lookup (e.g. "RAG (Retrieval-Augmented Generation)")
    no_paren = re.sub(r"\(.*?\)", "", key).strip()
    if no_paren in CANONICAL_SKILL_MAP:
        return CanonicalSkill(source_name=cleaned, canonical_name=CANONICAL_SKILL_MAP[no_paren])

    # Fallback to cleaned title-cased representation
    return CanonicalSkill(source_name=cleaned, canonical_name=cleaned)


# -------------------------------------------------------------
# CANDIDATE TARGET ROLE DEFINITIONS & FAMILIES
# -------------------------------------------------------------
# Role Family -> Concept -> List of regex patterns
TARGET_ROLE_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "AI_ML": {
        "AI Engineer": [
            r"\bai\s+engineer\b",
            r"\bai\s+developer\b",
            r"\bai\s+architect\b",
            r"\bai\s+systems?\s+engineer\b",
            r"\bai\s+agent\s+architect\b",
            r"\bapplied\s+ai\s+engineer\b",
            r"\bgenerative\s+ai\s+engineer\b",
            r"\bgenai\s+engineer\b",
            r"\bgenai\s+developer\b",
            r"\bllm\s+engineer\b",
            r"\bllm\s+developer\b",
            r"\bai/ml\s+engineer\b",
            r"\bml/ai\s+engineer\b",
        ],
        "ML Engineer": [
            r"\bmachine\s+learning\s+engineer\b",
            r"\bml\s+engineer\b",
            r"\bapplied\s+ml\b",
            r"\bmachine\s+learning\s+developer\b",
            r"\bdeep\s+learning\s+engineer\b",
            r"\bnlp\s+engineer\b",
            r"\bnatural\s+language\s+processing\s+engineer\b",
            r"\bcomputer\s+vision\s+engineer\b",
            r"\bvision\s+engineer\b",
            r"\bapplied\s+scientist\b",
            r"\bmlops\s+engineer\b",
        ],
    },
    "BACKEND": {
        "Backend Engineer": [
            r"\bbackend\s+engineer\b",
            r"\bback-end\s+engineer\b",
            r"\bbackend\s+developer\b",
            r"\bback-end\s+developer\b",
            r"\bpython\s+backend\b",
            r"\bpython\s+developer\b",
            r"\bpython\s+engineer\b",
            r"\bpython\s+software\s+engineer\b",
            r"\bsoftware\s+engineer\s*-\s*backend\b",
            r"\bsoftware\s+developer\s*-\s*backend\b",
            r"\bapi\s+engineer\b",
            r"\bapi\s+developer\b",
            r"\bserver-side\s+engineer\b",
            r"\bserver\s+engineer\b",
            r"\bdistributed\s+systems\s+engineer\b",
            r"\bsystems\s+engineer\b",
        ],
    },
    "FDE_CONSULTING": {
        "Forward Deployed Engineer (FDE)": [
            r"\bforward\s+deployed\s+engineer\b",
            r"\bforward\s+deployed\s+software\b",
            r"\bforward\s+deployed\s+ai\b",
            r"\bfde\b",
        ],
        "Technical Consultant": [
            r"\btechnical\s+consultant\b",
            r"\btechnology\s+consultant\b",
            r"\bit\s+consultant\b",
            r"\bsolutions\s+engineer\b",
            r"\btechnical\s+solutions\s+engineer\b",
            r"\btechnical\s+solutions\b",
            r"\bclient\s+solutions\s+engineer\b",
            r"\bsolutions\s+architect\b",
            r"\btechnical\s+architect\b",
            r"\bimplementation\s+engineer\b",
            r"\bcustomer\s+engineer\b",
            r"\btechnical\s+product\s+consultant\b",
            r"\bdeployment\s+engineer\b",
            r"\bintegration\s+engineer\b",
        ],
    },
}

# -------------------------------------------------------------
# ADJACENT ROLE DEFINITIONS (Close Specializations)
# -------------------------------------------------------------
ADJACENT_ROLES: List[Tuple[str, str, str, float]] = [
    # (regex_pattern, concept, family, default_score)
    (r"\bai\s+platform\s+engineer\b|\bai\s+platform\b", "AI Platform Engineer", "AI_ML", 78.0),
    (r"\bapplied\s+ai\b", "Applied AI Engineer", "AI_ML", 82.0),
    (r"\bdata\s+scientist\b", "Data Scientist", "AI_ML", 74.0),
    (r"\bresearch\s+engineer\b", "Research Engineer", "AI_ML", 72.0),
    (r"\bproduct\s+engineer\b", "Product Engineer", "PRODUCT_ENGINEERING", 72.0),
    (r"\bdata\s+engineer\b", "Data Engineer", "DATA_ENGINEERING", 68.0),
    (r"\bplatform\s+engineer\b", "Platform Engineer", "INFRA_DEVOPS", 65.0),
    (r"\bcloud\s+engineer\b", "Cloud Infrastructure Engineer", "INFRA_DEVOPS", 65.0),
    (r"\bimplementation\s+specialist\b", "Implementation Specialist", "FDE_CONSULTING", 64.0),
    (r"\btechnical\s+product\s+manager\b|\btpm\b", "Technical Product Manager", "PRODUCT_ENGINEERING", 60.0),
    (r"\bdatabase\s+engineer\b", "Database Engineer", "BACKEND", 70.0),
]

# -------------------------------------------------------------
# TRANSFERABLE TECHNICAL ROLES (General Technical Foundations)
# -------------------------------------------------------------
TRANSFERABLE_ROLES: List[Tuple[str, str, str, float]] = [
    # (regex_pattern, concept, family, default_score)
    (r"\bsoftware\s+engineer\b", "General Software Engineer", "GENERAL_SOFTWARE", 55.0),
    (r"\bsoftware\s+developer\b", "General Software Developer", "GENERAL_SOFTWARE", 55.0),
    (r"\bfull\s*stack\b|\bfullstack\b", "Full-Stack Engineer", "GENERAL_SOFTWARE", 52.0),
    (r"\bcore\s+engineer\b", "Core Software Engineer", "GENERAL_SOFTWARE", 54.0),
    (r"\bdevops\b|\bsite\s+reliability\b|\bsre\b", "DevOps / Reliability Engineer", "INFRA_DEVOPS", 48.0),
    (r"\bdata\s+analyst\b|\bbusiness\s+intelligence\b", "Data Analyst", "DATA_ANALYTICS", 45.0),
    (r"\bfrontend\b|\bfront-end\b|\bweb\s+developer\b", "Frontend Web Developer", "FRONTEND", 45.0),
    (r"\bqa\s+engineer\b|\btest\s+engineer\b|\bsdet\b|\bquality\s+assurance\b", "QA / Test Engineer", "QA_TESTING", 42.0),
    (r"\btechnical\s+support\b|\bsupport\s+engineer\b|\bservice\s+desk\s+engineer\b", "Technical Support Engineer", "TECH_SUPPORT", 40.0),
]

# -------------------------------------------------------------
# UNRELATED ROLES TAXONOMY (Clearly Outside Career Scope)
# -------------------------------------------------------------
UNRELATED_ROLE_PATTERNS: List[Tuple[str, str, str]] = [
    # (regex_pattern, concept, family)
    # Writing & Content
    (r"\b(?:freelance\s+)?writers?\b|\bcontent\s+writers?\b|\bcopywriters?\b|\bghostwriters?\b|\beditors?\b|\bproofreaders?\b|\bbloggers?\b|\bjournalists?\b|\bcontent\s+creators?\b|\bscriptwriters?\b", "Writing / Editorial", "WRITING_CONTENT"),
    # Sales & Commercial
    (r"\bsales\b|\baccount\s+executives?\b|\bcommercial\b|\bbdr\b|\bsdr\b|\bbusiness\s+development\b|\btelemarketers?\b|\binside\s+sales\b|\bclosers?\b", "Sales / Commercial", "SALES"),
    # Customer Support (Non-technical)
    (r"\bcustomer\s+(?:support|service|care|success\s+associate)\b|\bkundenservice\b|\bcall\s+center\b|\bclient\s+support\b|\binbound\b|\boutbound\b", "Customer Support / Service", "CUSTOMER_SERVICE"),
    # HR & Recruiting
    (r"\b(?:hr|human\s+resources)\b|\brecruiters?\b|\btalent\s+acquisition\b|\bpeople\s+operations\b|\bstaffing\b|\bheadhunters?\b", "HR / Recruiting", "HR_RECRUITING"),
    # Design & Creative
    (r"\bgraphic\s+designers?\b|\bui/ux\b|\bux\s+designers?\b|\billustrators?\b|\banimators?\b|\bvideo\s+editors?\b|\bvisual\s+designers?\b|\bcreative\s+directors?\b", "Design / Creative", "DESIGN"),
    # Marketing & Social Media
    (r"\bmarketing\b|\bsocial\s+media\b|\bcommunity\s+managers?\b|\bseo\s+specialists?\b|\bbrand\s+strategists?\b|\bcampaign\s+managers?\b", "Marketing / Social Media", "MARKETING"),
    # Accounting, Finance & Legal
    (r"\baccountants?\b|\bbookkeepers?\b|\bauditors?\b|\bfinancial\s+analysts?\b|\bpayroll\b|\blegal\b|\bparalegals?\b", "Finance / Accounting / Legal", "FINANCE_LEGAL"),
    # Administration & Clerical
    (r"\b(?:administrative|executive|virtual|office)\s+assistants?\b|\boffice\s+assistants?\b|\breceptionists?\b|\bclerks?\b|\bdata\s+entry\b", "Administrative / Clerical", "ADMIN_CLERICAL"),
    # Operations & Trades
    (r"\bwarehouse\b|\bdrivers?\b|\bcouriers?\b|\bnurses?\b|\bcaregivers?\b|\bcooks?\b|\bchefs?\b|\bcashiers?\b|\bmerchandisers?\b", "Operations / Services", "OPERATIONS_SERVICES"),
    # Niche Non-Engineering
    (r"\bcontent\s+reviewers?\b|\bdata\s+annotation\b|\bshopify\s+developers?\b|\bshopify\b|\bwordpress\b", "Niche Non-Engineering", "NICHE_NON_ENGINEERING"),
]

TECHNICAL_INDICATOR_PATTERN = re.compile(
    r"\b(engineer(?:ing)?|developer|software|architect|programmer|data|computing|tech(?:nical)?|coder|systems?|platform|devops|sre|algorithm|backend|frontend|fullstack|ml|ai|nlp|cv|api|cloud|database|infrastructure|embedded|firmware|cybersecurity|security|linux|python|java|golang|rust|c\+\+|react)\b",
    re.IGNORECASE
)


def normalize_role(title: str, candidate_target_roles: Optional[List[str]] = None) -> NormalizedRole:
    """
    Conservatively normalize a job title to determine career relevance tier and family.
    Distinguishes:
      - DIRECT: Target career role alignment (AI/ML, Backend, FDE/Tech Consulting)
      - ADJACENT: Close technical specializations (Data Science, AI Platform, Systems)
      - TRANSFERABLE: General software/technical foundations (SWE, Fullstack, DevOps)
      - UNRELATED: Clearly non-technical or outside candidate scope (Writing, Sales, HR, Admin)
      - UNKNOWN: Vague or missing title
    """
    if not title or not title.strip():
        return NormalizedRole(
            concept="Unknown Role",
            target_role=None,
            priority_rank=None,
            fit_level="UNKNOWN",
            score=30.0,
            explanation="Job title is not specified.",
            role_family="UNKNOWN",
            relevance_tier="UNKNOWN",
            is_target_career_aligned=False,
        )

    clean_title = title.lower().strip()

    target_priority = candidate_target_roles or [
        "AI Engineer",
        "ML Engineer",
        "Backend Engineer",
        "Forward Deployed Engineer (FDE)",
        "Technical Consultant",
    ]

    # 1. Check for Direct Match in Candidate Target Families
    for family, concepts in TARGET_ROLE_TAXONOMY.items():
        for role_name, patterns in concepts.items():
            for pat in patterns:
                if re.search(pat, clean_title, re.IGNORECASE):
                    # Determine priority rank if it matches candidate's explicit target list
                    rank = None
                    for idx, t in enumerate(target_priority):
                        if t.lower() in role_name.lower() or role_name.lower() in t.lower():
                            rank = idx + 1
                            break

                    # Priority-weighted scoring
                    if rank == 1:
                        score = 100.0
                        explanation = f"Direct alignment with #1 target role: {role_name} ({family})."
                    elif rank == 2:
                        score = 92.0
                        explanation = f"High alignment with #2 target role: {role_name} ({family})."
                    elif rank == 3:
                        score = 85.0
                        explanation = f"Strong alignment with #3 target role: {role_name} ({family})."
                    elif rank == 4:
                        score = 78.0
                        explanation = f"Aligned with #4 target role: {role_name} ({family})."
                    elif rank == 5:
                        score = 72.0
                        explanation = f"Aligned with #5 target role: {role_name} ({family})."
                    else:
                        score = 80.0
                        explanation = f"Direct alignment with target role family: {family} ({role_name})."

                    return NormalizedRole(
                        concept=role_name,
                        target_role=role_name,
                        priority_rank=rank,
                        fit_level="STRONG",
                        score=score,
                        explanation=explanation,
                        role_family=family,
                        relevance_tier="DIRECT",
                        is_target_career_aligned=True,
                    )

    # 2. Check for Adjacent Technical Roles
    for pat, concept, family, default_score in ADJACENT_ROLES:
        if re.search(pat, clean_title, re.IGNORECASE):
            return NormalizedRole(
                concept=concept,
                target_role=None,
                priority_rank=None,
                fit_level="ADJACENT",
                score=default_score,
                explanation=f"Role '{title}' is an adjacent technical specialization ({concept} - {family}) sharing strong domain overlap.",
                role_family=family,
                relevance_tier="ADJACENT",
                is_target_career_aligned=True,
            )

    # 3. Check for Explicitly Unrelated Domains (Writing, Sales, HR, Customer Service, Admin, etc.)
    for pat, concept, family in UNRELATED_ROLE_PATTERNS:
        if re.search(pat, clean_title, re.IGNORECASE):
            return NormalizedRole(
                concept=concept,
                target_role=None,
                priority_rank=None,
                fit_level="WEAK",
                score=10.0,
                explanation=f"Role '{title}' is in an unrelated domain ({concept}) outside candidate's target engineering careers.",
                role_family=family,
                relevance_tier="UNRELATED",
                is_target_career_aligned=False,
            )

    # 4. Check for Transferable Technical Roles (General Software, Fullstack, QA, Support)
    for pat, concept, family, default_score in TRANSFERABLE_ROLES:
        if re.search(pat, clean_title, re.IGNORECASE):
            return NormalizedRole(
                concept=concept,
                target_role=None,
                priority_rank=None,
                fit_level="MODERATE",
                score=default_score,
                explanation=f"Role '{title}' shares foundational software skills ({concept}) but is outside primary target roles.",
                role_family=family,
                relevance_tier="TRANSFERABLE",
                is_target_career_aligned=False,
            )

    # 5. Fallback Analysis for Unlisted Titles: Distinguish Technical vs Non-Technical
    if TECHNICAL_INDICATOR_PATTERN.search(clean_title):
        return NormalizedRole(
            concept="Other Technical Role",
            target_role=None,
            priority_rank=None,
            fit_level="MODERATE",
            score=40.0,
            explanation=f"Role '{title}' contains general technical keywords but is outside candidate's primary target tracks.",
            role_family="GENERAL_TECHNICAL",
            relevance_tier="TRANSFERABLE",
            is_target_career_aligned=False,
        )

    # Unlisted title with ZERO technical indicators: Fundamentally Unrelated
    return NormalizedRole(
        concept="Non-Technical / Unrelated Role",
        target_role=None,
        priority_rank=None,
        fit_level="WEAK",
        score=10.0,
        explanation=f"Role '{title}' does not indicate an engineering or technical role and is outside candidate's career direction.",
        role_family="UNRELATED",
        relevance_tier="UNRELATED",
        is_target_career_aligned=False,
    )

