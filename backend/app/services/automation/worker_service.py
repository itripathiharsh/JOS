import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.automation import AutomationTask, AutomationSettings
from app.models.application import Application, ApplicationNote
from app.models.job import Job
from app.models.profile import CandidateProfile
from app.models.decision import ApplicationDecision
from app.models.preparation import ApplicationPreparation
from app.models.execution import ApplicationExecution

from app.services.automation.queue_service import AutomationQueueService
from app.services.automation.approval_service import ApplicationApprovalService
from app.services.discovery_service import execute_discovery_run
from app.services.matching_service import calculate_or_get_job_match
from app.services.decision_engine.engine import ApplicationDecisionEngine
from app.services.preparation_engine.engine import ApplicationPreparationEngine
from app.services.execution_layer.idempotency import DuplicateSubmissionGuard
from app.services.execution_layer.engine import ApplicationExecutionEngine
from app.services.execution_layer.models import ExecutionStatus
from app.schemas.automation import WorkerTickResult

logger = logging.getLogger(__name__)


def get_utc_now():
    return datetime.now(timezone.utc)


class AutomationWorkerService:
    """
    Step 12: Controlled Background Automation Worker.
    Executes safe background tasks (Discovery, Matching, Decisions, Preparation, Follow-up checks).
    Enforces that an Application record or an APPLY decision NEVER equals permission to submit.
    Strictly halts at human approval gates, CAPTCHA, login barriers, and stale data.
    """

    @classmethod
    def run_worker_tick(
        cls,
        db: Session,
        worker_id: Optional[str] = None,
        max_tasks: int = 5,
    ) -> WorkerTickResult:
        """
        Executes a single controlled worker tick:
        1. Recovers any expired/stuck worker leases
        2. Claims and executes up to max_tasks from the durable task queue
        """
        w_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        recovered = AutomationQueueService.recover_stuck_tasks(db)

        claimed_count = 0
        succeeded_count = 0
        failed_count = 0
        blocked_count = 0
        processed_task_ids: List[str] = []

        for _ in range(max_tasks):
            task = AutomationQueueService.claim_next_task(db, worker_id=w_id)
            if not task:
                break

            claimed_count += 1
            processed_task_ids.append(task.id)

            try:
                cls.process_task(db, task, worker_id=w_id)
                # Re-fetch task state
                db.refresh(task)
                if task.status == "SUCCEEDED":
                    succeeded_count += 1
                elif task.status == "BLOCKED":
                    blocked_count += 1
                elif task.status in ("FAILED", "RETRY_WAIT"):
                    failed_count += 1
            except Exception as e:
                logger.exception(f"Unhandled exception while processing task {task.id}: {e}")
                AutomationQueueService.fail_task(
                    db,
                    task_id=task.id,
                    error_msg=f"Unhandled worker error: {str(e)}",
                    is_transient=True,
                )
                failed_count += 1

        return WorkerTickResult(
            worker_id=w_id,
            claimed_count=claimed_count,
            succeeded_count=succeeded_count,
            failed_count=failed_count,
            blocked_count=blocked_count,
            recovered_count=recovered,
            task_ids=processed_task_ids,
        )

    @classmethod
    def process_task(
        cls,
        db: Session,
        task: AutomationTask,
        worker_id: str,
    ) -> None:
        """Dispatches an individual task to its specialized handler."""
        task_type = task.task_type

        if task_type == "DISCOVERY":
            cls._handle_discovery(db, task)
        elif task_type in ("GOV_DISCOVERY", "GOV_SOURCE_DISCOVERY"):
            cls._handle_gov_discovery(db, task)
        elif task_type in ("GOV_CRAWL", "GOV_VACANCY_CRAWL", "GOV_SOURCE_CRAWL"):
            cls._handle_gov_crawl(db, task)
        elif task_type in ("GOV_DEADLINE_RECHECK", "GOV_VACANCY_RECHECK"):
            cls._handle_gov_deadline_recheck(db, task)
        elif task_type == "GOV_CHANGE_DETECTION":
            cls._handle_gov_change_detection(db, task)
        elif task_type == "MATCHING":
            cls._handle_matching(db, task)
        elif task_type == "DECISION":
            cls._handle_decision(db, task)
        elif task_type == "PREPARATION":
            cls._handle_preparation(db, task)
        elif task_type == "FOLLOWUP_CHECK":
            cls._handle_followup_check(db, task)
        elif task_type == "STALE_CHECK":
            cls._handle_stale_check(db, task)
        elif task_type == "EXECUTION":
            cls._handle_execution(db, task)
        else:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Unknown task type '{task_type}'",
                is_transient=False,
            )

    @classmethod
    def _handle_discovery(cls, db: Session, task: AutomationTask) -> None:
        """Executes automated job search and discovery using existing connectors."""
        try:
            source = task.payload.get("source", "remotive") if task.payload else "remotive"
            if source == "government":
                from app.services.government.engine import GovernmentDiscoveryEngine
                crawl_res = GovernmentDiscoveryEngine.crawl_batch(db, batch_size=20)
                AutomationQueueService.complete_task(
                    db,
                    task_id=task.id,
                    result=crawl_res,
                )
                return

            dry_run = task.payload.get("dry_run", False) if task.payload else False
            run_summary = execute_discovery_run(
                db=db,
                source_name=source,
                dry_run=dry_run,
            )
            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result={
                    "discovery_run_id": run_summary.id,
                    "total_jobs_fetched": run_summary.jobs_fetched,
                    "total_jobs_created": run_summary.jobs_created,
                    "total_jobs_updated": run_summary.jobs_updated,
                    "status": run_summary.status,
                },
            )
        except Exception as e:
            err_str = str(e)
            is_transient = "network" in err_str.lower() or "timeout" in err_str.lower() or "connection" in err_str.lower()
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Discovery failed: {err_str}",
                is_transient=is_transient,
            )

    @classmethod
    def _handle_gov_discovery(cls, db: Session, task: AutomationTask) -> None:
        """Executes autonomous open-ended search engine discovery for new Indian government sources."""
        try:
            from app.services.government.engine import GovernmentDiscoveryEngine
            scope = task.payload.get("scope", "ALL") if task.payload else "ALL"
            state = task.payload.get("state") if task.payload else None
            max_q = task.payload.get("max_queries", 15) if task.payload else 15
            res = GovernmentDiscoveryEngine.discover_sources_open_ended(
                db=db,
                scope=scope,
                state_filter=state,
                max_queries=max_q
            )
            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result=res,
            )
        except Exception as e:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Government source discovery failed: {str(e)}",
                is_transient=True,
            )

    @classmethod
    def _handle_gov_crawl(cls, db: Session, task: AutomationTask) -> None:
        """Crawls a specific government source or batch of due sources for vacancy announcements and PDFs."""
        try:
            from app.services.government.engine import GovernmentDiscoveryEngine
            from app.models.government import GovernmentSource

            payload = task.payload or {}
            source_id = payload.get("source_id")

            if source_id:
                src = db.query(GovernmentSource).filter(GovernmentSource.id == source_id).first()
                if not src:
                    AutomationQueueService.fail_task(
                        db,
                        task_id=task.id,
                        error_msg=f"Government source '{source_id}' not found.",
                        is_transient=False,
                    )
                    return
                res = GovernmentDiscoveryEngine.crawl_source(db, src)
            else:
                batch_size = payload.get("batch_size", 20)
                res = GovernmentDiscoveryEngine.crawl_due_sources_batch(
                    db=db,
                    batch_size=batch_size
                )

            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result=res,
            )
        except Exception as e:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Government vacancy crawl failed: {str(e)}",
                is_transient=True,
            )

    @classmethod
    def _handle_gov_deadline_recheck(cls, db: Session, task: AutomationTask) -> None:
        """Revalidates application deadlines across active vacancies and updates statuses."""
        try:
            from app.services.government.scheduler import GovernmentContinuousScheduler
            stats = GovernmentContinuousScheduler.revalidate_vacancy_deadlines(db)
            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result=stats,
            )
        except Exception as e:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Government deadline recheck failed: {str(e)}",
                is_transient=True,
            )

    @classmethod
    def _handle_gov_change_detection(cls, db: Session, task: AutomationTask) -> None:
        """Checks for changes, extensions, and corrigenda across monitored sources."""
        try:
            from app.services.government.scheduler import GovernmentContinuousScheduler
            stats = GovernmentContinuousScheduler.revalidate_vacancy_deadlines(db)
            metrics = GovernmentContinuousScheduler.get_monitoring_metrics(db)
            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result={"deadline_stats": stats, "metrics": metrics},
            )
        except Exception as e:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Government change detection failed: {str(e)}",
                is_transient=True,
            )

    @classmethod
    def _handle_matching(cls, db: Session, task: AutomationTask) -> None:
        """Evaluates match quality and generates decision recommendation for a canonical job."""
        if not task.job_id or not task.candidate_id:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg="MATCHING task requires both job_id and candidate_id.",
                is_transient=False,
            )
            return

        job = db.query(Job).filter(Job.id == task.job_id).first()
        if not job or not job.is_canonical:
            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result={"skipped": True, "reason": "Job is non-canonical or no longer exists."},
            )
            return

        try:
            match_res, _ = calculate_or_get_job_match(
                db=db,
                job_id=task.job_id,
                candidate_id=task.candidate_id,
            )
            decision, _ = ApplicationDecisionEngine.evaluate_and_persist(
                db=db,
                job_id=task.job_id,
                candidate_id=task.candidate_id,
            )
            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result={
                    "match_score": match_res.overall_score,
                    "fit_category": match_res.fit_category,
                    "decision": decision.decision,
                    "risk_level": decision.risk_level,
                },
            )
        except Exception as e:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Matching/Decision evaluation failed: {str(e)}",
                is_transient=False,
            )

    @classmethod
    def _handle_decision(cls, db: Session, task: AutomationTask) -> None:
        """Computes or re-evaluates ApplicationDecision for a job."""
        if not task.job_id or not task.candidate_id:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg="DECISION task requires job_id and candidate_id.",
                is_transient=False,
            )
            return

        try:
            decision, _ = ApplicationDecisionEngine.evaluate_and_persist(
                db=db,
                job_id=task.job_id,
                candidate_id=task.candidate_id,
                force=task.payload.get("force_recompute", False) if task.payload else False,
            )
            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result={"decision": decision.decision, "risk_level": decision.risk_level},
            )
        except Exception as e:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Decision evaluation failed: {str(e)}",
                is_transient=False,
            )

    @classmethod
    def _handle_preparation(cls, db: Session, task: AutomationTask) -> None:
        """
        Prepares an application package for a job with an APPLY decision.
        If preparation produces READY_WITH_REVIEW, enters human attention queue and does NOT proceed.
        """
        if not task.job_id or not task.candidate_id:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg="PREPARATION task requires job_id and candidate_id.",
                is_transient=False,
            )
            return

        # Check existing decision
        decision = db.query(ApplicationDecision).filter(
            ApplicationDecision.job_id == task.job_id,
            ApplicationDecision.candidate_id == task.candidate_id,
        ).first()

        if not decision or decision.decision != "APPLY":
            status_desc = decision.decision if decision else "NONE"
            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result={
                    "skipped": True,
                    "reason": f"Job decision is '{status_desc}'. Automated preparation requires APPLY decision.",
                },
            )
            return

        try:
            prep = ApplicationPreparationEngine.prepare_application_for_job(
                db=db,
                job_id=task.job_id,
                candidate_id=task.candidate_id,
                application_id=task.application_id,
            )
            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result={
                    "preparation_id": prep.id,
                    "readiness_status": prep.readiness_status,
                    "version": prep.version,
                    "requires_review": prep.readiness_status == "READY_WITH_REVIEW",
                },
            )
        except Exception as e:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Preparation generation failed: {str(e)}",
                is_transient=False,
            )

    @classmethod
    def _handle_followup_check(cls, db: Session, task: AutomationTask) -> None:
        """Identifies submitted applications > 7 days old with no recent activity."""
        now = get_utc_now()
        threshold_date = now - timedelta(days=7)

        apps = (
            db.query(Application)
            .filter(
                Application.lifecycle_stage.in_(["SUBMITTED", "ACKNOWLEDGED"]),
                Application.applied_at <= threshold_date,
            )
            .all()
        )

        flagged_count = 0
        for app in apps:
            # Check if note created in last 7 days
            recent_note = (
                db.query(ApplicationNote)
                .filter(
                    ApplicationNote.application_id == app.id,
                    ApplicationNote.created_at >= threshold_date,
                )
                .first()
            )
            if not recent_note:
                flagged_count += 1

        AutomationQueueService.complete_task(
            db,
            task_id=task.id,
            result={"followups_flagged": flagged_count},
        )

    @classmethod
    def _handle_stale_check(cls, db: Session, task: AutomationTask) -> None:
        """Revalidates preparations against updated candidate profiles or job descriptions."""
        preps = db.query(ApplicationPreparation).all()
        stale_count = 0

        for prep in preps:
            is_stale = False
            candidate = db.query(CandidateProfile).filter(CandidateProfile.id == prep.candidate_id).first()
            job = db.query(Job).filter(Job.id == prep.job_id).first()

            if candidate and candidate.updated_at and candidate.updated_at > prep.prepared_at:
                is_stale = True
            if job and job.updated_at and job.updated_at > prep.prepared_at:
                is_stale = True

            if is_stale and prep.readiness_status == "READY":
                prep.readiness_status = "READY_WITH_REVIEW"
                reasons = prep.readiness_reasons or []
                reasons.append("Underlying profile or job description was updated. Human review required.")
                prep.readiness_reasons = reasons
                stale_count += 1

        if stale_count > 0:
            db.commit()

        AutomationQueueService.complete_task(
            db,
            task_id=task.id,
            result={"stale_preparations_flagged": stale_count},
        )

    @classmethod
    def _handle_execution(cls, db: Session, task: AutomationTask) -> None:
        """
        CRITICAL EXECUTION SAFETY GATE:
        Prevents automated submission unless all verification conditions are met:
        1. Application exists and is not already submitted
        2. ApplicationDecision = APPLY
        3. ApplicationPreparation = READY
        4. Explicit, unexpired human approval exists (ApplicationApproval)
        5. No anti-bot / CAPTCHA barriers
        """
        if not task.application_id:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg="EXECUTION task requires application_id.",
                is_transient=False,
            )
            return

        app_rec = db.query(Application).filter(Application.id == task.application_id).first()
        if not app_rec:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Application {task.application_id} not found.",
                is_transient=False,
            )
            return

        # 1. Check duplicate / already submitted guard
        is_eligible, elig_reason, _ = DuplicateSubmissionGuard.check_application_eligibility(
            db, task.application_id
        )
        if not is_eligible:
            AutomationQueueService.block_task(
                db,
                task_id=task.id,
                reason=elig_reason,
                error_category="DUPLICATE_OR_ALREADY_SUBMITTED",
            )
            return

        # 2. Check Decision
        decision = db.query(ApplicationDecision).filter(
            ApplicationDecision.job_id == app_rec.job_id,
            ApplicationDecision.candidate_id == app_rec.candidate_id,
        ).first()

        if not decision or decision.decision != "APPLY":
            AutomationQueueService.block_task(
                db,
                task_id=task.id,
                reason=f"Submission blocked: Application decision is '{decision.decision if decision else 'NONE'}'. Must be APPLY.",
                error_category="DECISION_GATE",
            )
            return

        # 3. Check Preparation
        prep = db.query(ApplicationPreparation).filter(
            ApplicationPreparation.application_id == app_rec.id
        ).first()

        if not prep or prep.readiness_status != "READY":
            status_desc = prep.readiness_status if prep else "MISSING"
            AutomationQueueService.block_task(
                db,
                task_id=task.id,
                reason=f"Submission blocked: Preparation package status is '{status_desc}'. Must be READY.",
                error_category="PREPARATION_GATE",
            )
            return

        # 4. CRITICAL HUMAN APPROVAL GATE
        is_approved, apprv_reason, approval = ApplicationApprovalService.validate_approval_for_submission(
            db, task.application_id
        )
        if not is_approved:
            AutomationQueueService.block_task(
                db,
                task_id=task.id,
                reason=apprv_reason,
                error_category="APPROVAL_REQUIRED",
            )
            return

        # 5. Check mode: In Step 12, real external submissions are strictly gated.
        # If in ASSISTED mode or execution requested without direct user trigger:
        settings = (
            db.query(AutomationSettings)
            .filter(AutomationSettings.candidate_id == app_rec.candidate_id)
            .first()
        )
        if not settings or settings.mode == "MANUAL":
            AutomationQueueService.block_task(
                db,
                task_id=task.id,
                reason="Execution blocked: Automation mode is MANUAL. Human trigger required.",
                error_category="POLICY_GATE",
            )
            return

        # Start execution through Step 9 engine
        try:
            exec_rec = ApplicationExecutionEngine.start_execution(
                db=db,
                application_id=app_rec.id,
                mode=settings.mode,
                source=task.payload.get("source", "generic_web") if task.payload else "generic_web",
                allow_force=False,
            )

            # Check for barriers (CAPTCHA, Login, Awaiting User)
            if exec_rec.status == ExecutionStatus.BLOCKED.value or exec_rec.requires_user_action:
                blocker_msg = exec_rec.blocker_reason or exec_rec.user_action_prompt or "Human action required during execution."
                AutomationQueueService.block_task(
                    db,
                    task_id=task.id,
                    reason=f"Execution halted at barrier: {blocker_msg}",
                    error_category="EXECUTION_BARRIER",
                )
                return

            if exec_rec.status == ExecutionStatus.READY_TO_SUBMIT.value:
                # With verified approval, execute final submission
                exec_rec = ApplicationExecutionEngine.approve_and_submit(
                    db=db,
                    execution_id=exec_rec.id,
                )

            AutomationQueueService.complete_task(
                db,
                task_id=task.id,
                result={
                    "execution_id": exec_rec.id,
                    "status": exec_rec.status,
                    "submission_confirmed": exec_rec.submission_confirmed,
                },
            )

        except Exception as e:
            AutomationQueueService.fail_task(
                db,
                task_id=task.id,
                error_msg=f"Execution error: {str(e)}",
                is_transient=False,
            )
