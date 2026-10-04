from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.job import Job
from app.models.profile import CandidateProfile
from app.models.matching import MatchResult
from app.models.decision import ApplicationDecision
from app.services.matching_service import get_default_candidate, calculate_or_get_job_match
from app.services.decision_engine.evaluator import evaluate_application_decision
from app.core.logging import logger

DECISION_ENGINE_VERSION = "1.1.0"


class ApplicationDecisionEngine:
    """
    Step 7 Master Application Decision Engine.
    Coordinates match retrieval, multi-dimensional rule evaluation, and persistence.
    """

    @staticmethod
    def is_decision_stale(decision: ApplicationDecision, job: Job, candidate: CandidateProfile) -> bool:
        """Determines if a cached decision needs recomputation."""
        if decision.engine_version != DECISION_ENGINE_VERSION:
            return True

        decided_at = decision.decided_at
        if decided_at.tzinfo is None:
            decided_at = decided_at.replace(tzinfo=timezone.utc)

        job_updated = job.updated_at
        if job_updated and job_updated.tzinfo is None:
            job_updated = job_updated.replace(tzinfo=timezone.utc)
        if job_updated and job_updated > decided_at:
            return True

        cand_updated = candidate.updated_at
        if cand_updated and cand_updated.tzinfo is None:
            cand_updated = cand_updated.replace(tzinfo=timezone.utc)
        if cand_updated and cand_updated > decided_at:
            return True

        return False

    @classmethod
    def evaluate_and_persist(
        cls,
        db: Session,
        job_id: str,
        candidate_id: Optional[str] = None,
        force: bool = False,
    ) -> Tuple[ApplicationDecision, bool]:
        """
        Evaluates a job and persists or updates its ApplicationDecision.
        Returns (ApplicationDecision, was_reused: bool).
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job with ID '{job_id}' not found.")

        candidate = get_default_candidate(db, candidate_id)

        # Check existing decision
        existing_decision = db.query(ApplicationDecision).filter(
            and_(
                ApplicationDecision.job_id == job.id,
                ApplicationDecision.candidate_id == candidate.id,
            )
        ).first()

        if existing_decision and not force and not cls.is_decision_stale(existing_decision, job, candidate):
            return existing_decision, True

        # Ensure a MatchResult exists (reuses cached match if available)
        match_result, _ = calculate_or_get_job_match(
            db=db,
            job_id=job.id,
            candidate_id=candidate.id,
            force_recompute=force,
        )

        # Run multi-dimensional evaluation
        eval_result = evaluate_application_decision(
            job=job,
            candidate=candidate,
            match_result=match_result,
            db=db,
        )

        now = datetime.now(timezone.utc)

        if existing_decision:
            existing_decision.decision = eval_result.decision
            existing_decision.confidence_score = eval_result.confidence_score
            existing_decision.risk_level = eval_result.risk_level
            existing_decision.reasons = eval_result.reasons
            existing_decision.supporting_factors = eval_result.supporting_factors
            existing_decision.disqualifying_factors = eval_result.disqualifying_factors
            existing_decision.review_reasons = eval_result.review_reasons
            existing_decision.evaluation_metadata = eval_result.metadata
            existing_decision.engine_version = DECISION_ENGINE_VERSION
            existing_decision.decided_at = now
            existing_decision.updated_at = now
            db.commit()
            db.refresh(existing_decision)
            return existing_decision, False
        else:
            new_decision = ApplicationDecision(
                job_id=job.id,
                candidate_id=candidate.id,
                decision=eval_result.decision,
                confidence_score=eval_result.confidence_score,
                risk_level=eval_result.risk_level,
                reasons=eval_result.reasons,
                supporting_factors=eval_result.supporting_factors,
                disqualifying_factors=eval_result.disqualifying_factors,
                review_reasons=eval_result.review_reasons,
                evaluation_metadata=eval_result.metadata,
                engine_version=DECISION_ENGINE_VERSION,
                decided_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(new_decision)
            db.commit()
            db.refresh(new_decision)
            return new_decision, False

    @classmethod
    def get_decision_for_job(
        cls,
        db: Session,
        job_id: str,
        candidate_id: Optional[str] = None,
    ) -> Optional[ApplicationDecision]:
        """Retrieves existing decision for a job and candidate."""
        candidate = get_default_candidate(db, candidate_id)
        return db.query(ApplicationDecision).filter(
            and_(
                ApplicationDecision.job_id == job_id,
                ApplicationDecision.candidate_id == candidate.id,
            )
        ).first()

    @classmethod
    def bulk_evaluate(
        cls,
        db: Session,
        limit: int = 50,
        force: bool = False,
        candidate_id: Optional[str] = None,
        only_canonical: bool = True,
    ) -> Dict[str, Any]:
        """
        Bulk processes decisions across stored jobs.
        """
        candidate = get_default_candidate(db, candidate_id)
        query = db.query(Job)
        if only_canonical:
            query = query.filter(Job.is_canonical == True)

        jobs = query.order_by(desc(Job.discovered_at)).limit(limit).all()

        processed = 0
        reused = 0
        new_or_updated = 0
        apply_count = 0
        review_count = 0
        skip_count = 0
        decisions_list: List[ApplicationDecision] = []

        for job in jobs:
            try:
                decision, was_reused = cls.evaluate_and_persist(
                    db=db,
                    job_id=job.id,
                    candidate_id=candidate.id,
                    force=force,
                )
                processed += 1
                if was_reused:
                    reused += 1
                else:
                    new_or_updated += 1

                if decision.decision == "APPLY":
                    apply_count += 1
                elif decision.decision == "REVIEW":
                    review_count += 1
                elif decision.decision == "SKIP":
                    skip_count += 1

                decisions_list.append(decision)
            except Exception as exc:
                logger.error(f"Error evaluating decision for job {job.id}: {exc}", exc_info=True)

        return {
            "processed": processed,
            "reused": reused,
            "new_or_updated": new_or_updated,
            "apply_count": apply_count,
            "review_count": review_count,
            "skip_count": skip_count,
            "items": decisions_list,
        }
