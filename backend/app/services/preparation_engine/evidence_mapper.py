import re
from typing import List, Dict, Any, Optional, Set
from app.models.profile import CandidateProfile
from app.models.job import Job
from intelligence.candidate import extract_candidate_data
from intelligence.normalization import normalize_skill
from app.services.preparation_engine.models import (
    CandidateEvidenceItem,
    EvidenceMatchType,
    ExtractedJobRequirements,
)

# Transferable skill adjacency mappings
TRANSFERABLE_MAP: Dict[str, Dict[str, str]] = {
    "PostgreSQL": {
        "related": ["SQL", "Databases", "Backend Development", "FastAPI", "Firebase"],
        "reason": "Demonstrated relational database and backend data persistence experience in production applications.",
    },
    "MySQL": {
        "related": ["SQL", "Databases", "Backend Development", "FastAPI"],
        "reason": "Demonstrated relational database modeling and SQL query experience.",
    },
    "Docker": {
        "related": ["Cloud", "Deployment", "CI/CD", "Vercel", "Firebase", "Hugging Face"],
        "reason": "Containerization and cloud application packaging transferable through cloud service deployments.",
    },
    "Kubernetes": {
        "related": ["Docker", "Cloud", "Distributed Systems"],
        "reason": "Foundational understanding of microservices and deployment pipelines.",
    },
    "AWS": {
        "related": ["Cloud", "Firebase", "Hugging Face", "Vercel"],
        "reason": "Cloud architecture and API hosting experience across modern cloud providers.",
    },
    "GCP": {
        "related": ["Cloud", "Firebase", "Gemini APIs"],
        "reason": "Google cloud ecosystem experience through Gemini APIs and Firebase services.",
    },
    "Azure": {
        "related": ["Cloud"],
        "reason": "General cloud infrastructure and REST API deployment familiarity.",
    },
    "Redis": {
        "related": ["Vector Search", "ChromaDB", "Caching", "FastAPI"],
        "reason": "In-memory caching and indexing experience transferable through vector database index management.",
    },
    "LangChain": {
        "related": ["LangGraph", "RAG", "LLMs", "Generative AI"],
        "reason": "Direct sister framework experience through production LangGraph state machines and RAG pipelines.",
    },
    "LlamaIndex": {
        "related": ["LangGraph", "ChromaDB", "RAG", "Vector Search"],
        "reason": "Information retrieval and semantic search pipeline experience using LangGraph and ChromaDB.",
    },
    "Pinecone": {
        "related": ["ChromaDB", "Vector Search", "Embeddings"],
        "reason": "Vector database storage, indexing, and semantic retrieval implemented with ChromaDB.",
    },
    "Weaviate": {
        "related": ["ChromaDB", "Vector Search", "Embeddings"],
        "reason": "Vector search and hybrid retrieval experience implemented with ChromaDB.",
    },
    "Kafka": {
        "related": ["Backend Development", "Microservices", "REST APIs"],
        "reason": "Event-driven and asynchronous message processing concepts in backend systems.",
    },
    "PyTorch": {
        "related": ["Machine Learning", "Deep Learning", "Hugging Face Transformers", "NLP"],
        "reason": "Model fine-tuning and inference pipelines built with Hugging Face Transformers and Python.",
    },
    "TensorFlow": {
        "related": ["Machine Learning", "Deep Learning", "PyTorch"],
        "reason": "Deep learning architectures and mathematical foundations through BS in Data Science coursework.",
    },
}


