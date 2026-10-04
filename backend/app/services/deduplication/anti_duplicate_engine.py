import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from app.models.job import Job, JobDuplicate
from app.services.deduplication.url_normalizer import normalize_url
from app.services.deduplication.normalizers import (
    normalize_company,
    normalize_title,
    normalize_location,
    extract_requisition_id,
)
from app.services.deduplication.confidence_model import (
    evaluate_job_pair,
    DuplicateEvaluationResult,
)
from app.services.deduplication.canonical_selector import select_canonical_record

logger = logging.getLogger(__name__)


def job_to_eval_dict(job: Job) -> Dict[str, Any]:
    """Extract standard evaluation dictionary from Job model."""
    return {
        "id": job.id,
        "title": job.title or "",
        "company": job.company or "",
        "location": job.location or "",
        "work_mode": job.work_mode or "",
        "description": job.description or "",
        "requirements": job.requirements or "",
        "responsibilities": job.responsibilities or "",
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency or "USD",
        "application_url": job.application_url or "",
        "canonical_url": job.canonical_url or normalize_url(job.application_url),
        "source": job.source or "",
        "external_job_id": job.external_job_id or "",
        "raw_payload": job.raw_payload or "",
        "discovered_at": job.discovered_at,
        "created_at": job.created_at,
    }


