from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.application import Application, ApplicationOverride
from app.models.job import Job
from app.models.decision import ApplicationDecision
from app.models.matching import MatchResult
from app.services.application_memory.models import LifecycleStage, RejectionCategory, ConversionMetric


class ApplicationFeedbackEngine:
    """
    Step 10: Deterministic Application Memory & Feedback Analytics Engine.
    Analyzes historical application data and provides descriptive feedback,
    conversion metrics, rejection patterns, and decision alignment observations.

    CRITICAL SAFETY BOUNDARIES:
    - Zero Machine Learning.
    - Zero automated changes to Candidate Profile, Target Roles, or Salary Floor.
    - Zero automated changes to Decision Engine, Match Weights, or Taxonomy.
    - Purely observational, descriptive, explainable feedback.
    - Zero division safety and honest sample-size indicators.
    """

    MIN_RELIABLE_SAMPLE_SIZE = 5

    @classmethod
    def get_feedback_report(cls, db: Session, candidate_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates the comprehensive feedback and memory analysis report.
        """
        query = db.query(Application)
        if candidate_id:
            query = query.filter(Application.candidate_id == candidate_id)

        applications = query.all()
        total_apps = len(applications)

        # 1. Lifecycle Overview Counts
        lifecycle_counts = cls._compute_lifecycle_counts(applications)

        # 2. Conversion Funnels with Explicit Denominators
        conversions = cls._compute_conversions(lifecycle_counts)

        # 3. Target Role Performance
        role_performance = cls._analyze_role_performance(db, applications)

        # 4. Source Performance
        source_performance = cls._analyze_source_performance(applications)

        # 5. Match Score Tier Breakdown
        match_tier_performance = cls._analyze_match_tiers(db, applications)

        # 6. Work Mode Breakdown
        work_mode_performance = cls._analyze_work_modes(db, applications)

        # 7. Resume Performance
        resume_performance = cls._analyze_resumes(applications)

        # 8. Rejection Reasons Categorization
        rejection_patterns = cls._analyze_rejections(applications)

        # 9. System Decision vs User Override Matrix
        decision_alignment = cls._analyze_decision_alignment(db, applications)

        # 10. Descriptive Observations & Suggested Improvements
        observations = cls._generate_descriptive_observations(
            total_apps=total_apps,
            conversions=conversions,
            role_performance=role_performance,
            rejection_patterns=rejection_patterns,
            decision_alignment=decision_alignment,
        )

        return {
            "total_applications": total_apps,
            "lifecycle_counts": lifecycle_counts,
            "conversions": conversions,
            "role_performance": role_performance,
            "source_performance": source_performance,
            "match_tier_performance": match_tier_performance,
            "work_mode_performance": work_mode_performance,
            "resume_performance": resume_performance,
            "rejection_patterns": rejection_patterns,
            "decision_alignment": decision_alignment,
            "observations": observations,
            "sample_size_alert": (
                f"Sample size is limited (N={total_apps}). Patterns should be treated as directional observations rather than statistical conclusions."
                if total_apps < cls.MIN_RELIABLE_SAMPLE_SIZE
                else None
            ),
        }

    @classmethod
    def _compute_lifecycle_counts(cls, applications: List[Application]) -> Dict[str, int]:
        counts = {stage.value: 0 for stage in LifecycleStage}
        for app in applications:
            stage = app.lifecycle_stage or LifecycleStage.NOT_STARTED.value
            counts[stage] = counts.get(stage, 0) + 1
        return counts

    @classmethod
    def _compute_conversions(cls, counts: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        """
        Calculates conversion rates with explicit denominators and zero-division protection.
        """
        # Submitted includes SUBMITTED, ACKNOWLEDGED, SCREENING, INTERVIEW, OFFER, ACCEPTED, REJECTED (if submitted), NO_RESPONSE
        submitted_stages = {
            LifecycleStage.SUBMITTED.value,
            LifecycleStage.ACKNOWLEDGED.value,
            LifecycleStage.SCREENING.value,
            LifecycleStage.INTERVIEW.value,
            LifecycleStage.OFFER.value,
            LifecycleStage.ACCEPTED.value,
            LifecycleStage.REJECTED.value,
            LifecycleStage.NO_RESPONSE.value,
        }
        submitted_count = sum(counts.get(s, 0) for s in submitted_stages)

        interviews_count = (
            counts.get(LifecycleStage.SCREENING.value, 0)
            + counts.get(LifecycleStage.INTERVIEW.value, 0)
            + counts.get(LifecycleStage.OFFER.value, 0)
            + counts.get(LifecycleStage.ACCEPTED.value, 0)
        )
        offers_count = counts.get(LifecycleStage.OFFER.value, 0) + counts.get(LifecycleStage.ACCEPTED.value, 0)

        # 1. Application -> Interview
        app_to_interview_rate = round((interviews_count / submitted_count) * 100, 1) if submitted_count > 0 else 0.0
        app_to_interview = {
            "numerator": interviews_count,
            "denominator": submitted_count,
            "rate": app_to_interview_rate,
            "is_statistically_significant": submitted_count >= cls.MIN_RELIABLE_SAMPLE_SIZE,
            "warning": "No submitted applications yet." if submitted_count == 0 else None,
        }

        # 2. Application -> Offer
        app_to_offer_rate = round((offers_count / submitted_count) * 100, 1) if submitted_count > 0 else 0.0
        app_to_offer = {
            "numerator": offers_count,
            "denominator": submitted_count,
            "rate": app_to_offer_rate,
            "is_statistically_significant": submitted_count >= cls.MIN_RELIABLE_SAMPLE_SIZE,
            "warning": "No submitted applications yet." if submitted_count == 0 else None,
        }

        # 3. Interview -> Offer
        interview_to_offer_rate = round((offers_count / interviews_count) * 100, 1) if interviews_count > 0 else 0.0
        interview_to_offer = {
            "numerator": offers_count,
            "denominator": interviews_count,
            "rate": interview_to_offer_rate,
            "is_statistically_significant": interviews_count >= cls.MIN_RELIABLE_SAMPLE_SIZE,
            "warning": "No interviews recorded yet." if interviews_count == 0 else None,
        }

        return {
            "application_to_interview": app_to_interview,
            "application_to_offer": app_to_offer,
            "interview_to_offer": interview_to_offer,
            "submitted_total": submitted_count,
        }

    @classmethod
    def _analyze_role_performance(cls, db: Session, applications: List[Application]) -> List[Dict[str, Any]]:
        """
        Aggregates performance by job title / target role.
        """
        role_map: Dict[str, Dict[str, int]] = {}

        for app in applications:
            title = "Unspecified Role"
            if app.job_snapshot and "title" in app.job_snapshot:
                title = app.job_snapshot["title"]
            elif app.job_id:
                job = db.query(Job).filter(Job.id == app.job_id).first()
                if job:
                    title = job.title

            if title not in role_map:
                role_map[title] = {
                    "applications": 0,
                    "interviews": 0,
                    "offers": 0,
                    "rejections": 0,
                    "no_response": 0,
                }

            role_map[title]["applications"] += 1
            stage = app.lifecycle_stage
            if stage in (LifecycleStage.SCREENING.value, LifecycleStage.INTERVIEW.value):
                role_map[title]["interviews"] += 1
            elif stage in (LifecycleStage.OFFER.value, LifecycleStage.ACCEPTED.value):
                role_map[title]["interviews"] += 1
                role_map[title]["offers"] += 1
            elif stage == LifecycleStage.REJECTED.value:
                role_map[title]["rejections"] += 1
            elif stage == LifecycleStage.NO_RESPONSE.value:
                role_map[title]["no_response"] += 1

        results = []
        for role, stats in sorted(role_map.items(), key=lambda x: x[1]["applications"], reverse=True):
            apps = stats["applications"]
            interview_rate = round((stats["interviews"] / apps) * 100, 1) if apps > 0 else 0.0
            offer_rate = round((stats["offers"] / apps) * 100, 1) if apps > 0 else 0.0
            results.append({
                "role": role,
                "applications": apps,
                "interviews": stats["interviews"],
                "offers": stats["offers"],
                "rejections": stats["rejections"],
                "no_response": stats["no_response"],
                "interview_rate": interview_rate,
                "offer_rate": offer_rate,
                "is_small_sample": apps < cls.MIN_RELIABLE_SAMPLE_SIZE,
            })
        return results

    @classmethod
    def _analyze_source_performance(cls, applications: List[Application]) -> List[Dict[str, Any]]:
        """
        Aggregates performance by ingestion source (Remotive, manual, etc.).
        """
        source_map: Dict[str, Dict[str, int]] = {}
        for app in applications:
            src = app.source or "unknown"
            if src not in source_map:
                source_map[src] = {
                    "applications": 0,
                    "interviews": 0,
                    "offers": 0,
                    "rejections": 0,
                    "no_response": 0,
                }

            source_map[src]["applications"] += 1
            stage = app.lifecycle_stage
            if stage in (LifecycleStage.SCREENING.value, LifecycleStage.INTERVIEW.value):
                source_map[src]["interviews"] += 1
            elif stage in (LifecycleStage.OFFER.value, LifecycleStage.ACCEPTED.value):
                source_map[src]["interviews"] += 1
                source_map[src]["offers"] += 1
            elif stage == LifecycleStage.REJECTED.value:
                source_map[src]["rejections"] += 1
            elif stage == LifecycleStage.NO_RESPONSE.value:
                source_map[src]["no_response"] += 1

        results = []
        for src, stats in sorted(source_map.items(), key=lambda x: x[1]["applications"], reverse=True):
            apps = stats["applications"]
            results.append({
                "source": src,
                "applications": apps,
                "interviews": stats["interviews"],
                "offers": stats["offers"],
                "rejections": stats["rejections"],
                "no_response": stats["no_response"],
                "interview_rate": round((stats["interviews"] / apps) * 100, 1) if apps > 0 else 0.0,
                "rejection_rate": round((stats["rejections"] / apps) * 100, 1) if apps > 0 else 0.0,
                "is_small_sample": apps < cls.MIN_RELIABLE_SAMPLE_SIZE,
            })
        return results

    @classmethod
    def _analyze_match_tiers(cls, db: Session, applications: List[Application]) -> List[Dict[str, Any]]:
        """
        Breaks down application outcomes across match score tiers:
        80-100, 70-79, 60-69, below 60.
        """
        tiers = {
            "80_100": {"label": "80 – 100 (High Relevance)", "apps": 0, "interviews": 0, "offers": 0, "rejections": 0},
            "70_79": {"label": "70 – 79 (Good Relevance)", "apps": 0, "interviews": 0, "offers": 0, "rejections": 0},
            "60_69": {"label": "60 – 69 (Partial Relevance)", "apps": 0, "interviews": 0, "offers": 0, "rejections": 0},
            "below_60": {"label": "Below 60 (Low Relevance)", "apps": 0, "interviews": 0, "offers": 0, "rejections": 0},
        }

        for app in applications:
            score = None
            if app.decision_snapshot and app.decision_snapshot.get("match_score") is not None:
                score = app.decision_snapshot["match_score"]
            elif app.job_id and app.candidate_id:
                match = db.query(MatchResult).filter_by(job_id=app.job_id, candidate_id=app.candidate_id).first()
                if match:
                    score = match.overall_score

            if score is None:
                continue

            tier_key = (
                "80_100" if score >= 80 else
                "70_79" if score >= 70 else
                "60_69" if score >= 60 else
                "below_60"
            )

            tiers[tier_key]["apps"] += 1
            stage = app.lifecycle_stage
            if stage in (LifecycleStage.SCREENING.value, LifecycleStage.INTERVIEW.value):
                tiers[tier_key]["interviews"] += 1
            elif stage in (LifecycleStage.OFFER.value, LifecycleStage.ACCEPTED.value):
                tiers[tier_key]["interviews"] += 1
                tiers[tier_key]["offers"] += 1
            elif stage == LifecycleStage.REJECTED.value:
                tiers[tier_key]["rejections"] += 1

        results = []
        for key, data in tiers.items():
            apps = data["apps"]
            results.append({
                "tier": key,
                "label": data["label"],
                "applications": apps,
                "interviews": data["interviews"],
                "offers": data["offers"],
                "rejections": data["rejections"],
                "interview_rate": round((data["interviews"] / apps) * 100, 1) if apps > 0 else 0.0,
            })
        return results

    @classmethod
    def _analyze_work_modes(cls, db: Session, applications: List[Application]) -> List[Dict[str, Any]]:
        mode_map: Dict[str, Dict[str, int]] = {}
        for app in applications:
            mode = "unknown"
            if app.job_snapshot and "work_mode" in app.job_snapshot:
                mode = app.job_snapshot["work_mode"] or "unknown"
            elif app.job_id:
                job = db.query(Job).filter(Job.id == app.job_id).first()
                if job:
                    mode = job.work_mode or "unknown"

            if mode not in mode_map:
                mode_map[mode] = {"applications": 0, "interviews": 0, "offers": 0}
            mode_map[mode]["applications"] += 1
            if app.lifecycle_stage in (LifecycleStage.SCREENING.value, LifecycleStage.INTERVIEW.value):
                mode_map[mode]["interviews"] += 1
            elif app.lifecycle_stage in (LifecycleStage.OFFER.value, LifecycleStage.ACCEPTED.value):
                mode_map[mode]["interviews"] += 1
                mode_map[mode]["offers"] += 1

        results = []
        for mode, stats in mode_map.items():
            apps = stats["applications"]
            results.append({
                "work_mode": mode,
                "applications": apps,
                "interviews": stats["interviews"],
                "offers": stats["offers"],
                "interview_rate": round((stats["interviews"] / apps) * 100, 1) if apps > 0 else 0.0,
            })
        return results

    @classmethod
    def _analyze_resumes(cls, applications: List[Application]) -> List[Dict[str, Any]]:
        resume_map: Dict[str, Dict[str, int]] = {}
        for app in applications:
            r_name = app.resume_used or "Harsh_Resume.pdf"
            if app.artifacts_snapshot and "resume_name" in app.artifacts_snapshot:
                r_name = app.artifacts_snapshot["resume_name"] or r_name

            if r_name not in resume_map:
                resume_map[r_name] = {"applications": 0, "interviews": 0, "offers": 0, "rejections": 0}

            resume_map[r_name]["applications"] += 1
            stage = app.lifecycle_stage
            if stage in (LifecycleStage.SCREENING.value, LifecycleStage.INTERVIEW.value):
                resume_map[r_name]["interviews"] += 1
            elif stage in (LifecycleStage.OFFER.value, LifecycleStage.ACCEPTED.value):
                resume_map[r_name]["interviews"] += 1
                resume_map[r_name]["offers"] += 1
            elif stage == LifecycleStage.REJECTED.value:
                resume_map[r_name]["rejections"] += 1

        results = []
        for r_name, stats in resume_map.items():
            apps = stats["applications"]
            results.append({
                "resume_name": r_name,
                "applications": apps,
                "interviews": stats["interviews"],
                "offers": stats["offers"],
                "rejections": stats["rejections"],
                "interview_rate": round((stats["interviews"] / apps) * 100, 1) if apps > 0 else 0.0,
                "note": "Correlational metric only. Does not assert direct causation.",
            })
        return results

    @classmethod
    def _analyze_rejections(cls, applications: List[Application]) -> Dict[str, Any]:
        """
        Categorizes rejection patterns without inventing reasons.
        """
        rejection_counts: Dict[str, int] = {cat.value: 0 for cat in RejectionCategory}
        total_rejections = 0
        samples_by_category: Dict[str, List[str]] = {cat.value: [] for cat in RejectionCategory}

        for app in applications:
            if app.lifecycle_stage == LifecycleStage.REJECTED.value:
                total_rejections += 1
                cat = app.rejection_category or RejectionCategory.UNKNOWN.value
                rejection_counts[cat] = rejection_counts.get(cat, 0) + 1
                if app.rejection_reason and len(samples_by_category[cat]) < 3:
                    samples_by_category[cat].append(app.rejection_reason)

        breakdown = []
        for cat, count in rejection_counts.items():
            if count > 0:
                pct = round((count / total_rejections) * 100, 1) if total_rejections > 0 else 0.0
                breakdown.append({
                    "category": cat,
                    "count": count,
                    "percentage": pct,
                    "sample_reasons": samples_by_category.get(cat, []),
                })

        breakdown.sort(key=lambda x: x["count"], reverse=True)

        return {
            "total_rejections": total_rejections,
            "breakdown": breakdown,
        }

    @classmethod
    def _analyze_decision_alignment(cls, db: Session, applications: List[Application]) -> Dict[str, Any]:
        """
        Compares System Decision vs User Overrides vs Final Outcome.
        """
        alignment_matrix: Dict[str, Dict[str, int]] = {
            "APPLY_followed": {"total": 0, "interviews": 0, "offers": 0, "rejections": 0},
            "REVIEW_approved": {"total": 0, "interviews": 0, "offers": 0, "rejections": 0},
            "SKIP_overridden_to_APPLY": {"total": 0, "interviews": 0, "offers": 0, "rejections": 0},
            "REVIEW_overridden_to_SKIP": {"total": 0, "interviews": 0, "offers": 0, "rejections": 0},
        }

        overrides = db.query(ApplicationOverride).all()
        overridden_app_ids = {ov.application_id: ov for ov in overrides}

        for app in applications:
            orig_dec = "REVIEW"
            if app.decision_snapshot and "decision" in app.decision_snapshot:
                orig_dec = app.decision_snapshot["decision"]

            is_overridden = app.id in overridden_app_ids
            ov = overridden_app_ids.get(app.id)

            group_key = None
            if not is_overridden:
                if orig_dec == "APPLY":
                    group_key = "APPLY_followed"
                elif orig_dec == "REVIEW":
                    group_key = "REVIEW_approved"
            else:
                if orig_dec == "SKIP" and ov.override_decision == "APPLY":
                    group_key = "SKIP_overridden_to_APPLY"
                elif orig_dec == "REVIEW" and ov.override_decision == "SKIP":
                    group_key = "REVIEW_overridden_to_SKIP"

            if group_key and group_key in alignment_matrix:
                alignment_matrix[group_key]["total"] += 1
                stage = app.lifecycle_stage
                if stage in (LifecycleStage.SCREENING.value, LifecycleStage.INTERVIEW.value):
                    alignment_matrix[group_key]["interviews"] += 1
                elif stage in (LifecycleStage.OFFER.value, LifecycleStage.ACCEPTED.value):
                    alignment_matrix[group_key]["interviews"] += 1
                    alignment_matrix[group_key]["offers"] += 1
                elif stage == LifecycleStage.REJECTED.value:
                    alignment_matrix[group_key]["rejections"] += 1

        return {
            "matrix": alignment_matrix,
            "total_overrides_recorded": len(overrides),
        }

    @classmethod
    def _generate_descriptive_observations(
        cls,
        total_apps: int,
        conversions: Dict[str, Any],
        role_performance: List[Dict[str, Any]],
        rejection_patterns: Dict[str, Any],
        decision_alignment: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        Produces purely descriptive observations with honesty safeguards.
        NEVER outputs commands to alter scoring weights or profile fields.
        """
        observations = []

        if total_apps == 0:
            observations.append({
                "type": "INFO",
                "message": "No applications tracked yet. Start preparing and submitting applications to build your career feedback loop.",
            })
            return observations

        if total_apps < cls.MIN_RELIABLE_SAMPLE_SIZE:
            observations.append({
                "type": "CAUTION",
                "message": f"Sample size is limited (N={total_apps}). Statistical conclusions require more application data.",
            })

        # Role observation
        if role_performance:
            top_role = role_performance[0]
            if top_role["applications"] >= 2:
                observations.append({
                    "type": "OBSERVATION",
                    "message": f"Highest application volume is in '{top_role['role']}' roles ({top_role['applications']} applications, {top_role['interview_rate']}% interview rate).",
                })

        # Rejection pattern observation
        breakdown = rejection_patterns.get("breakdown", [])
        if breakdown:
            top_rejection = breakdown[0]
            if top_rejection["category"] != RejectionCategory.UNKNOWN.value:
                observations.append({
                    "type": "OBSERVATION",
                    "message": f"Most frequent identified rejection category is '{top_rejection['category'].replace('_', ' ')}' ({top_rejection['count']} occurrences, {top_rejection['percentage']}% of rejections).",
                })

        # Decision vs override observation
        skip_to_apply = decision_alignment.get("matrix", {}).get("SKIP_overridden_to_APPLY", {})
        if skip_to_apply.get("total", 0) > 0:
            observations.append({
                "type": "OBSERVATION",
                "message": f"User overrode SKIP to APPLY on {skip_to_apply['total']} jobs, yielding {skip_to_apply['interviews']} interviews and {skip_to_apply['rejections']} rejections.",
            })

        # Conversion summary
        submitted_total = conversions.get("submitted_total", 0)
        if submitted_total > 0:
            int_rate = conversions.get("application_to_interview", {}).get("rate", 0.0)
            observations.append({
                "type": "SUMMARY",
                "message": f"Application-to-interview conversion is currently {int_rate}% across {submitted_total} submitted applications.",
            })

        return observations