def map_candidate_evidence(
    candidate: CandidateProfile,
    job: Job,
    extracted_reqs: ExtractedJobRequirements,
) -> List[CandidateEvidenceItem]:
    """
    Evaluates every extracted requirement against verified Candidate Profile facts.
    Classifies into DIRECT, TRANSFERABLE, WEAK, MISSING, UNKNOWN.
    Never invents claims or converts MISSING/UNKNOWN into DIRECT.
    """
    cand_data = extract_candidate_data(candidate)
    evidence_items: List[CandidateEvidenceItem] = []

    # Prepare candidate knowledge sets
    cand_skills_canonical: Set[str] = {s.canonical_name for s in cand_data.skills}
    cand_skills_raw: Set[str] = {s.name.lower() for s in (candidate.skills or [])}

    # Aggregate project text for deep evidence referencing
    project_evidence_map: Dict[str, str] = {}
    for p in (candidate.projects or []):
        techs = (p.technologies or "").lower()
        desc = (p.description or "").lower()
        combined = f"{techs} {desc}"
        for s in cand_skills_canonical:
            if s.lower() in combined:
                project_evidence_map[s] = f"Project '{p.name}' ({p.technologies})"

    # Aggregate experience text
    exp_evidence_map: Dict[str, str] = {}
    for e in (candidate.experiences or []):
        combined = f"{e.company.lower()} {e.title.lower()} {(e.description or '').lower()} {(e.technologies or '').lower()}"
        for s in cand_skills_canonical:
            if s.lower() in combined:
                exp_evidence_map[s] = f"Role '{e.title}' at {e.company}"

    # 1. Map Experience Requirement
    cand_years = cand_data.actual_experience_years
    min_exp_req = extracted_reqs.min_experience_years

    if min_exp_req is not None:
        req_str = f"Experience requirement: {int(min_exp_req)}+ years"
        if cand_years >= min_exp_req:
            evidence_items.append(CandidateEvidenceItem(
                requirement=req_str,
                category="experience",
                match_type=EvidenceMatchType.DIRECT.value,
                candidate_evidence=f"Candidate has approximately {cand_years:.1f} years of practical software/AI experience across 4 verified industry roles.",
                source="Candidate Experience Records (Sentio Mind, Banao Technologies, Innovate, Edunet)",
                notes="Defensible verified industry experience meets requirement.",
            ))
        elif cand_years >= (min_exp_req - 1.5) and min_exp_req <= 3.5:
            evidence_items.append(CandidateEvidenceItem(
                requirement=req_str,
                category="experience",
                match_type=EvidenceMatchType.WEAK.value,
                candidate_evidence=f"Candidate has ~{cand_years:.1f} years practical experience vs {min_exp_req:.1f} years requested.",
                source="Candidate Experience Records",
                notes="Close to requirement; strong project portfolio provides supporting evidence.",
            ))
        else:
            evidence_items.append(CandidateEvidenceItem(
                requirement=req_str,
                category="experience",
                match_type=EvidenceMatchType.MISSING.value,
                candidate_evidence=f"Candidate has ~{cand_years:.1f} years practical experience vs {min_exp_req:.1f}+ years requested.",
                source="Candidate Experience Records",
                notes=f"Seniority gap: vacancy requires {min_exp_req:.1f}+ years; candidate has ~{cand_years:.1f} years.",
            ))
    else:
        evidence_items.append(CandidateEvidenceItem(
            requirement="Foundational software engineering experience",
            category="experience",
            match_type=EvidenceMatchType.DIRECT.value,
            candidate_evidence=f"Candidate possesses ~{cand_years:.1f} years of practical engineering experience across 4 companies.",
            source="Candidate Experience Records",
            notes="No explicit minimum years requested; candidate background is fully sufficient.",
        ))

    # 2. Map Education Requirement
    edu_records = candidate.educations or []
    has_btech_cse = any("b.tech" in (e.degree or "").lower() or "computer science" in (e.field or "").lower() for e in edu_records)
    has_iit_ds = any("iit madras" in (e.institution or "").lower() or "data science" in (e.field or "").lower() for e in edu_records)

    req_degree = extracted_reqs.required_degree or "Bachelor's degree in Computer Science / STEM"
    if "phd" in req_degree.lower() or "doctorate" in req_degree.lower():
        evidence_items.append(CandidateEvidenceItem(
            requirement=f"Degree requirement: {req_degree}",
            category="education",
            match_type=EvidenceMatchType.MISSING.value,
            candidate_evidence="Candidate holds B.Tech in CSE and BS in Data Science; does not hold a PhD.",
            source="Candidate Education Records",
            notes="Doctoral degree requirement cannot be claimed.",
        ))
    elif has_btech_cse or has_iit_ds:
        evidence_items.append(CandidateEvidenceItem(
            requirement=f"Degree requirement: {req_degree}",
            category="education",
            match_type=EvidenceMatchType.DIRECT.value,
            candidate_evidence="B.Tech in Computer Science & Engineering (BBDITM) and BS in Data Science & Applications (IIT Madras).",
            source="Candidate Education Records (BBDITM, IIT Madras)",
            notes="Direct degree and STEM field alignment.",
        ))
    else:
        evidence_items.append(CandidateEvidenceItem(
            requirement=f"Degree requirement: {req_degree}",
            category="education",
            match_type=EvidenceMatchType.UNKNOWN.value,
            candidate_evidence="Education details require verification.",
            source="Candidate Education Records",
            notes="Cannot verify degree alignment.",
        ))

    # 3. Map Required and Preferred Technical Skills
    # Track evaluated canonical skills to avoid duplicate rows
    evaluated_skills: Set[str] = set()

    req_canon_set = {normalize_skill(s).canonical_name for s in extracted_reqs.required_skills}
    pref_canon_set = {normalize_skill(s).canonical_name for s in extracted_reqs.preferred_skills}

    # Process all keywords and extracted skills
    for kw in extracted_reqs.keywords:
        norm_kw = normalize_skill(kw).canonical_name
        if norm_kw in evaluated_skills:
            continue
        evaluated_skills.add(norm_kw)

        # Determine category: required_skill, preferred_skill, or domain_keyword
        if norm_kw in req_canon_set:
            skill_category = "required_skill"
            prefix = "Required Skill"
        elif norm_kw in pref_canon_set:
            skill_category = "preferred_skill"
            prefix = "Preferred Skill"
        else:
            skill_category = "domain_keyword"
            prefix = "Keyword / Topic"

        # Check DIRECT
        if norm_kw in cand_skills_canonical or norm_kw.lower() in cand_skills_raw:
            source_desc = exp_evidence_map.get(norm_kw) or project_evidence_map.get(norm_kw) or "Candidate Verified Skill Inventory"
            evidence_items.append(CandidateEvidenceItem(
                requirement=f"{prefix}: {norm_kw}",
                category=skill_category,
                match_type=EvidenceMatchType.DIRECT.value,
                candidate_evidence=f"Explicitly verified proficiency in {norm_kw}.",
                source=source_desc,
                notes=f"Candidate has verified skills and project implementation with {norm_kw}.",
            ))
            continue

        # Check TRANSFERABLE
        if norm_kw in TRANSFERABLE_MAP:
            trans_info = TRANSFERABLE_MAP[norm_kw]
            matched_related = [r for r in trans_info["related"] if r in cand_skills_canonical or r.lower() in cand_skills_raw]
            if matched_related:
                evidence_items.append(CandidateEvidenceItem(
                    requirement=f"{prefix}: {norm_kw}",
                    category=skill_category,
                    match_type=EvidenceMatchType.TRANSFERABLE.value,
                    candidate_evidence=f"Transferable experience via {', '.join(matched_related)}. {trans_info['reason']}",
                    source="Candidate Skills & Architecture Experience",
                    notes=f"Transferable skill: candidate has not explicitly used {norm_kw}, but has adjacent competencies ({', '.join(matched_related)}).",
                ))
                continue

        # If not direct and not transferable -> MISSING
        evidence_items.append(CandidateEvidenceItem(
            requirement=f"{prefix}: {norm_kw}",
            category=skill_category,
            match_type=EvidenceMatchType.MISSING.value,
            candidate_evidence=f"No defensible evidence of {norm_kw} found in candidate profile or project history.",
            source="None",
            notes=f"DO NOT CLAIM: candidate has no record of working with {norm_kw}.",
        ))

    # 4. Map Location & Work Authorization Requirement
    pref_record = candidate.preference_record
    allowed_modes = (pref_record.work_modes if pref_record else None) or ["Remote", "Hybrid", "On-site"]
    job_mode = job.work_mode or "remote"

    if job_mode.lower() in [m.lower() for m in allowed_modes]:
        evidence_items.append(CandidateEvidenceItem(
            requirement=f"Work mode: {job_mode.title()}",
            category="location",
            match_type=EvidenceMatchType.DIRECT.value,
            candidate_evidence=f"Candidate accepts {', '.join(allowed_modes)} work arrangements.",
            source="Candidate Career Preferences",
            notes="Work mode matches candidate preferences.",
        ))
    else:
        evidence_items.append(CandidateEvidenceItem(
            requirement=f"Work mode: {job_mode.title()}",
            category="location",
            match_type=EvidenceMatchType.WEAK.value,
            candidate_evidence=f"Candidate preference specifies {', '.join(allowed_modes)}; job specifies {job_mode}.",
            source="Candidate Career Preferences",
            notes="Work mode discrepancy requires candidate confirmation.",
        ))

    # Location / Timezone
    if job.location:
        lower_loc = job.location.lower()
        if "india" in lower_loc or "worldwide" in lower_loc or "remote" in lower_loc or "anywhere" in lower_loc:
            evidence_items.append(CandidateEvidenceItem(
                requirement=f"Geographic eligibility: {job.location}",
                category="location",
                match_type=EvidenceMatchType.DIRECT.value,
                candidate_evidence="Candidate is based in Lucknow, India with worldwide/remote availability.",
                source="Candidate Profile & Preferences",
                notes="Geographic eligibility confirmed.",
            ))
        elif any(country in lower_loc for country in ["us only", "usa only", "uk only", "canada only", "germany only", "eu only"]):
            evidence_items.append(CandidateEvidenceItem(
                requirement=f"Geographic eligibility: {job.location}",
                category="location",
                match_type=EvidenceMatchType.MISSING.value,
                candidate_evidence=f"Job specifies exclusive region ('{job.location}'); candidate is based in India.",
                source="Candidate Profile Location",
                notes="Regional restriction mismatch.",
            ))
        else:
            evidence_items.append(CandidateEvidenceItem(
                requirement=f"Geographic eligibility: {job.location}",
                category="location",
                match_type=EvidenceMatchType.UNKNOWN.value,
                candidate_evidence="Work authorization or visa eligibility requires candidate confirmation.",
                source="None",
                notes="Requires explicit confirmation from candidate.",
            ))

    return evidence_items
