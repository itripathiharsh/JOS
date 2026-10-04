import os
from typing import Dict, Any, List, Set, Optional
from app.models.profile import CandidateProfile, Document
from app.models.job import Job
from app.models.matching import MatchResult
from intelligence.candidate import extract_candidate_data
from app.services.preparation_engine.models import (
    ExtractedJobRequirements,
    ResumeRecommendation,
    SkillsRecommendation,
    GeneratedContent,
)
from app.services.preparation_engine.claim_safety import ClaimSafetyAuditor


def generate_resume_recommendation(
    candidate: CandidateProfile,
    job: Job,
    extracted_reqs: ExtractedJobRequirements,
    match_result: Optional[MatchResult] = None,
) -> ResumeRecommendation:
    """
    Evaluates candidate's documents and recommends the best matching resume
    with deterministic KEEP, EMPHASIZE, DE-EMPHASIZE, and ADD_IF_TRUE tailoring guidance.
    Master resume is never modified.
    """
    cand_data = extract_candidate_data(candidate)
    documents = candidate.documents or []
    resume_docs = [d for d in documents if d.type == "resume"]

    rec_doc = resume_docs[0] if resume_docs else None
    doc_id = rec_doc.id if rec_doc else None
    doc_name = rec_doc.name if rec_doc else "Harsh_Resume.pdf"
    file_path = rec_doc.file_path if rec_doc else "storage/documents/Harsh_Resume.pdf"

    # Match analysis
    cand_skills = {s.canonical_name for s in cand_data.skills}
    job_keywords = set(extracted_reqs.keywords)
    overlap = sorted(list(cand_skills.intersection(job_keywords)))
    missing = sorted(list(job_keywords - cand_skills))

    is_ai_role = any(t in job.title.lower() for t in ["ai", "ml", "machine learning", "data", "rag", "llm"])
    is_backend_role = any(t in job.title.lower() for t in ["backend", "back-end", "api", "python", "software engineer"])

    why_recommended = (
        f"Master Resume '{doc_name}' is the verified primary source of truth documenting ~{cand_data.actual_experience_years:.1f} "
        f"years of practical experience across {len(candidate.experiences or [])} industry roles (Sentio Mind, Banao Technologies, "
        f"Innovate, Edunet) and dual STEM degrees (B.Tech CSE and BS Data Science from IIT Madras)."
    )

    if len(missing) == 0:
        sufficiency = "Highly Sufficient: Profile and resume substantiate 100% of extracted core requirements."
    elif len(overlap) >= 3:
        sufficiency = f"Substantially Sufficient: Directly verifies {len(overlap)} core skills ({', '.join(overlap[:4])}). Minor gaps should be addressed with transferable context."
    else:
        sufficiency = f"Partially Sufficient: Good foundational alignment, but contains {len(missing)} unverified skills in the job specification."

    # KEEP
    keep_points = [
        "Verified ~2.0 practical years across Sentio Mind, Banao Technologies, Innovate, and Edunet Foundation.",
        "Dual STEM academic background: B.Tech CSE (BBDITM, 2022-2026) and BS in Data Science & Applications (IIT Madras).",
        f"Core technical competencies matching the vacancy: {', '.join(overlap[:5]) if overlap else 'Python, FastAPI, Machine Learning'}.",
    ]
    if is_ai_role:
        keep_points.append("EcoRAG Agent project: LangGraph multi-turn architecture with ChromaDB vector search and Groq Llama 3.1.")
        keep_points.append("Green Minds AI Wellness Journal: Generative AI, Firebase, Streamlit, and Groq/Gemini APIs.")
    else:
        keep_points.append("Backend engineering projects: FastAPI REST APIs, schema design, and asynchronous request handling.")

    # EMPHASIZE
    emphasize_points = []
    if is_ai_role:
        emphasize_points.append("Elevate RAG architectures, prompt engineering, and vector retrieval pipelines to the top of project section.")
        emphasize_points.append("Highlight production experience at Sentio Mind & Banao Technologies delivering generative AI integrations.")
    elif is_backend_role:
        emphasize_points.append("Emphasize Python backend architecture, FastAPI endpoints, relational database persistence, and API contract design.")
        emphasize_points.append("Highlight code quality, automated testing, and scalable server-side patterns.")
    else:
        emphasize_points.append(f"Emphasize direct transferable skills matching {job.title}: {', '.join(overlap[:4]) if overlap else 'Software Development'}.")

    # DE-EMPHASIZE
    deemphasize_points = [
        "De-emphasize generic coursework or introductory university lab assignments.",
        "Condense unrelated secondary web design or basic styling details to keep technical focus razor-sharp.",
    ]
    if is_ai_role:
        deemphasize_points.append("Reduce space allocated to generic non-AI web utilities to give prominence to LangGraph/RAG systems.")
    elif is_backend_role:
        deemphasize_points.append("Condense purely frontend/Streamlit UI details to prioritize backend service and database logic.")

    # ADD_IF_TRUE
    add_if_true_points = []
    for m in missing[:3]:
        if m in ["PostgreSQL", "MySQL", "SQL"]:
            add_if_true_points.append(f"If you have hands-on production experience with {m}, explicitly cite it under Database skills.")
        elif m in ["Docker", "Kubernetes", "CI/CD"]:
            add_if_true_points.append(f"If you have created Dockerfiles or CI/CD pipelines in your projects, add a brief mention.")
        elif m in ["AWS", "GCP", "Cloud"]:
            add_if_true_points.append(f"If you have deployed services directly to {m}, specify the cloud services utilized.")
        else:
            add_if_true_points.append(f"If you have defensible, unlisted experience with {m}, add it manually with verifiable proof.")

    return ResumeRecommendation(
        recommended_document_id=doc_id,
        document_name=doc_name,
        file_path=file_path,
        why_recommended=why_recommended,
        sufficiency_assessment=sufficiency,
        gaps_identified=[f"Job emphasizes {m}; unverified in candidate profile." for m in missing[:4]],
        keep_points=keep_points,
        emphasize_points=emphasize_points,
        deemphasize_points=deemphasize_points,
        add_if_true_points=add_if_true_points,
    )


