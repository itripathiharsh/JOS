from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc

from app.models.job import Job, SourceStatus
from app.models.matching import MatchResult
from app.models.decision import ApplicationDecision
from app.models.preparation import ApplicationPreparation
from app.models.execution import ApplicationExecution
from app.models.application import Application, ApplicationEvent, ApplicationNote, ApplicationOverride
from app.models.profile import CandidateProfile
from app.models.automation import AutomationTask, AutomationSettings
from app.services.profile_service import get_default_profile, calculate_profile_completeness
from app.services.application_memory.models import LifecycleStage
from app.services.application_memory.feedback_engine import ApplicationFeedbackEngine
from app.schemas.dashboard_os import (
    DashboardHealthKPIs,
    AttentionQueueItem,
    DashboardFunnel,
    DashboardFunnelStep,
    PipelineStageCount,
    MatchQualityDistribution,
    TopOpportunityItem,
    SourceHealthItem,
    ProfileHealthSummary,
    RecentActivityItem,
    FeedbackSummaryKPIs,
    AutomationTelemetrySummary,
    JobOperatingSystemResponse,
)


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DashboardOperatingSystemService:
    """
    Step 11: Job Operating System Aggregation & Telemetry Service.
    Acts as the single source of truth for the entire application lifecycle,
    discovery pipeline, match intelligence, execution state, and application memory.
    """

    @classmethod
    def get_dashboard_data(
        cls,
        db: Session,
        target_role: Optional[str] = None,
        work_mode: Optional[str] = None,
        source: Optional[str] = None,
        candidate_id: Optional[str] = None,
    ) -> JobOperatingSystemResponse:
        if candidate_id:
            candidate = db.query(CandidateProfile).filter(CandidateProfile.id == candidate_id).first()
        else:
            candidate = (
                db.query(CandidateProfile)
                .order_by(CandidateProfile.updated_at.desc(), CandidateProfile.created_at.desc())
                .first()
            )
        cand_id = candidate.id if candidate else None

        # 1. Base Job Queries with Filters
        job_query = db.query(Job)
        if work_mode:
            job_query = job_query.filter(Job.work_mode.ilike(f"%{work_mode}%"))
        if source:
            job_query = job_query.filter(Job.source == source)
        if target_role:
            job_query = job_query.filter(Job.title.ilike(f"%{target_role}%"))

        total_discovered = job_query.count()
        canonical_jobs_count = job_query.filter(Job.is_canonical.is_(True)).count()

        # 2. Match Quality Distribution
        match_query = db.query(MatchResult.fit_category, func.count(MatchResult.id)).group_by(MatchResult.fit_category)
        if candidate_id:
            match_query = match_query.filter(MatchResult.candidate_id == candidate_id)
        match_cat_counts = dict(match_query.all())

        high_relevance_count = match_cat_counts.get("HIGH_RELEVANCE", 0)
        good_relevance_count = match_cat_counts.get("GOOD_RELEVANCE", 0)
        partial_relevance_count = match_cat_counts.get("PARTIAL_RELEVANCE", 0)
        low_relevance_count = match_cat_counts.get("LOW_RELEVANCE", 0)
        insufficient_data_count = match_cat_counts.get("INSUFFICIENT_DATA", 0)

        hard_mismatch_query = db.query(func.count(MatchResult.id)).filter(
            or_(
                MatchResult.has_hard_mismatch.is_(True),
                MatchResult.hard_requirement_status.in_(["FAILED", "FAIL", "false"]),
            )
        )
        if candidate_id:
            hard_mismatch_query = hard_mismatch_query.filter(MatchResult.candidate_id == candidate_id)
        hard_mismatches_count = hard_mismatch_query.scalar() or 0

        match_quality = MatchQualityDistribution(
            high_relevance=high_relevance_count,
            good_relevance=good_relevance_count,
            partial_relevance=partial_relevance_count,
            low_relevance=low_relevance_count,
            hard_mismatches=hard_mismatches_count,
            insufficient_data=insufficient_data_count,
        )

        # 3. Application Lifecycle Stage Counts
        app_query = db.query(Application.lifecycle_stage, func.count(Application.id)).group_by(Application.lifecycle_stage)
        if candidate_id:
            app_query = app_query.filter(Application.candidate_id == candidate_id)
        raw_stage_counts = dict(app_query.all())

        # Stage metadata mapping
        stage_meta = {
            LifecycleStage.NOT_STARTED.value: {"label": "Not Started", "is_terminal": False, "is_positive": False, "is_active": False},
            LifecycleStage.PREPARED.value: {"label": "Prepared", "is_terminal": False, "is_positive": False, "is_active": True},
            LifecycleStage.IN_PROGRESS.value: {"label": "In Progress", "is_terminal": False, "is_positive": False, "is_active": True},
            LifecycleStage.AWAITING_USER.value: {"label": "Awaiting User", "is_terminal": False, "is_positive": False, "is_active": True},
            LifecycleStage.SUBMITTED.value: {"label": "Submitted", "is_terminal": False, "is_positive": False, "is_active": True},
            LifecycleStage.ACKNOWLEDGED.value: {"label": "Acknowledged", "is_terminal": False, "is_positive": False, "is_active": True},
            LifecycleStage.SCREENING.value: {"label": "Screening", "is_terminal": False, "is_positive": True, "is_active": True},
            LifecycleStage.INTERVIEW.value: {"label": "Interview", "is_terminal": False, "is_positive": True, "is_active": True},
            LifecycleStage.OFFER.value: {"label": "Offer", "is_terminal": True, "is_positive": True, "is_active": False},
            LifecycleStage.ACCEPTED.value: {"label": "Accepted", "is_terminal": True, "is_positive": True, "is_active": False},
            LifecycleStage.REJECTED.value: {"label": "Rejected", "is_terminal": True, "is_positive": False, "is_active": False},
            LifecycleStage.WITHDRAWN.value: {"label": "Withdrawn", "is_terminal": True, "is_positive": False, "is_active": False},
            LifecycleStage.EXPIRED.value: {"label": "Expired", "is_terminal": True, "is_positive": False, "is_active": False},
            LifecycleStage.NO_RESPONSE.value: {"label": "No Response", "is_terminal": True, "is_positive": False, "is_active": False},
        }

        pipeline_stages: List[PipelineStageCount] = []
        for stage in LifecycleStage:
            meta = stage_meta.get(stage.value, {"label": stage.value, "is_terminal": False, "is_positive": False, "is_active": False})
            count = raw_stage_counts.get(stage.value, 0)
            pipeline_stages.append(
                PipelineStageCount(
                    stage=stage.value,
                    label=meta["label"],
                    count=count,
                    is_terminal=meta["is_terminal"],
                    is_positive=meta["is_positive"],
                    is_active=meta["is_active"],
                )
            )

        # 4. Computed Lifecycle Totals
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
        total_submitted = sum(raw_stage_counts.get(s, 0) for s in submitted_stages)
        active_interviews = raw_stage_counts.get(LifecycleStage.SCREENING.value, 0) + raw_stage_counts.get(LifecycleStage.INTERVIEW.value, 0)
        offers_received = raw_stage_counts.get(LifecycleStage.OFFER.value, 0) + raw_stage_counts.get(LifecycleStage.ACCEPTED.value, 0)
        awaiting_response = raw_stage_counts.get(LifecycleStage.SUBMITTED.value, 0) + raw_stage_counts.get(LifecycleStage.ACKNOWLEDGED.value, 0)

        # 5. Ready to Apply & Review Required Calculations
        # Ready to apply: Decision = APPLY, Preparation is READY or READY_WITH_REVIEW, not submitted yet
        ready_to_apply_query = (
            db.query(func.count(Job.id))
            .join(ApplicationDecision, ApplicationDecision.job_id == Job.id)
            .join(ApplicationPreparation, ApplicationPreparation.job_id == Job.id)
            .outerjoin(Application, Application.job_id == Job.id)
            .filter(
                ApplicationDecision.decision == "APPLY",
                ApplicationPreparation.readiness_status.in_(["READY", "READY_WITH_REVIEW"]),
                or_(
                    Application.id.is_(None),
                    Application.lifecycle_stage.in_(["NOT_STARTED", "PREPARED"]),
                ),
            )
        )
        ready_to_apply_count = ready_to_apply_query.scalar() or 0

        # Review Required: Decision = REVIEW or Preparation = BLOCKED or Execution = INTERACTION_BLOCKED
        review_decision_count = (
            db.query(func.count(ApplicationDecision.id))
            .filter(ApplicationDecision.decision == "REVIEW")
            .scalar() or 0
        )
        prep_blocked_count = (
            db.query(func.count(ApplicationPreparation.id))
            .filter(ApplicationPreparation.readiness_status == "BLOCKED")
            .scalar() or 0
        )
        exec_blocked_count = (
            db.query(func.count(ApplicationExecution.id))
            .filter(ApplicationExecution.status == "INTERACTION_BLOCKED")
            .scalar() or 0
        )
        review_required_count = review_decision_count + prep_blocked_count + exec_blocked_count

        health_kpis = DashboardHealthKPIs(
            jobs_discovered=total_discovered,
            canonical_jobs=canonical_jobs_count,
            high_relevance_jobs=high_relevance_count,
            ready_to_apply=ready_to_apply_count,
            review_required=review_required_count,
            applications_submitted=total_submitted,
            active_interviews=active_interviews,
            offers_received=offers_received,
            awaiting_response=awaiting_response,
        )

        # 6. Action Queue (Prioritized Action Items for Today)
        action_queue = cls._build_action_queue(db, candidate)

        # 7. Job Search Funnel with Exact Numbers
        funnel = cls._build_funnel(
            db=db,
            total_discovered=total_discovered,
            canonical_jobs=canonical_jobs_count,
            high_relevance=high_relevance_count,
            good_relevance=good_relevance_count,
            partial_relevance=partial_relevance_count,
            total_submitted=total_submitted,
            active_interviews=active_interviews,
            offers_received=offers_received,
            candidate_id=candidate_id,
        )

        # 8. Curated Top Opportunities
        top_opportunities = cls._get_top_opportunities(db, candidate_id, limit=6)

        # 9. Source Health
        source_health = cls._get_source_health(db)

        # 10. Profile Health & Completeness
        profile_health = cls._get_profile_health(candidate)

        # 11. Recent Activity Feed
        recent_activity = cls._get_recent_activity(db, limit=15)

        # 12. Feedback Summary (Reusing ApplicationFeedbackEngine)
        feedback_summary = cls._get_feedback_summary(db, candidate_id)

        # 13. Step 12 Automation Telemetry
        auto_settings = None
        if candidate:
            auto_settings = db.query(AutomationSettings).filter(AutomationSettings.candidate_id == candidate.id).first()
        mode_val = auto_settings.mode if auto_settings else "ASSISTED"

        pending_t = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == "PENDING").scalar() or 0
        running_t = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == "RUNNING").scalar() or 0
        failed_t = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == "FAILED").scalar() or 0
        blocked_t = db.query(func.count(AutomationTask.id)).filter(AutomationTask.status == "BLOCKED").scalar() or 0

        last_t_run = (
            db.query(AutomationTask.completed_at)
            .filter(AutomationTask.status == "SUCCEEDED")
            .order_by(AutomationTask.completed_at.desc())
            .first()
        )
        auto_telemetry = AutomationTelemetrySummary(
            mode=mode_val,
            is_active=mode_val != "MANUAL",
            pending_tasks=pending_t,
            running_tasks=running_t,
            failed_tasks=failed_t,
            blocked_tasks=blocked_t,
            last_run=last_t_run[0] if last_t_run else None,
        )

        return JobOperatingSystemResponse(
            health_kpis=health_kpis,
            action_queue=action_queue,
            funnel=funnel,
            pipeline=pipeline_stages,
            match_quality=match_quality,
            top_opportunities=top_opportunities,
            source_health=source_health,
            profile_health=profile_health,
            recent_activity=recent_activity,
            feedback_summary=feedback_summary,
            automation_telemetry=auto_telemetry,
            generated_at=get_utc_now(),
        )

    @classmethod
    def _build_action_queue(cls, db: Session, candidate: Optional[CandidateProfile]) -> List[AttentionQueueItem]:
        items: List[AttentionQueueItem] = []

        # 1. High Priority: Execution ready to submit (human approval gate)
        ready_submits = (
            db.query(ApplicationExecution, Application, Job)
            .join(Application, Application.id == ApplicationExecution.application_id)
            .join(Job, Job.id == Application.job_id)
            .filter(ApplicationExecution.status == "READY_TO_SUBMIT")
            .limit(5)
            .all()
        )
        for exec_rec, app_rec, job_rec in ready_submits:
            items.append(
                AttentionQueueItem(
                    id=f"exec-approve-{exec_rec.id}",
                    priority="HIGH",
                    category="APPROVAL",
                    title=f"Approval Required: {job_rec.title} @ {job_rec.company}",
                    description="Application execution is completed and waiting for your final review and explicit approval to submit.",
                    job_id=job_rec.id,
                    application_id=app_rec.id,
                    action_label="Review & Approve",
                    action_target="applications",
                    action_type="open_execution",
                    metadata={"attempt": exec_rec.attempt_number, "mode": getattr(exec_rec, "mode", "MANUAL")},
                    created_at=exec_rec.updated_at,
                )
            )

        # 2. High Priority: Execution blocked (e.g. CAPTCHA, login, missing info)
        blocked_execs = (
            db.query(ApplicationExecution, Application, Job)
            .join(Application, Application.id == ApplicationExecution.application_id)
            .join(Job, Job.id == Application.job_id)
            .filter(ApplicationExecution.status.in_(["INTERACTION_BLOCKED", "BLOCKED"]))
            .limit(5)
            .all()
        )
        for exec_rec, app_rec, job_rec in blocked_execs:
            reason = getattr(exec_rec, "blocker_reason", None) or getattr(exec_rec, "failure_reason", None) or "Human intervention required (CAPTCHA, Login, or Form Question)."
            items.append(
                AttentionQueueItem(
                    id=f"exec-blocked-{exec_rec.id}",
                    priority="HIGH",
                    category="BLOCKED",
                    title=f"Execution Blocked: {job_rec.title} @ {job_rec.company}",
                    description=f"Action blocked: {reason}",
                    job_id=job_rec.id,
                    application_id=app_rec.id,
                    action_label="Inspect & Resume",
                    action_target="applications",
                    action_type="open_execution",
                    metadata={"reason": reason},
                    created_at=exec_rec.updated_at,
                )
            )

        # 2b. High Priority: Automation Worker Blocked Tasks (e.g. CAPTCHA, login, approval required)
        blocked_auto_tasks = (
            db.query(AutomationTask)
            .filter(AutomationTask.status == "BLOCKED")
            .limit(5)
            .all()
        )
        for b_task in blocked_auto_tasks:
            items.append(
                AttentionQueueItem(
                    id=f"auto-blocked-{b_task.id}",
                    priority="HIGH",
                    category="BLOCKED",
                    title=f"Automation Blocked: {b_task.task_type}",
                    description=b_task.last_error or "Background automation halted at safety gate. Manual review required.",
                    job_id=b_task.job_id,
                    application_id=b_task.application_id,
                    action_label="Inspect Task",
                    action_target="applications" if b_task.application_id else "jobs",
                    action_type="open_execution" if b_task.application_id else "open_job",
                    metadata={"error_category": b_task.error_category},
                    created_at=b_task.updated_at,
                )
            )

        # 3. High/Medium Priority: Preparation Blocked (e.g. salary floor or claim safety)
        blocked_preps = (
            db.query(ApplicationPreparation, Job)
            .join(Job, Job.id == ApplicationPreparation.job_id)
            .filter(ApplicationPreparation.readiness_status == "BLOCKED")
            .limit(5)
            .all()
        )
        for prep_rec, job_rec in blocked_preps:
            warnings_list = prep_rec.warnings or []
            warning_msg = warnings_list[0] if warnings_list else "Preparation package requires manual override or claim confirmation."
            items.append(
                AttentionQueueItem(
                    id=f"prep-blocked-{prep_rec.id}",
                    priority="HIGH" if "salary" in warning_msg.lower() else "MEDIUM",
                    category="PREPARATION",
                    title=f"Preparation Blocked: {job_rec.title} @ {job_rec.company}",
                    description=warning_msg,
                    job_id=job_rec.id,
                    application_id=prep_rec.application_id,
                    action_label="Review Preparation",
                    action_target="jobs",
                    action_type="open_preparation",
                    metadata={"warnings_count": len(warnings_list)},
                    created_at=prep_rec.created_at,
                )
            )

        # 4. Medium Priority: Jobs with Decision = REVIEW
        review_decisions = (
            db.query(ApplicationDecision, Job)
            .join(Job, Job.id == ApplicationDecision.job_id)
            .filter(ApplicationDecision.decision == "REVIEW")
            .order_by(Job.created_at.desc())
            .limit(5)
            .all()
        )
        for dec_rec, job_rec in review_decisions:
            reasons = dec_rec.review_reasons or dec_rec.reasons or ["Role requires candidate evaluation."]
            items.append(
                AttentionQueueItem(
                    id=f"decision-review-{dec_rec.id}",
                    priority="MEDIUM",
                    category="DECISION",
                    title=f"Review Candidate Fit: {job_rec.title} @ {job_rec.company}",
                    description=reasons[0] if reasons else "Job flagged for human decision.",
                    job_id=job_rec.id,
                    action_label="Inspect Decision",
                    action_target="jobs",
                    action_type="open_job",
                    metadata={"confidence": dec_rec.confidence_score, "risk": dec_rec.risk_level},
                    created_at=dec_rec.created_at,
                )
            )

        # 5. Medium Priority: Ready to Apply (APPLY + READY, not submitted)
        ready_apply_jobs = (
            db.query(Job, ApplicationDecision, ApplicationPreparation)
            .join(ApplicationDecision, ApplicationDecision.job_id == Job.id)
            .join(ApplicationPreparation, ApplicationPreparation.job_id == Job.id)
            .outerjoin(Application, Application.job_id == Job.id)
            .filter(
                ApplicationDecision.decision == "APPLY",
                ApplicationPreparation.readiness_status.in_(["READY", "READY_WITH_REVIEW"]),
                or_(
                    Application.id.is_(None),
                    Application.lifecycle_stage.in_(["NOT_STARTED", "PREPARED"]),
                ),
            )
            .limit(5)
            .all()
        )
        for job_rec, dec_rec, prep_rec in ready_apply_jobs:
            items.append(
                AttentionQueueItem(
                    id=f"ready-apply-{job_rec.id}",
                    priority="MEDIUM",
                    category="APPROVAL",
                    title=f"Ready to Apply: {job_rec.title} @ {job_rec.company}",
                    description=f"Match score: {dec_rec.confidence_score*100:.0f}%. Package is prepared and ready for submission.",
                    job_id=job_rec.id,
                    application_id=prep_rec.application_id,
                    action_label="Launch Execution",
                    action_target="jobs",
                    action_type="open_execution",
                    metadata={"prep_status": prep_rec.readiness_status},
                    created_at=job_rec.created_at,
                )
            )

        # 6. Medium Priority: Follow Up recommended (> 7 days since submission, no update)
        seven_days_ago = get_utc_now() - timedelta(days=7)
        stale_applications = (
            db.query(Application, Job)
            .join(Job, Job.id == Application.job_id)
            .filter(
                Application.lifecycle_stage.in_(["SUBMITTED", "ACKNOWLEDGED"]),
                Application.updated_at <= seven_days_ago,
            )
            .limit(5)
            .all()
        )
        for app_rec, job_rec in stale_applications:
            days_ago = (get_utc_now() - app_rec.updated_at).days
            items.append(
                AttentionQueueItem(
                    id=f"follow-up-{app_rec.id}",
                    priority="MEDIUM",
                    category="FOLLOW_UP",
                    title=f"Follow Up Recommended: {job_rec.title} @ {job_rec.company}",
                    description=f"Submitted {days_ago} days ago without response. Consider reaching out or checking portal status.",
                    job_id=job_rec.id,
                    application_id=app_rec.id,
                    action_label="View Application",
                    action_target="applications",
                    action_type="open_memory",
                    metadata={"days_since_submission": days_ago},
                    created_at=app_rec.updated_at,
                )
            )

        # 7. Info: Active Interview / Screening
        interview_apps = (
            db.query(Application, Job)
            .join(Job, Job.id == Application.job_id)
            .filter(Application.lifecycle_stage.in_(["SCREENING", "INTERVIEW"]))
            .limit(3)
            .all()
        )
        for app_rec, job_rec in interview_apps:
            items.append(
                AttentionQueueItem(
                    id=f"interview-active-{app_rec.id}",
                    priority="INFO",
                    category="INTERVIEW",
                    title=f"Active Stage: {app_rec.lifecycle_stage} @ {job_rec.company}",
                    description=f"Position: {job_rec.title}. Log notes and debrief insights after your call.",
                    job_id=job_rec.id,
                    application_id=app_rec.id,
                    action_label="Open Memory & Notes",
                    action_target="applications",
                    action_type="open_memory",
                    metadata={"stage": app_rec.lifecycle_stage},
                    created_at=app_rec.updated_at,
                )
            )

        # 8. Info: Profile incomplete
        if candidate:
            completeness = calculate_profile_completeness(candidate)
            if completeness.score < 80:
                missing = completeness.missing_required[:2]
                items.append(
                    AttentionQueueItem(
                        id="profile-incomplete-warning",
                        priority="INFO",
                        category="PROFILE",
                        title=f"Profile Health: {completeness.score}% Completeness",
                        description=f"Strengthen application packages by completing: {', '.join(missing) if missing else 'missing profile details'}.",
                        action_label="Update Profile",
                        action_target="profile",
                        action_type="open_profile",
                        metadata={"score": completeness.score},
                        created_at=candidate.updated_at,
                    )
                )

        return items

    @classmethod
    def _build_funnel(
        cls,
        db: Session,
        total_discovered: int,
        canonical_jobs: int,
        high_relevance: int,
        good_relevance: int,
        partial_relevance: int,
        total_submitted: int,
        active_interviews: int,
        offers_received: int,
        candidate_id: Optional[str] = None,
    ) -> DashboardFunnel:
        career_aligned = high_relevance + good_relevance + partial_relevance

        # Count jobs with decision APPLY or REVIEW
        decided_query = db.query(func.count(ApplicationDecision.id)).filter(
            ApplicationDecision.decision.in_(["APPLY", "REVIEW"])
        )
        if candidate_id:
            decided_query = decided_query.filter(ApplicationDecision.candidate_id == candidate_id)
        decided_apply_review = decided_query.scalar() or 0

        # Count prepared packages
        prep_query = db.query(func.count(ApplicationPreparation.id))
        if candidate_id:
            prep_query = prep_query.filter(ApplicationPreparation.candidate_id == candidate_id)
        prepared_count = prep_query.scalar() or 0

        # Construct steps with zero-division safe conversions
        counts_sequence = [
            ("discovered", "Jobs Discovered", total_discovered),
            ("canonical", "Unique Canonical Jobs", canonical_jobs),
            ("career_aligned", "Career-Aligned Jobs", career_aligned),
            ("decided", "APPLY / REVIEW Decided", decided_apply_review),
            ("prepared", "Packages Prepared", prepared_count),
            ("submitted", "Applications Submitted", total_submitted),
            ("interviews", "Interviews & Screenings", active_interviews),
            ("offers", "Offers Received", offers_received),
        ]

        steps: List[DashboardFunnelStep] = []
        for i, (stage, label, count) in enumerate(counts_sequence):
            conv = None
            if i > 0:
                prev_count = counts_sequence[i - 1][2]
                conv = round((count / prev_count) * 100, 1) if prev_count > 0 else 0.0
            steps.append(DashboardFunnelStep(stage=stage, label=label, count=count, conversion_from_prev=conv))

        return DashboardFunnel(
            discovered=total_discovered,
            unique_canonical=canonical_jobs,
            career_aligned=career_aligned,
            decided_apply_review=decided_apply_review,
            prepared=prepared_count,
            submitted=total_submitted,
            interviews=active_interviews,
            offers=offers_received,
            steps=steps,
        )

    @classmethod
    def _get_top_opportunities(cls, db: Session, candidate_id: Optional[str], limit: int = 6) -> List[TopOpportunityItem]:
        query = (
            db.query(Job, MatchResult, ApplicationDecision, ApplicationPreparation, ApplicationExecution, Application)
            .outerjoin(MatchResult, and_(MatchResult.job_id == Job.id, MatchResult.candidate_id == candidate_id))
            .outerjoin(ApplicationDecision, and_(ApplicationDecision.job_id == Job.id, ApplicationDecision.candidate_id == candidate_id))
            .outerjoin(ApplicationPreparation, and_(ApplicationPreparation.job_id == Job.id, ApplicationPreparation.candidate_id == candidate_id))
            .outerjoin(Application, and_(Application.job_id == Job.id, Application.candidate_id == candidate_id))
            .outerjoin(ApplicationExecution, ApplicationExecution.application_id == Application.id)
            .filter(Job.is_canonical.is_(True))
            .order_by(
                desc(MatchResult.overall_score),
                desc(Job.posted_at),
                desc(Job.created_at),
            )
            .limit(limit)
        )

        records = query.all()
        results: List[TopOpportunityItem] = []

        for job_rec, match_rec, dec_rec, prep_rec, exec_rec, app_rec in records:
            salary_str = None
            if job_rec.salary_min or job_rec.salary_max:
                cur = job_rec.currency or "USD"
                if job_rec.salary_min and job_rec.salary_max:
                    salary_str = f"{cur} {int(job_rec.salary_min):,} - {int(job_rec.salary_max):,}"
                elif job_rec.salary_min:
                    salary_str = f"From {cur} {int(job_rec.salary_min):,}"
                elif job_rec.salary_max:
                    salary_str = f"Up to {cur} {int(job_rec.salary_max):,}"

            results.append(
                TopOpportunityItem(
                    id=job_rec.id,
                    title=job_rec.title,
                    company=job_rec.company,
                    source=job_rec.source,
                    location=job_rec.location,
                    work_mode=job_rec.work_mode,
                    salary_display=salary_str,
                    match_score=float(match_rec.overall_score) if match_rec and match_rec.overall_score is not None else None,
                    fit_category=match_rec.fit_category if match_rec else None,
                    decision=dec_rec.decision if dec_rec else None,
                    decision_reasons=dec_rec.reasons if dec_rec and dec_rec.reasons else [],
                    hard_requirement_status="PASS" if match_rec and match_rec.hard_requirement_status else ("FAIL" if match_rec and match_rec.hard_requirement_status is False else "UNKNOWN"),
                    is_canonical=job_rec.is_canonical,
                    application_id=app_rec.id if app_rec else None,
                    preparation_status=prep_rec.readiness_status if prep_rec else None,
                    execution_status=exec_rec.status if exec_rec else None,
                    posted_at=job_rec.posted_at,
                )
            )

        return results

    @classmethod
    def _get_source_health(cls, db: Session) -> List[SourceHealthItem]:
        statuses = db.query(SourceStatus).all()
        if not statuses:
            # Fallback for default connectors if table is empty
            return [
                SourceHealthItem(
                    source="remotive",
                    status="active",
                    last_checked=get_utc_now(),
                    last_success=get_utc_now(),
                    jobs_fetched=0,
                    jobs_created=0,
                    jobs_updated=0,
                ),
                SourceHealthItem(
                    source="manual",
                    status="active",
                    last_checked=get_utc_now(),
                    last_success=get_utc_now(),
                    jobs_fetched=0,
                    jobs_created=0,
                    jobs_updated=0,
                ),
            ]

        return [
            SourceHealthItem(
                source=s.source,
                status=s.status,
                last_checked=s.last_checked,
                last_success=s.last_success,
                jobs_fetched=s.jobs_fetched,
                jobs_created=s.jobs_created,
                jobs_updated=s.jobs_updated,
                error_message=s.error_message,
            )
            for s in statuses
        ]

    @classmethod
    def _get_profile_health(cls, candidate: Optional[CandidateProfile]) -> ProfileHealthSummary:
        if not candidate:
            return ProfileHealthSummary(
                completeness_score=0,
                is_ready_for_apply=False,
                missing_critical_items=["Candidate Profile record missing"],
                pending_confirmations=["Create profile"],
                has_resume=False,
                target_roles_count=0,
            )

        completeness = calculate_profile_completeness(candidate)
        missing_critical = completeness.missing_required
        pending_confirmations = completeness.missing_optional

        has_resume = any("resume" in d.criterion.lower() and d.met for d in completeness.details) or any(doc.type == "resume" for doc in (candidate.documents or []))
        target_roles = []
        if candidate.preference_record and candidate.preference_record.target_roles:
            target_roles = candidate.preference_record.target_roles
        elif candidate.preferences and "target_roles" in candidate.preferences:
            target_roles = candidate.preferences.get("target_roles", [])

        return ProfileHealthSummary(
            completeness_score=completeness.score,
            is_ready_for_apply=completeness.score >= 70 and has_resume,
            missing_critical_items=missing_critical,
            pending_confirmations=pending_confirmations,
            has_resume=has_resume,
            target_roles_count=len(target_roles),
        )

    @classmethod
    def _get_recent_activity(cls, db: Session, limit: int = 15) -> List[RecentActivityItem]:
        items: List[RecentActivityItem] = []

        # 1. Recent Application Events
        events = (
            db.query(ApplicationEvent, Application, Job)
            .join(Application, Application.id == ApplicationEvent.application_id)
            .outerjoin(Job, Job.id == Application.job_id)
            .order_by(ApplicationEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        for ev, app, job in events:
            items.append(
                RecentActivityItem(
                    id=f"event-{ev.id}",
                    timestamp=ev.created_at,
                    event_type=ev.event_type,
                    title=f"Application {ev.event_type.replace('_', ' ').title()}",
                    description=ev.description or "",
                    actor=ev.actor or "system",
                    job_id=job.id if job else None,
                    application_id=app.id,
                    job_title=job.title if job else None,
                    company=job.company if job else None,
                )
            )

        # 2. Recent Application Notes
        notes = (
            db.query(ApplicationNote, Application, Job)
            .join(Application, Application.id == ApplicationNote.application_id)
            .outerjoin(Job, Job.id == Application.job_id)
            .order_by(ApplicationNote.created_at.desc())
            .limit(5)
            .all()
        )
        for nt, app, job in notes:
            items.append(
                RecentActivityItem(
                    id=f"note-{nt.id}",
                    timestamp=nt.created_at,
                    event_type="NOTE_ADDED",
                    title=f"Note Added ({nt.category.title()})",
                    description=nt.content[:100] + ("..." if len(nt.content) > 100 else ""),
                    actor=nt.author,
                    job_id=job.id if job else None,
                    application_id=app.id,
                    job_title=job.title if job else None,
                    company=job.company if job else None,
                )
            )

        # 3. Sort chronologically descending
        items.sort(key=lambda x: x.timestamp, reverse=True)
        return items[:limit]

    @classmethod
    def _get_feedback_summary(cls, db: Session, candidate_id: Optional[str]) -> FeedbackSummaryKPIs:
        report = ApplicationFeedbackEngine.get_feedback_report(db, candidate_id)
        conversions = report["conversions"]
        app_to_int = conversions["application_to_interview"]
        app_to_off = conversions["application_to_offer"]
        int_to_off = conversions["interview_to_offer"]

        top_obs = [o["message"] for o in report.get("observations", [])][:3]

        return FeedbackSummaryKPIs(
            submitted_count=conversions.get("submitted_total", 0),
            app_to_interview_rate=app_to_int["rate"],
            app_to_interview_fraction=f"{app_to_int['numerator']}/{app_to_int['denominator']}",
            app_to_offer_rate=app_to_off["rate"],
            app_to_offer_fraction=f"{app_to_off['numerator']}/{app_to_off['denominator']}",
            interview_to_offer_rate=int_to_off["rate"],
            interview_to_offer_fraction=f"{int_to_off['numerator']}/{int_to_off['denominator']}",
            sample_size_alert=report.get("sample_size_alert"),
            top_observations=top_obs,
        )
