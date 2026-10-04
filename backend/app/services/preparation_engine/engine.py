from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from fastapi import HTTPException, status

from app.models.job import Job
from app.models.profile import CandidateProfile
from app.models.matching import MatchResult
from app.models.decision import ApplicationDecision
from app.models.application import Application, ApplicationEvent
from app.models.preparation import ApplicationPreparation

from app.services.matching_service import get_default_candidate, calculate_or_get_job_match
from app.services.decision_engine.engine import ApplicationDecisionEngine
from app.services.preparation_engine.requirement_extractor import extract_application_requirements
from app.services.preparation_engine.evidence_mapper import map_candidate_evidence
from app.services.preparation_engine.content_generator import (
    generate_resume_recommendation,
    generate_skills_recommendation,
    generate_deterministic_content,
)
from app.services.preparation_engine.question_answering import generate_application_questions
from app.services.preparation_engine.readiness_assessor import assess_application_readiness
from app.core.logging import logger

PREPARATION_ENGINE_VERSION = "1.0.0"


class ApplicationPreparationEngine:
    """
    Step 8 Master Application Preparation Engine.
    Coordinates requirement extraction, evidence mapping, claim safety,
    deterministic content generation, question answering, and readiness assessment.
    """

    @classmethod
    def prepare_application_for_job(
        cls,
        db: Session,
        job_id: str,
        candidate_id: Optional[str] = None,
        application_id: Optional[str] = None,
        force_regenerate: bool = False,
        allow_skip: bool = False,
        user_overrides: Optional[Dict[str, Any]] = None,
        user_notes: Optional[str] = None,
    ) -> ApplicationPreparation:
        """
        Prepares everything required to submit a strong application for a job.
        Strict Boundary: Preparation only. Never auto-submits.
        APPLY and REVIEW jobs can be prepared.
        SKIP jobs cannot be prepared by default (raises 400).
        """
        # 1. Validate Job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID '{job_id}' not found."
            )

        # 2. Get Candidate Profile
        candidate = get_default_candidate(db, candidate_id)

        # 3. Obtain or Re-use Match & Decision
        match_result, _ = calculate_or_get_job_match(db, job.id, candidate.id)
        decision, _ = ApplicationDecisionEngine.evaluate_and_persist(db, job.id, candidate.id)

        # 4. Eligibility Check: APPLY and REVIEW jobs proceed; SKIP jobs are blocked by default
        if decision.decision == "SKIP" and not allow_skip:
            reason = decision.reasons[0] if decision.reasons else "Disqualified by Application Decision Engine."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot prepare application for job with decision 'SKIP'. Reason: {reason}. Only APPLY and REVIEW jobs can be prepared.",
            )

        # 5. Check or Create Application Record
        app_record: Optional[Application] = None
        if application_id:
            app_record = db.query(Application).filter(Application.id == application_id).first()
            if not app_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Application with ID '{application_id}' not found."
                )
        else:
            # Check if an application already exists for this job and candidate
            app_record = db.query(Application).filter(
                and_(
                    Application.job_id == job.id,
                    Application.candidate_id == candidate.id,
                )
            ).first()

        now = datetime.now(timezone.utc)

        if not app_record:
            app_record = Application(
                job_id=job.id,
                candidate_id=candidate.id,
                status="preparation",
                source=job.source,
                application_url=job.application_url,
                resume_used="Harsh_Resume.pdf",
                notes=f"Prepared application package for {job.title} at {job.company}",
            )
            db.add(app_record)
            db.flush()

            # Add audit event
            start_event = ApplicationEvent(
                application_id=app_record.id,
                event_type="preparation_started",
                description=f"Step 8 preparation started for {job.title} at {job.company}",
                event_metadata={"decision": decision.decision, "version": 1},
            )
            db.add(start_event)
            db.flush()

        # 6. Check Existing Preparation Record
        existing_prep = db.query(ApplicationPreparation).filter(
            and_(
                ApplicationPreparation.job_id == job.id,
                ApplicationPreparation.candidate_id == candidate.id,
            )
        ).first()

        # If existing exists and not forced, return cached package (merging user overrides if given)
        if existing_prep and not force_regenerate:
            if user_overrides or user_notes is not None:
                if user_overrides:
                    merged = dict(existing_prep.user_overrides or {})
                    merged.update(user_overrides)
                    existing_prep.user_overrides = merged
                if user_notes is not None:
                    existing_prep.user_notes = user_notes
                existing_prep.updated_at = now
                db.commit()
                db.refresh(existing_prep)
            return existing_prep

        # 7. Execute Preparation Engine Pipeline
        # A. Requirement Extraction
        extracted_reqs = extract_application_requirements(job)

        # B. Candidate Evidence Mapping
        evidence_items = map_candidate_evidence(candidate, job, extracted_reqs)

        # C. Skills Recommendation
        skills_rec = generate_skills_recommendation(candidate, job, extracted_reqs)

        # D. Resume Recommendation
        resume_rec = generate_resume_recommendation(candidate, job, extracted_reqs, match_result)

        # E. Deterministic Content Generation
        gen_content = generate_deterministic_content(candidate, job, extracted_reqs, skills_rec)

        # F. Application Questions & Proposed Answers
        question_answers = generate_application_questions(
            candidate=candidate,
            job=job,
            extracted_reqs=extracted_reqs,
            user_overrides=user_overrides or (existing_prep.user_overrides if existing_prep else None),
        )

        # G. Readiness Assessment
        readiness_status, readiness_score, readiness_reasons, confirmations_required, warnings = assess_application_readiness(
            evidence_items=evidence_items,
            questions=question_answers,
            extracted_reqs=extracted_reqs,
            decision=decision,
            match_result=match_result,
        )

        # Construct Snapshots
        job_snapshot = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "source": job.source,
            "application_url": job.application_url,
            "location": job.location,
            "work_mode": job.work_mode,
            "salary_min": float(job.salary_min) if job.salary_min is not None else None,
            "salary_max": float(job.salary_max) if job.salary_max is not None else None,
            "currency": job.currency,
            "is_canonical": job.is_canonical,
        }

        decision_snapshot = {
            "decision": decision.decision,
            "confidence_score": decision.confidence_score,
            "risk_level": decision.risk_level,
            "match_score": match_result.overall_score if match_result else None,
            "fit_category": match_result.fit_category if match_result else None,
            "role_relevance": match_result.dimension_details.get("role_fit") if match_result and match_result.dimension_details else {},
            "hard_requirement_status": match_result.hard_requirement_status if match_result else "PASSED",
            "primary_reason": decision.reasons[0] if decision.reasons else None,
        }

        # 8. Persistence (Create or Version-Increment Existing)
        if existing_prep:
            # Increment version to prevent uncontrolled duplicates
            new_version = existing_prep.version + 1
            existing_prep.application_id = app_record.id
            existing_prep.version = new_version
            existing_prep.readiness_status = readiness_status
            existing_prep.readiness_score = readiness_score
            existing_prep.readiness_reasons = readiness_reasons
            existing_prep.job_snapshot = job_snapshot
            existing_prep.decision_snapshot = decision_snapshot
            existing_prep.resume_recommendation = resume_rec.to_dict()
            existing_prep.extracted_requirements = extracted_reqs.to_dict()
            existing_prep.evidence_mapping = [item.to_dict() for item in evidence_items]
            existing_prep.skills_recommendation = skills_rec.to_dict()
            existing_prep.generated_content = gen_content.to_dict()
            existing_prep.question_answers = [qa.to_dict() for qa in question_answers]
            existing_prep.warnings = warnings
            existing_prep.human_confirmation_required = confirmations_required
            if user_overrides:
                merged = dict(existing_prep.user_overrides or {})
                merged.update(user_overrides)
                existing_prep.user_overrides = merged
            if user_notes is not None:
                existing_prep.user_notes = user_notes
            existing_prep.engine_version = PREPARATION_ENGINE_VERSION
            existing_prep.prepared_at = now
            existing_prep.updated_at = now

            # Log regeneration audit event
            regen_event = ApplicationEvent(
                application_id=app_record.id,
                event_type="preparation_regenerated",
                description=f"Step 8 preparation package regenerated (v{new_version})",
                event_metadata={"version": new_version, "readiness_status": readiness_status, "readiness_score": readiness_score},
            )
            db.add(regen_event)
            db.commit()
            db.refresh(existing_prep)
            return existing_prep
        else:
            new_prep = ApplicationPreparation(
                application_id=app_record.id,
                job_id=job.id,
                candidate_id=candidate.id,
                version=1,
                readiness_status=readiness_status,
                readiness_score=readiness_score,
                readiness_reasons=readiness_reasons,
                job_snapshot=job_snapshot,
                decision_snapshot=decision_snapshot,
                resume_recommendation=resume_rec.to_dict(),
                extracted_requirements=extracted_reqs.to_dict(),
                evidence_mapping=[item.to_dict() for item in evidence_items],
                skills_recommendation=skills_rec.to_dict(),
                generated_content=gen_content.to_dict(),
                question_answers=[qa.to_dict() for qa in question_answers],
                warnings=warnings,
                human_confirmation_required=confirmations_required,
                user_overrides=user_overrides or {},
                user_notes=user_notes,
                engine_version=PREPARATION_ENGINE_VERSION,
                prepared_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(new_prep)

            # Log completion audit event
            comp_event = ApplicationEvent(
                application_id=app_record.id,
                event_type="preparation_completed",
                description=f"Step 8 preparation package created (v1: {readiness_status})",
                event_metadata={"version": 1, "readiness_status": readiness_status, "readiness_score": readiness_score},
            )
            db.add(comp_event)
            db.commit()
            db.refresh(new_prep)
            return new_prep

    @classmethod
    def get_preparation_for_job(
        cls,
        db: Session,
        job_id: str,
        candidate_id: Optional[str] = None,
    ) -> Optional[ApplicationPreparation]:
        """Fetches existing preparation record for job and candidate."""
        candidate = get_default_candidate(db, candidate_id)
        return db.query(ApplicationPreparation).filter(
            and_(
                ApplicationPreparation.job_id == job_id,
                ApplicationPreparation.candidate_id == candidate.id,
            )
        ).first()

    @classmethod
    def get_preparation_by_application_id(
        cls,
        db: Session,
        application_id: str,
    ) -> Optional[ApplicationPreparation]:
        """Fetches existing preparation record linked to application_id."""
        return db.query(ApplicationPreparation).filter(
            ApplicationPreparation.application_id == application_id
        ).first()

    @classmethod
    def update_user_overrides(
        cls,
        db: Session,
        job_id: str,
        user_overrides: Dict[str, Any],
        user_notes: Optional[str] = None,
        candidate_id: Optional[str] = None,
    ) -> ApplicationPreparation:
        """
        Updates human-confirmed information or user notes on a prepared package.
        Re-evaluates question answers and readiness with updated confirmations.
        """
        prep = cls.get_preparation_for_job(db, job_id, candidate_id)
        if not prep:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preparation package for job ID '{job_id}' not found. Run preparation first."
            )

        merged = dict(prep.user_overrides or {})
        merged.update(user_overrides)
        prep.user_overrides = merged

        if user_notes is not None:
            prep.user_notes = user_notes

        # Re-apply confirmed answers to question_answers list
        updated_qas = []
        for qa in (prep.question_answers or []):
            cat = qa.get("category")
            if cat in merged:
                qa["confirmed_answer"] = merged[cat]
            updated_qas.append(qa)
        prep.question_answers = updated_qas

        # Re-assess remaining confirmations
        rem_confirmations = []
        for qa in updated_qas:
            if qa.get("requires_human_confirmation") and not qa.get("confirmed_answer"):
                rem_confirmations.append({
                    "question": qa.get("question"),
                    "category": qa.get("category"),
                    "proposed_answer": qa.get("proposed_answer"),
                    "reason": qa.get("evidence"),
                })
        prep.human_confirmation_required = rem_confirmations

        # If all confirmations are cleared and status was READY_WITH_REVIEW, upgrade to READY
        if len(rem_confirmations) == 0 and prep.readiness_status == "READY_WITH_REVIEW":
            prep.readiness_status = "READY"
            prep.readiness_score = min(100.0, prep.readiness_score + 15.0)
            prep.readiness_reasons = ["All pending items confirmed by candidate. Package ready for submission."]

        prep.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(prep)
        return prep