def generate_skills_recommendation(
    candidate: CandidateProfile,
    job: Job,
    extracted_reqs: ExtractedJobRequirements,
) -> SkillsRecommendation:
    """
    Categorizes skills for the job into:
    - Strong Match: Verified and relevant
    - Supporting Skills: Verified adjacent skills
    - Missing Skills: Job asks for them but candidate lacks verified evidence
    - Do Not Claim: Crucial guardrail list of skills candidate cannot substantiate
    """
    cand_data = extract_candidate_data(candidate)
    cand_skills = {s.canonical_name for s in cand_data.skills}
    job_keywords = set(extracted_reqs.keywords)

    strong_match = sorted(list(cand_skills.intersection(job_keywords)))
    missing_skills = sorted(list(job_keywords - cand_skills))

    # Supporting skills: candidate skills relevant to this domain not in job keywords
    is_ai = any(t in job.title.lower() for t in ["ai", "ml", "learning", "data"])
    supporting_candidates = [
        "FastAPI", "Python", "RAG", "LangGraph", "LangChain", "ChromaDB",
        "Streamlit", "Firebase", "Git", "REST APIs", "Vector Search", "Gemini APIs", "Groq"
    ]
    supporting_skills = [
        s for s in supporting_candidates
        if s in cand_skills and s not in strong_match
    ][:6]

    # Do Not Claim: Missing skills from job description that are critical or specialized
    do_not_claim = [
        m for m in missing_skills
        if m in ["Golang", "Rust", "Kubernetes", "Scala", "C++", "Salesforce", "AWS Lambda", "Ruby", "PHP"]
    ]
    if not do_not_claim:
        do_not_claim = missing_skills[:4]

    return SkillsRecommendation(
        strong_match=strong_match,
        supporting_skills=supporting_skills,
        missing_skills=missing_skills,
        do_not_claim=do_not_claim,
    )