class AntiDuplicateEngine:
    """
    Production Anti-Duplicate Engine:
    - Layered Identity Signals (Canonical URL -> Requisition ID -> Company+Title+Location -> Description)
    - Contradiction Checks preventing unsafe false positives
    - Candidate Blocking (Indexed DB lookups avoiding O(N^2) full-table scans)
    - Deterministic Canonical Record Selection
    - Full Traceability preserving raw source records and occurrence history
    """

    @staticmethod
    def get_blocking_candidates(
        db: Session,
        job: Job,
        max_candidates: int = 30,
    ) -> List[Job]:
        """
        Retrieves a small, targeted candidate set of plausible duplicates
        using indexed database lookups to strictly avoid O(N^2) table scans.
        """
        norm_url = job.canonical_url or normalize_url(job.application_url)
        comp_norm = normalize_company(job.company)
        
        # Build list of filter predicates
        predicates = []

        # 1. Exact canonical URL match
        if norm_url:
            predicates.append(Job.canonical_url == norm_url)
            predicates.append(Job.application_url == job.application_url)

        # 2. Requisition ID match in raw_payload or external_job_id
        req_id = extract_requisition_id(
            raw_payload=job.raw_payload,
            external_id=job.external_job_id,
            url=job.application_url,
            text=job.description,
        )
        if req_id and len(req_id) >= 4:
            predicates.append(Job.external_job_id == req_id)
            predicates.append(Job.raw_payload.ilike(f"%{req_id}%"))

        # 3. Company match (exact or core token)
        if comp_norm:
            # First 2 significant words of company name
            comp_tokens = comp_norm.split()
            if comp_tokens:
                main_token = comp_tokens[0]
                if len(main_token) >= 3:
                    predicates.append(Job.company.ilike(f"%{main_token}%"))

        if not predicates:
            return []

        # Query only candidates matching one of the blocking predicates
        query = db.query(Job).filter(
            Job.id != job.id,
            or_(*predicates)
        )

        candidates = query.limit(max_candidates).all()
        return candidates

    @staticmethod
    def evaluate_and_link(
        db: Session,
        job: Job,
        auto_commit: bool = False,
    ) -> Optional[JobDuplicate]:
        """
        Evaluates an ingested job against stored candidates and executes
        canonical linking or flags possible duplicates.
        """
        # Ensure canonical_url is computed and stored
        if not job.canonical_url and job.application_url:
            job.canonical_url = normalize_url(job.application_url)

        # 1. Candidate blocking (avoids full-table scan)
        candidates = AntiDuplicateEngine.get_blocking_candidates(db, job)
        if not candidates:
            # No plausible candidates: job is standalone canonical
            job.is_canonical = True
            job.duplicate_status = "canonical"
            job.canonical_job_id = None
            if auto_commit:
                db.commit()
            return None

        job_dict = job_to_eval_dict(job)
        best_match: Optional[Tuple[Job, DuplicateEvaluationResult]] = None

        # 2. Evaluate pairwise similarity against small candidate set
        for candidate in candidates:
            cand_dict = job_to_eval_dict(candidate)
            res = evaluate_job_pair(job_dict, cand_dict)

            if res.confidence in ("VERY_HIGH", "HIGH", "MEDIUM"):
                if not best_match or res.confidence_score > best_match[1].confidence_score:
                    best_match = (candidate, res)

        if not best_match:
            job.is_canonical = True
            job.duplicate_status = "canonical"
            job.canonical_job_id = None
            if auto_commit:
                db.commit()
            return None

        matched_candidate, eval_result = best_match

        # 3. Handle VERY_HIGH or HIGH duplicate match (Auto-merge)
        if eval_result.should_merge:
            # Determine which job is canonical using deterministic selection rules
            canonical_rec, duplicate_rec = select_canonical_record(matched_candidate, job)

            # Link duplicate to canonical
            duplicate_rec.is_canonical = False
            duplicate_rec.duplicate_status = "duplicate"
            duplicate_rec.duplicate_confidence = eval_result.confidence
            duplicate_rec.canonical_job_id = canonical_rec.id

            canonical_rec.is_canonical = True
            canonical_rec.duplicate_status = "canonical"

            # Check if JobDuplicate record already exists
            dup_link = db.query(JobDuplicate).filter(
                JobDuplicate.canonical_job_id == canonical_rec.id,
                JobDuplicate.duplicate_job_id == duplicate_rec.id,
            ).first()

            if not dup_link:
                dup_link = JobDuplicate(
                    canonical_job_id=canonical_rec.id,
                    duplicate_job_id=duplicate_rec.id,
                    confidence=eval_result.confidence,
                    confidence_score=eval_result.confidence_score,
                    match_method=eval_result.match_method,
                    status="auto_merged",
                    evidence=json.dumps({
                        "matched_signals": eval_result.matched_signals,
                        "contradictions": eval_result.contradictions,
                        "similarity_metrics": eval_result.similarity_metrics,
                        "evidence": eval_result.evidence,
                    }),
                )
                db.add(dup_link)
            else:
                dup_link.confidence = eval_result.confidence
                dup_link.confidence_score = eval_result.confidence_score
                dup_link.match_method = eval_result.match_method
                dup_link.status = "auto_merged"
                dup_link.evidence = json.dumps({
                    "matched_signals": eval_result.matched_signals,
                    "contradictions": eval_result.contradictions,
                    "similarity_metrics": eval_result.similarity_metrics,
                    "evidence": eval_result.evidence,
                })
                dup_link.updated_at = datetime.now(timezone.utc)

            logger.info(
                f"[AntiDuplicate] AUTO-MERGED: Job {duplicate_rec.id} ({duplicate_rec.source}) "
                f"linked as duplicate to Canonical {canonical_rec.id} ({canonical_rec.source}). "
                f"Confidence={eval_result.confidence} ({eval_result.confidence_score}), "
                f"Method={eval_result.match_method}"
            )

            if auto_commit:
                db.commit()
            return dup_link

        # 4. Handle MEDIUM confidence match (Possible Duplicate - DO NOT AUTO MERGE)
        elif eval_result.confidence == "MEDIUM":
            job.is_canonical = True  # Remains visible as its own job
            job.duplicate_status = "possible_duplicate"
            job.duplicate_confidence = "MEDIUM"
            job.canonical_job_id = matched_candidate.id

            dup_link = db.query(JobDuplicate).filter(
                JobDuplicate.canonical_job_id == matched_candidate.id,
                JobDuplicate.duplicate_job_id == job.id,
            ).first()

            if not dup_link:
                dup_link = JobDuplicate(
                    canonical_job_id=matched_candidate.id,
                    duplicate_job_id=job.id,
                    confidence=eval_result.confidence,
                    confidence_score=eval_result.confidence_score,
                    match_method=eval_result.match_method,
                    status="possible_duplicate",
                    evidence=json.dumps({
                        "matched_signals": eval_result.matched_signals,
                        "contradictions": eval_result.contradictions,
                        "similarity_metrics": eval_result.similarity_metrics,
                        "evidence": eval_result.evidence,
                    }),
                )
                db.add(dup_link)

            logger.info(
                f"[AntiDuplicate] POSSIBLE DUPLICATE: Job {job.id} flagged against {matched_candidate.id} "
                f"with Confidence=MEDIUM ({eval_result.confidence_score}). Kept separate for review."
            )

            if auto_commit:
                db.commit()
            return dup_link

        # 5. Low or No Match -> Standalone Canonical
        job.is_canonical = True
        job.duplicate_status = "canonical"
        job.canonical_job_id = None
        if auto_commit:
            db.commit()
        return None

    @classmethod
    def get_source_occurrences(cls, db: Session, job_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all source occurrences for a given job.
        If the job is a duplicate, finds its canonical and all sibling duplicates.
        If the job is canonical, finds all duplicate records linked to it.
        """
        target_job = db.query(Job).filter(Job.id == job_id).first()
        if not target_job:
            return []

        canonical_id = target_job.canonical_job_id if (not target_job.is_canonical and target_job.canonical_job_id) else target_job.id
        canonical_job = db.query(Job).filter(Job.id == canonical_id).first()
        if not canonical_job:
            canonical_job = target_job

        # Find all duplicate jobs linked to canonical
        duplicate_jobs = db.query(Job).filter(
            Job.canonical_job_id == canonical_job.id,
            Job.duplicate_status == "duplicate",
        ).all()

        occurrences = []

        # 1. Canonical job itself
        occurrences.append({
            "job_id": canonical_job.id,
            "source": canonical_job.source,
            "external_job_id": canonical_job.external_job_id,
            "application_url": canonical_job.application_url,
            "canonical_url": canonical_job.canonical_url,
            "discovered_at": canonical_job.discovered_at,
            "last_seen_at": canonical_job.last_seen_at,
            "is_canonical": True,
            "duplicate_status": canonical_job.duplicate_status,
            "duplicate_confidence": None,
        })

        # 2. Linked duplicates
        for dj in duplicate_jobs:
            if dj.id == canonical_job.id:
                continue
            occurrences.append({
                "job_id": dj.id,
                "source": dj.source,
                "external_job_id": dj.external_job_id,
                "application_url": dj.application_url,
                "canonical_url": dj.canonical_url,
                "discovered_at": dj.discovered_at,
                "last_seen_at": dj.last_seen_at,
                "is_canonical": False,
                "duplicate_status": dj.duplicate_status,
                "duplicate_confidence": dj.duplicate_confidence,
            })

        return occurrences
