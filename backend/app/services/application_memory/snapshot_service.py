from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.profile import CandidateProfile
from app.models.job import Job
from app.models.decision import ApplicationDecision
from app.models.matching import MatchResult
from app.models.preparation import ApplicationPreparation
from app.models.execution import ApplicationExecution


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SnapshotService:
    """
    Step 10: Snapshot Service for Immutable Application Memory.
    Captures exact point-in-time state of candidate profile, job posting,
    decision intelligence, and application artifacts at application time.
    Preserves historical fidelity even when active profile or job changes later.
    """

    @staticmethod
    def capture_candidate_snapshot(candidate: CandidateProfile) -> Dict[str, Any]:
        """
        Creates an immutable snapshot of candidate profile state.
        """
        target_roles = []
        if candidate.preference_record and candidate.preference_record.target_roles:
            target_roles = list(candidate.preference_record.target_roles)
        elif candidate.preferences and "target_roles" in candidate.preferences:
            target_roles = list(candidate.preferences["target_roles"])

        educations = [
            {
                "institution": edu.institution,
                "degree": edu.degree,
                "field": edu.field,
                "start_date": edu.start_date,
                "end_date": edu.end_date,
            }
            for edu in (candidate.educations or [])
        ]

        experiences = [
            {
                "company": exp.company,
                "title": exp.title,
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "is_current": getattr(exp, "current", False),
            }
            for exp in (candidate.experiences or [])
        ]


        skills = [s.name for s in (candidate.skills or [])]

        return {
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "summary": candidate.summary,
            "target_roles": target_roles,
            "total_experience_years": 2.0,  # verified master resume boundary
            "skills": skills,
            "educations": educations,
            "experiences": experiences,
            "links": candidate.links or {},
            "captured_at": get_utc_now().isoformat(),
        }

    @staticmethod
    def capture_job_snapshot(job: Job) -> Dict[str, Any]:
        """
        Creates an immutable snapshot of job posting state.
        """
        return {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "work_mode": job.work_mode,
            "salary_min": float(job.salary_min) if job.salary_min else None,
            "salary_max": float(job.salary_max) if job.salary_max else None,
            "currency": job.currency,
            "application_url": job.application_url,
            "source": job.source,
            "requirements": job.requirements,
            "is_canonical": job.is_canonical,
            "canonical_job_id": job.canonical_job_id,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "captured_at": get_utc_now().isoformat(),
        }

    @staticmethod
    def capture_decision_snapshot(
        decision: Optional[ApplicationDecision],
        match: Optional[MatchResult] = None,
    ) -> Dict[str, Any]:
        """
        Creates an immutable snapshot of application decision evaluation.
        """
        if not decision:
            return {
                "decision": "UNKNOWN",
                "confidence_score": 0.0,
                "risk_level": "UNKNOWN",
                "reasons": ["No decision record existed at application creation."],
                "supporting_factors": [],
                "disqualifying_factors": [],
                "review_reasons": [],
                "match_score": match.overall_score if match else None,
                "engine_version": "1.0.0",
                "captured_at": get_utc_now().isoformat(),
            }

        return {
            "decision": decision.decision,
            "confidence_score": decision.confidence_score,
            "risk_level": decision.risk_level,
            "reasons": decision.reasons or [],
            "supporting_factors": decision.supporting_factors or [],
            "disqualifying_factors": decision.disqualifying_factors or [],
            "review_reasons": decision.review_reasons or [],
            "match_score": match.overall_score if match else (
                decision.evaluation_metadata.get("match_score") if decision.evaluation_metadata else None
            ),
            "engine_version": decision.engine_version,
            "captured_at": get_utc_now().isoformat(),
        }

    @staticmethod
    def capture_artifacts_snapshot(
        preparation: Optional[ApplicationPreparation],
        execution: Optional[ApplicationExecution] = None,
    ) -> Dict[str, Any]:
        """
        Creates an immutable snapshot of exact artifacts and answers used.
        """
        resume_name = "Harsh_Resume.pdf"
        resume_path = "f:\\job wala project\\Harsh_Resume.pdf"
        cover_letter = None
        application_message = None
        screening_answers = []

        if preparation:
            if preparation.resume_recommendation:
                resume_name = preparation.resume_recommendation.get("selected_resume", resume_name)
                resume_path = preparation.resume_recommendation.get("file_path", resume_path)
            
            if preparation.generated_content:
                cover_letter = preparation.generated_content.get("tailored_cover_letter")
                application_message = preparation.generated_content.get("short_application_message")

            if preparation.question_answers:
                screening_answers = preparation.question_answers

        if execution and execution.step_details:
            manual_kit = execution.step_details.get("manual_kit", {})
            if manual_kit:
                draft_materials = manual_kit.get("draft_materials", {})
                if not cover_letter:
                    cover_letter = draft_materials.get("cover_letter")
                if not application_message:
                    application_message = draft_materials.get("short_message")

        return {
            "resume_name": resume_name,
            "resume_path": resume_path,
            "resume_version": "v1.0-master",
            "cover_letter": cover_letter,
            "application_message": application_message,
            "screening_answers": screening_answers,
            "portfolio_url": "https://harsh-tripathi.github.io",
            "github_url": "https://github.com/harsh-tripathi",
            "linkedin_url": "https://linkedin.com/in/harsh-tripathi",
            "captured_at": get_utc_now().isoformat(),
        }