def generate_deterministic_content(
    candidate: CandidateProfile,
    job: Job,
    extracted_reqs: ExtractedJobRequirements,
    skills_rec: SkillsRecommendation,
) -> GeneratedContent:
    """
    Generates explainable, deterministic application materials:
    - Application Summary
    - Tailored Cover Letter / Short Application Message
    - Short Application Message
    - Claim Safety Audit
    """
    cand_data = extract_candidate_data(candidate)
    cand_name = candidate.name or "Harsh Vardhan Tripathi"
    cand_years = f"{cand_data.actual_experience_years:.1f}"
    top_matched_skills = ", ".join(skills_rec.strong_match[:4]) if skills_rec.strong_match else "Python, Generative AI, and Backend Architecture"

    # 1. Application Summary
    summary = (
        f"{cand_name} is an engineer with approximately {cand_years} years of practical industry and research experience "
        f"across AI development, machine learning, and backend systems. Possessing dual academic degrees (B.Tech in Computer Science "
        f"& Engineering and BS in Data Science & Applications from IIT Madras), with demonstrated experience delivering production "
        f"applications at Sentio Mind and Banao Technologies. Strong technical expertise in {top_matched_skills}, retrieval-augmented "
        f"generation (RAG) agents, and robust REST APIs."
    )

    # 2. Cover Letter
    # Build project paragraph based on relevance
    is_ai = any(t in job.title.lower() for t in ["ai", "ml", "learning", "data", "rag", "llm"])
    if is_ai:
        project_highlight = (
            "In my recent project work, I engineered the EcoRAG Agent, an environmental intelligence system utilizing LangGraph "
            "for multi-turn state-graph routing, ChromaDB for vector indexing, and Groq Llama 3.1 for high-speed inference. Additionally, "
            "at Sentio Mind and Banao Technologies, I contributed to deploying production AI pipelines and client-facing generative solutions."
        )
    else:
        project_highlight = (
            "In my development experience, I have architected and deployed backend microservices using FastAPI and modern Python tools, "
            "integrating relational persistence and cloud data pipelines. At Sentio Mind and Banao Technologies, I focused on building "
            "reliable, low-latency API contracts and end-to-end service integration."
        )

    # Gap acknowledgment paragraph if missing skills exist
    gap_note = ""
    if skills_rec.missing_skills:
        safe_missing = ", ".join(skills_rec.missing_skills[:2])
        gap_note = (
            f"While my primary practical expertise is concentrated in Python and modern AI/backend ecosystems, my strong computer "
            f"science foundations from IIT Madras and BBDITM allow me to quickly ramp up on adjacent technologies such as {safe_missing}."
        )

    cover_letter = (
        f"Dear Hiring Team at {job.company},\n\n"
        f"I am writing to express my strong interest in the {job.title} position at {job.company}. "
        f"With approximately {cand_years} years of practical engineering experience and a dual background in Computer Science "
        f"(B.Tech, BBDITM) and Data Science (BS, IIT Madras), I build resilient, data-driven software solutions.\n\n"
        f"My background aligns closely with your core requirements, specifically across {top_matched_skills}. {project_highlight}\n\n"
        f"{gap_note + chr(10) + chr(10) if gap_note else ''}"
        f"[Candidate Note: You may insert specific reasons for your interest in {job.company} and their team mission here.]\n\n"
        f"I welcome the opportunity to discuss how my technical skills and practical engineering experience can contribute "
        f"to {job.company}'s engineering goals.\n\n"
        f"Sincerely,\n"
        f"{cand_name}\n"
        f"{candidate.email or 'harsh.tripathi.cs@gmail.com'} | {candidate.phone or '+91 95652 49247'}\n"
        f"Portfolio: {candidate.links.get('portfolio', 'https://harshtripathi.vercel.app/') if candidate.links else 'https://harshtripathi.vercel.app/'}"
    )

    # 3. Short Application Message (for LinkedIn / message fields)
    short_message = (
        f"Hi {job.company} Team — I am applying for the {job.title} opening. I bring ~{cand_years} years of software & AI "
        f"engineering experience (Sentio Mind, Banao Technologies), dual degrees in CS & Data Science (IIT Madras), and verified "
        f"proficiency in {top_matched_skills}. Excited about the opportunity to contribute to your engineering team!"
    )

    # 4. Claim Safety Audit
    audit_summary = ClaimSafetyAuditor.audit_generated_text(summary, candidate)
    audit_letter = ClaimSafetyAuditor.audit_generated_text(cover_letter, candidate)
    combined_violations = list(set(audit_summary["violations"] + audit_letter["violations"]))
    combined_warnings = list(set(audit_summary["warnings"] + audit_letter["warnings"]))

    claim_audit = {
        "passed": len(combined_violations) == 0,
        "violations": combined_violations,
        "warnings": combined_warnings,
        "safety_verdict": "SAFE" if len(combined_violations) == 0 else "FLAGGED",
        "verified_years_used": cand_years,
        "verified_skills_used": top_matched_skills,
    }

    return GeneratedContent(
        application_summary=summary,
        cover_letter=cover_letter,
        short_message=short_message,
        claim_safety_audit=claim_audit,
    )
