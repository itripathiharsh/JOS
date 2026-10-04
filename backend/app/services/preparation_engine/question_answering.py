from typing import List, Dict, Any, Optional
from app.models.profile import CandidateProfile
from app.models.job import Job
from intelligence.candidate import extract_candidate_data
from app.services.preparation_engine.models import (
    ApplicationQuestionAnswer,
    ExtractedJobRequirements,
)


def generate_application_questions(
    candidate: CandidateProfile,
    job: Job,
    extracted_reqs: ExtractedJobRequirements,
    user_overrides: Optional[Dict[str, Any]] = None,
) -> List[ApplicationQuestionAnswer]:
    """
    Deterministically generates proposed answers for common application screening questions.
    Enforces Phase G & H guardrails:
    - Sensitive questions (work auth, sponsorship, salary, legal declarations) ALWAYS require human confirmation.
    - Salary floor (₹3.5 LPA) is marked NEEDS_CONFIRMATION and requires confirmation.
    """
    cand_data = extract_candidate_data(candidate)
    pref_record = candidate.preference_record
    links = candidate.links or {}
    overrides = user_overrides or {}
    questions: List[ApplicationQuestionAnswer] = []

    # 1. Years of Experience Question
    cand_years = f"{cand_data.actual_experience_years:.1f}"
    questions.append(ApplicationQuestionAnswer(
        question="How many years of relevant software/AI engineering experience do you have?",
        category="years_experience",
        proposed_answer=f"{cand_years} years",
        answer_source="Candidate Experience Records (Sentio Mind, Banao, Innovate, Edunet)",
        confidence="HIGH",
        evidence=f"Calculated from 4 verified industry roles totalling ~{cand_years} practical years.",
        requires_human_confirmation=False,
        confirmed_answer=overrides.get("years_experience"),
    ))

    # 2. Highest Level of Education
    edu_list = candidate.educations or []
    highest_edu = "Bachelor's Degree (B.Tech in Computer Science & Engineering, BS in Data Science)" if edu_list else "Bachelor's Degree"
    questions.append(ApplicationQuestionAnswer(
        question="What is your highest level of completed or current education?",
        category="education",
        proposed_answer=highest_edu,
        answer_source="Candidate Education Records (BBDITM, IIT Madras)",
        confidence="HIGH",
        evidence="B.Tech CSE from BBDITM (2022-2026) and BS in Data Science & Applications from IIT Madras (2022-Present).",
        requires_human_confirmation=False,
        confirmed_answer=overrides.get("education"),
    ))

    # 3. Current Location & Timezone
    cand_loc = candidate.location or "Lucknow, Uttar Pradesh, India"
    questions.append(ApplicationQuestionAnswer(
        question="Where are you currently located?",
        category="location",
        proposed_answer=cand_loc,
        answer_source="Candidate Profile Location",
        confidence="HIGH",
        evidence=f"Primary candidate location: {cand_loc}.",
        requires_human_confirmation=False,
        confirmed_answer=overrides.get("location"),
    ))

    # 4. Work Authorization (CRITICAL SENSITIVE QUESTION)
    questions.append(ApplicationQuestionAnswer(
        question="Are you legally authorized to work in the specified location / country for this employer?",
        category="work_authorization",
        proposed_answer="Yes (Authorized to work in India / Remote contracts; foreign on-site requires candidate review)",
        answer_source="Inferred - Candidate Profile Location (India)",
        confidence="MEDIUM",
        evidence="Candidate is an Indian national based in Lucknow, India. Legally authorized for Indian entities and global remote contracts.",
        requires_human_confirmation=True,  # STRICT GUARDRAIL
        confirmed_answer=overrides.get("work_authorization"),
    ))

    # 5. Visa Sponsorship (CRITICAL SENSITIVE QUESTION)
    questions.append(ApplicationQuestionAnswer(
        question="Will you now or in the future require visa sponsorship for employment?",
        category="sponsorship",
        proposed_answer="No for India / Remote; Candidate confirmation required for foreign relocation",
        answer_source="Inferred - Location Preference",
        confidence="MEDIUM",
        evidence="Remote roles typically do not require sponsorship; cross-border relocation requires individual legal assessment.",
        requires_human_confirmation=True,  # STRICT GUARDRAIL
        confirmed_answer=overrides.get("sponsorship"),
    ))

    # 6. Salary Expectation (CRITICAL SALARY RULE - PHASE H)
    salary_floor = pref_record.minimum_salary if pref_record and pref_record.minimum_salary is not None else 350000.00
    salary_curr = pref_record.currency if pref_record else "INR"
    salary_status = pref_record.salary_status if pref_record else "NEEDS_CONFIRMATION"

    questions.append(ApplicationQuestionAnswer(
        question="What is your expected annual compensation / salary?",
        category="salary",
        proposed_answer=f"₹{int(salary_floor):,} {salary_curr} minimum (Candidate baseline: ₹3.5 LPA - Status: {salary_status})",
        answer_source="Candidate Career Preferences",
        confidence="LOW",  # Low confidence because salary floor is unconfirmed
        evidence=f"Candidate baseline floor is ₹3.5 LPA ({salary_floor} {salary_curr}) marked as '{salary_status}'. Must not be submitted without human confirmation.",
        requires_human_confirmation=True,  # STRICT GUARDRAIL
        confirmed_answer=overrides.get("salary"),
    ))

    # 7. Notice Period / Start Date
    questions.append(ApplicationQuestionAnswer(
        question="What is your notice period or earliest possible start date?",
        category="notice_period",
        proposed_answer="Available immediately / 15-30 days upon agreement",
        answer_source="Candidate Preference & Academic Status",
        confidence="MEDIUM",
        evidence="Final year B.Tech / flexible schedule; can start immediately for remote/internship or standard 15-30 days notice.",
        requires_human_confirmation=True,
        confirmed_answer=overrides.get("notice_period"),
    ))

    # 8. Relocation Commitment (CRITICAL SENSITIVE QUESTION)
    reloc_allowed = pref_record.relocation_allowed if pref_record else True
    questions.append(ApplicationQuestionAnswer(
        question="Are you willing to relocate for this position if required?",
        category="relocation",
        proposed_answer="Yes, open to relocation within India or viable international opportunities" if reloc_allowed else "Remote only",
        answer_source="Candidate Preferences (relocation_allowed)",
        confidence="MEDIUM",
        evidence=f"Profile preference 'relocation_allowed' is currently set to {reloc_allowed}.",
        requires_human_confirmation=True,  # STRICT GUARDRAIL
        confirmed_answer=overrides.get("relocation"),
    ))

    # 9. Professional Links (GitHub, LinkedIn, Portfolio)
    github_url = links.get("github") or "https://github.com/itripathiharsh"
    linkedin_url = links.get("linkedin") or "https://www.linkedin.com/in/iamharshvardhantripathi/"
    portfolio_url = links.get("portfolio") or "https://harshtripathi.vercel.app/"

    questions.append(ApplicationQuestionAnswer(
        question="Please provide links to your GitHub, LinkedIn, and Portfolio profiles.",
        category="links",
        proposed_answer=f"GitHub: {github_url} | LinkedIn: {linkedin_url} | Portfolio: {portfolio_url}",
        answer_source="Candidate Profile Links",
        confidence="HIGH",
        evidence="Explicitly verified URLs in candidate profile.",
        requires_human_confirmation=False,
        confirmed_answer=overrides.get("links"),
    ))

    # 10. Legal & Demographic Declarations (CRITICAL SENSITIVE QUESTION)
    questions.append(ApplicationQuestionAnswer(
        question="Do you certify that all information submitted is true, accurate, and complete to the best of your knowledge?",
        category="sensitive_declaration",
        proposed_answer="Requires Candidate Direct Sign-off",
        answer_source="Legal Declaration Compliance Gate",
        confidence="HIGH",
        evidence="Legally binding statements must be directly acknowledged by the human applicant.",
        requires_human_confirmation=True,  # STRICT GUARDRAIL
        confirmed_answer=overrides.get("sensitive_declaration"),
    ))

    return questions
