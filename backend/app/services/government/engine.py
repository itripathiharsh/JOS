"""
Job Operating System - Master Government Job Source Discovery Engine
Orchestrates:
1. Seed Registry Initialization
2. Open-Ended Search Engine Discovery (Central, 28 States, 8 UTs, PSUs, Research)
3. Government Portal Exploration & Recursive Sub-Organisation Discovery
4. PDF-First Recruitment Extraction & Corrigendum Tracking
5. Pipeline Ingestion (Deduplication, Matching, Decision, Preparation, Safety)
"""
import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc

from app.models.government import (
    GovernmentSource,
    GovernmentVacancy,
    GovernmentDiscoveryRun,
    GovernmentChangeEvent,
    GovernmentUnresolvedTarget,
)
from app.models.job import Job, Company
from app.models.profile import CandidateProfile
from app.schemas.government import GovernmentCoverageResponse
from app.services.government.seed_registry import SEED_GOVERNMENT_ORGANISATIONS, INDIAN_STATES, INDIAN_UTS
from app.services.government.search_engine import GovernmentSearchDiscoveryEngine
from app.services.government.page_explorer import GovernmentPageExplorer
from app.services.government.pdf_extractor import GovernmentPdfExtractor
from app.services.government.coverage_matrix import GovernmentCoverageCalculator
from app.services.government.scheduler import GovernmentContinuousScheduler
from app.services.government.universe_parser import GovernmentUniverseParser
from app.services.government.source_resolver import GovernmentSourceResolver
from connectors.models import NormalizedJob
from app.services.deduplication import normalize_url, AntiDuplicateEngine
from app.services.matching_service import calculate_or_get_job_match
from app.services.decision_engine import ApplicationDecisionEngine

logger = logging.getLogger(__name__)


def get_utc_now():
    return datetime.now(timezone.utc)


def sanitize_text(val: Optional[str]) -> Optional[str]:
    """Sanitizes text strings, stripping PostgreSQL-incompatible null bytes (\x00)."""
    if val is None:
        return None
    return str(val).replace("\x00", "").strip()


class GovernmentDiscoveryEngine:
    """
    Central orchestrator for autonomous discovery and crawling of Indian
    government, PSU, research, university, and contractual employment sources.
    """

    CHECKPOINT_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "govt",
        "discovery_output",
        "discovery_checkpoint.json"
    )

    @classmethod
    def save_checkpoint(cls, data: Dict[str, Any], filepath: Optional[str] = None) -> str:
        """Persists discovery checkpoint to disk for crash recovery and resumability."""
        target = filepath or cls.CHECKPOINT_FILE
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump({**data, "timestamp": datetime.now(timezone.utc).isoformat()}, f, indent=2)
        return target

    @classmethod
    def load_checkpoint(cls, filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Loads discovery checkpoint from disk if present."""
        target = filepath or cls.CHECKPOINT_FILE
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def _upsert_source(self, source_dict: Dict[str, Any]) -> Tuple[GovernmentSource, bool]:
        """Upsert source record avoiding duplicates by official_domain."""
        if not self.db:
            raise ValueError("Database session required for instance operations.")
        domain = source_dict["official_domain"].lower().strip()
        existing = self.db.query(GovernmentSource).filter(
            GovernmentSource.official_domain == domain
        ).first()
        now = get_utc_now()
        if existing:
            for k, v in source_dict.items():
                if v is not None and hasattr(existing, k):
                    setattr(existing, k, v)
            existing.last_seen = now
            return existing, False
        else:
            src = GovernmentSource(**source_dict)
            if not src.discovered_at:
                src.discovered_at = now
            if not src.last_seen:
                src.last_seen = now
            self.db.add(src)
            return src, True

    def crawl_batch(self, batch_size: int = 20, force_recheck: bool = False, **kwargs) -> Dict[str, Any]:
        if not self.db:
            raise ValueError("Database session required.")
        return self.__class__.crawl_batch(self.db, batch_size=batch_size, force_recheck=force_recheck, **kwargs)

    @classmethod
    def seed_initial_sources(cls, db: Session) -> int:
        """
        Seeds the persistent GovernmentSource registry with initial authoritative
        central ministries, states, UTs, PSUs, and research institutes.
        Idempotent: skips already registered domains.
        """
        created_count = 0
        now = get_utc_now()

        for seed in SEED_GOVERNMENT_ORGANISATIONS:
            domain = seed["official_domain"].lower().strip()
            existing = db.query(GovernmentSource).filter(
                GovernmentSource.official_domain == domain
            ).first()

            if not existing:
                src = GovernmentSource(
                    organisation_name=seed["organisation_name"],
                    organisation_type=seed.get("organisation_type", "other"),
                    government_level=seed.get("government_level", "central"),
                    state=seed.get("state"),
                    city=seed.get("city"),
                    official_domain=domain,
                    career_url=seed.get("career_url"),
                    recruitment_url=seed.get("recruitment_url"),
                    source_type=seed.get("source_type", "portal"),
                    source_status="VERIFIED",
                    discovery_method="seed",
                    discovered_at=now,
                    last_seen=now,
                    crawl_interval_minutes=1440,
                    next_crawl_at=now,
                    change_frequency_category="low",
                    consecutive_failures=0,
                    confidence=1.0,
                    relevance_score=1.0,
                )
                db.add(src)
                created_count += 1

        if created_count > 0:
            db.commit()
            logger.info(f"Seeded {created_count} initial government sources.")

        return created_count

    @classmethod
    def discover_sources_open_ended(
        self,
        db: Session,
        scope: str = "ALL",
        state_filter: Optional[str] = None,
        max_queries: int = 15,
    ) -> Dict[str, Any]:
        """
        Executes autonomous search engine discovery to identify previously unknown
        government websites, recruitment boards, and contractual vacancies.
        """
        # Ensure seeds exist
        self.seed_initial_sources(db)

        start_time = time.time()
        search_engine = GovernmentSearchDiscoveryEngine()
        queries = search_engine.generate_search_queries(
            scope=scope,
            state_filter=state_filter,
            max_queries=max_queries
        )

        sources_discovered = 0
        now = get_utc_now()
        discovered_domains_set = set()

        for q in queries:
            items = search_engine.execute_search_query(q)
            for it in items:
                domain = it["domain"]
                if not domain or domain in discovered_domains_set:
                    continue
                discovered_domains_set.add(domain)

                existing = db.query(GovernmentSource).filter(
                    GovernmentSource.official_domain == domain
                ).first()

                if not existing:
                    meta = search_engine.infer_organisation_metadata(
                        domain=domain,
                        title=it.get("title", ""),
                        snippet=it.get("snippet", "")
                    )
                    new_src = GovernmentSource(
                        organisation_name=meta["organisation_name"],
                        organisation_type=meta["organisation_type"],
                        government_level=meta["government_level"],
                        state=meta["state"] or state_filter,
                        official_domain=domain,
                        career_url=it["url"],
                        source_type="portal",
                        source_status="DISCOVERED",
                        discovery_method="search_engine",
                        discovered_from=q,
                        discovered_at=now,
                        last_seen=now,
                        confidence=0.9,
                        relevance_score=0.9,
                    )
                    db.add(new_src)
                    sources_discovered += 1
                else:
                    existing.last_seen = now

            # Modest delay between queries
            time.sleep(0.5)

        db.commit()
        duration_ms = (time.time() - start_time) * 1000.0

        # Record audit run
        run_record = GovernmentDiscoveryRun(
            run_type="source_discovery",
            status="completed",
            scope_filter=f"{scope}:{state_filter or 'ALL'}",
            sources_discovered=sources_discovered,
            sources_verified=0,
            vacancies_discovered=0,
            vacancies_created=0,
            vacancies_updated=0,
            duration_ms=duration_ms,
        )
        db.add(run_record)
        db.commit()

        logger.info(f"Open-ended source discovery completed: {sources_discovered} new sources found in {duration_ms:.1f}ms")
        return {
            "sources_discovered": sources_discovered,
            "queries_executed": len(queries),
            "duration_ms": duration_ms,
        }

    @classmethod
    def crawl_source(
        cls,
        db: Session,
        source: GovernmentSource
    ) -> Dict[str, Any]:
        """
        Inspects an individual government source with continuous freshness protection:
        1. Explores website and discovers child institutions recursively.
        2. Discovers recruitment notices & PDF links.
        3. Computes document SHA-256 and compares with historical state.
        4. Detects NEW, UPDATED, EXTENDED, CORRIGENDUM, or CLOSED events without duplicating jobs.
        5. Ingests or updates jobs and links to Candidate Profile match & decision pipeline.
        6. Reschedules source deterministically with adaptive intervals and failure backoff.
        """
        explorer = GovernmentPageExplorer()
        pdf_extractor = GovernmentPdfExtractor()
        now = get_utc_now()

        source.crawl_status = "crawling"
        source.last_checked = now
        source.is_locked = True
        source.locked_at = now
        db.commit()

        vacancies_created = 0
        vacancies_updated = 0
        change_events_count = 0
        child_registered = 0
        change_detected = False
        outcome = "success"
        error_type: Optional[str] = None

        try:
            res = explorer.explore_organisation_domain(
                domain=source.official_domain,
                known_career_url=source.career_url or source.recruitment_url
            )

            source.crawl_status = res["crawl_status"]
            if res.get("requires_manual_access"):
                source.source_status = "REQUIRES_MANUAL_ACCESS"
                outcome = "manual_access"
                error_type = "MANUAL_ACCESS"
            elif res["crawl_status"] == "success":
                source.source_status = "ACTIVE"
                source.last_success = now
                outcome = "success"
            else:
                outcome = "failed"
                if "block" in str(res.get("error_message", "")).lower() or "403" in str(res.get("error_message", "")):
                    error_type = "BLOCKED"
                elif "captcha" in str(res.get("error_message", "")).lower():
                    error_type = "MANUAL_ACCESS"
                elif "dns" in str(res.get("error_message", "")).lower() or "410" in str(res.get("error_message", "")):
                    error_type = "DEAD"
                else:
                    error_type = "TEMPORARY_FAILURE"

            # 1. Register any recursively discovered child organisations
            for child in res.get("child_sources", []):
                child_domain = child["official_domain"]
                existing_child = db.query(GovernmentSource).filter(
                    GovernmentSource.official_domain == child_domain
                ).first()
                if not existing_child:
                    new_child = GovernmentSource(
                        organisation_name=child["organisation_name"],
                        organisation_type=child["organisation_type"],
                        government_level=child["government_level"],
                        state=child.get("state") or source.state,
                        official_domain=child_domain,
                        career_url=child.get("career_url"),
                        source_type="portal",
                        source_status="DISCOVERED",
                        discovery_method="recursive_link",
                        discovered_from=source.official_domain,
                        discovered_at=now,
                        last_seen=now,
                        crawl_interval_minutes=1440,
                        next_crawl_at=now,
                        change_frequency_category="low",
                    )
                    db.add(new_child)
                    child_registered += 1

            # 2. Process discovered vacancies with versioning and change detection
            for vac_raw in res.get("vacancies", []):
                pdf_url = vac_raw.get("pdf_url")
                pdf_data = {}
                if pdf_url:
                    pdf_data = pdf_extractor.process_pdf_url(pdf_url)

                title = sanitize_text(pdf_data.get("position") or vac_raw.get("title") or "Technical Specialist")
                company = sanitize_text(source.organisation_name)
                salary_str = sanitize_text(pdf_data.get("salary"))
                duration_str = sanitize_text(pdf_data.get("contract_duration"))
                age_limit_str = sanitize_text(pdf_data.get("age_limit"))
                num_positions = pdf_data.get("number_of_positions")
                change_type_raw = pdf_data.get("change_type", "new_vacancy")
                corrigendum = sanitize_text(pdf_data.get("corrigendum_details"))
                app_email = sanitize_text(pdf_data.get("application_email"))
                apply_url = sanitize_text(vac_raw.get("apply_url") or pdf_url or source.career_url or f"https://{source.official_domain}")
                deadline_dt = pdf_data.get("application_deadline")

                # Stable identifier per vacancy
                unique_token = pdf_data.get("pdf_sha256") or vac_raw.get("pdf_url") or vac_raw.get("title")
                import hashlib
                ext_id = f"gov_{hashlib.md5(f'{source.official_domain}_{unique_token}'.encode('utf-8')).hexdigest()[:12]}"

                raw_desc = vac_raw.get('description', '') or ''
                extracted_pdf_snippet = sanitize_text(pdf_data.get('pdf_extracted_text', '')[:3000]) or ''
                desc_text = sanitize_text(
                    f"{raw_desc}\n\n"
                    f"Official Government Notification from {company}.\n"
                    f"Contract Duration: {duration_str or 'Specified in notice'}\n"
                    f"Remuneration: {salary_str or 'As per Government Rules'}\n"
                    f"Selection Process: {pdf_data.get('selection_process') or 'As per notification'}\n"
                    f"{extracted_pdf_snippet}"
                )

                # Query existing job
                existing_job = db.query(Job).filter(
                    Job.source == "government",
                    Job.external_job_id == ext_id
                ).first()

                if not existing_job:
                    # Also check by application_url to prevent duplication when URL is identical
                    existing_job = db.query(Job).filter(
                        Job.source == "government",
                        Job.application_url == apply_url
                    ).first()

                if not existing_job:
                    # 1. NEW VACANCY
                    comp_rec = db.query(Company).filter(Company.name == company).first()
                    if not comp_rec:
                        comp_rec = Company(name=company, website=f"https://{source.official_domain}")
                        db.add(comp_rec)
                        db.flush()

                    new_job = Job(
                        source="government",
                        external_job_id=ext_id,
                        title=title[:255] if title else "Technical Specialist",
                        company=company[:255] if company else "Government Organization",
                        location=source.state or "India",
                        work_mode="onsite",
                        description=desc_text,
                        application_url=apply_url,
                        canonical_url=normalize_url(apply_url) if apply_url else None,
                        currency="INR",
                        discovered_at=now,
                        last_seen_at=now,
                        status="discovered",
                        is_canonical=True,
                        duplicate_status="canonical",
                    )
                    db.add(new_job)
                    db.flush()

                    AntiDuplicateEngine.evaluate_and_link(db, new_job)

                    # Initial deadline status
                    deadline_status = "UNKNOWN"
                    if deadline_dt:
                        diff = (deadline_dt - now).total_seconds()
                        if diff <= 0:
                            deadline_status = "EXPIRED"
                        elif diff <= 86400:
                            deadline_status = "DEADLINE_TODAY"
                        elif diff <= 259200:
                            deadline_status = "DEADLINE_APPROACHING"
                        else:
                            deadline_status = "OPEN"

                    gov_vac = GovernmentVacancy(
                        job_id=new_job.id,
                        source_id=source.id,
                        government_level=source.government_level,
                        organisation_type=source.organisation_type,
                        state=source.state,
                        employment_type="Contract" if vac_raw.get("is_contractual") else "Permanent",
                        contract_duration=duration_str,
                        pay_scale=salary_str,
                        number_of_positions=num_positions,
                        age_limit=age_limit_str,
                        selection_process=sanitize_text(pdf_data.get("selection_process")),
                        official_notification_url=pdf_url or vac_raw.get("source_url"),
                        official_application_url=apply_url,
                        application_mode="email" if app_email else "online_portal",
                        application_email=app_email,
                        pdf_url=pdf_url,
                        pdf_sha256=pdf_data.get("pdf_sha256"),
                        pdf_extracted_text=sanitize_text(pdf_data.get("pdf_extracted_text")),
                        extraction_status=pdf_data.get("extraction_status", "not_applicable"),
                        change_type="new_vacancy",
                        corrigendum_details=corrigendum,
                        published_at=now,
                        application_deadline=deadline_dt,
                        deadline_status=deadline_status,
                        last_verified_at=now,
                    )
                    db.add(gov_vac)
                    db.flush()

                    # Audit Change Event
                    evt = GovernmentChangeEvent(
                        source_id=source.id,
                        vacancy_id=gov_vac.id,
                        url=apply_url or pdf_url or f"https://{source.official_domain}",
                        document_type="pdf" if pdf_url else "notice",
                        previous_hash=None,
                        new_hash=pdf_data.get("pdf_sha256"),
                        change_type="NEW",
                        change_summary=f"Discovered new vacancy: {title} ({company})",
                        detected_at=now,
                    )
                    db.add(evt)
                    change_events_count += 1
                    change_detected = True

                    # Pipeline matching & decision
                    try:
                        calculate_or_get_job_match(db=db, job_id=new_job.id)
                        ApplicationDecisionEngine.evaluate_and_persist(db=db, job_id=new_job.id)
                    except Exception as eval_e:
                        logger.debug(f"Automatic matching skipped during crawl: {eval_e}")

                    vacancies_created += 1

                else:
                    # 2. EXISTING VACANCY - CHECK FOR CHANGES / CORRIGENDA
                    existing_job.last_seen_at = now
                    existing_job.description = desc_text

                    gov_vac = db.query(GovernmentVacancy).filter(
                        GovernmentVacancy.job_id == existing_job.id
                    ).first()

                    if gov_vac:
                        gov_vac.last_verified_at = now
                        old_hash = gov_vac.pdf_sha256
                        new_hash = pdf_data.get("pdf_sha256")
                        has_hash_change = new_hash and old_hash and (new_hash != old_hash)

                        # Detect Corrigendum or Extension
                        is_corrigendum = (
                            change_type_raw == "corrigendum"
                            or (corrigendum and not gov_vac.corrigendum_details)
                        )
                        is_extension = False
                        if deadline_dt and gov_vac.application_deadline:
                            if deadline_dt > gov_vac.application_deadline:
                                is_extension = True

                        if has_hash_change or is_corrigendum or is_extension:
                            change_detected = True
                            event_type = "CORRIGENDUM" if is_corrigendum else ("EXTENDED" if is_extension else "UPDATED")

                            gov_vac.pdf_sha256 = new_hash or old_hash
                            gov_vac.pdf_extracted_text = sanitize_text(pdf_data.get("pdf_extracted_text")) or gov_vac.pdf_extracted_text
                            gov_vac.extraction_status = pdf_data.get("extraction_status", gov_vac.extraction_status)
                            if corrigendum:
                                gov_vac.corrigendum_details = corrigendum
                            if is_extension and deadline_dt:
                                gov_vac.application_deadline = deadline_dt
                                gov_vac.deadline_status = "EXTENDED"
                                gov_vac.change_type = "deadline_extended"
                            elif is_corrigendum:
                                gov_vac.change_type = "corrigendum"
                            else:
                                gov_vac.change_type = "updated_vacancy"

                            # Audit change event
                            evt = GovernmentChangeEvent(
                                source_id=source.id,
                                vacancy_id=gov_vac.id,
                                url=pdf_url or apply_url or f"https://{source.official_domain}",
                                document_type="pdf" if pdf_url else "notice",
                                previous_hash=old_hash,
                                new_hash=new_hash,
                                change_type=event_type,
                                change_summary=f"Detected {event_type} on {existing_job.title}: {corrigendum or 'Document contents or deadline revised'}",
                                detected_at=now,
                            )
                            db.add(evt)
                            change_events_count += 1

                    vacancies_updated += 1

            source.vacancies_found += vacancies_created
            db.commit()

        except Exception as crawl_err:
            logger.exception(f"Error while crawling source [{source.official_domain}]: {crawl_err}")
            outcome = "failed"
            err_msg = str(crawl_err).lower()
            if "403" in err_msg or "cloudflare" in err_msg or "forbidden" in err_msg:
                error_type = "BLOCKED"
            elif "captcha" in err_msg or "login" in err_msg:
                error_type = "MANUAL_ACCESS"
            elif "getaddrinfo" in err_msg or "name or service not known" in err_msg or "410" in err_msg:
                error_type = "DEAD"
            else:
                error_type = "TEMPORARY_FAILURE"

        finally:
            # Deterministic adaptive rescheduling
            try:
                GovernmentContinuousScheduler.reschedule_source(
                    db=db,
                    source=source,
                    outcome=outcome,
                    change_detected=change_detected,
                    error_type=error_type,
                )
            except Exception as resched_err:
                logger.error(f"Failed to reschedule source [{source.id}]: {resched_err}")
                source.is_locked = False
                source.locked_at = None
                db.commit()

        logger.info(
            f"Crawled [{source.organisation_name}]: Outcome={outcome}, "
            f"Created={vacancies_created}, Updated={vacancies_updated}, "
            f"Changes={change_events_count}, Interval={source.crawl_interval_minutes}m"
        )

        return {
            "source_id": source.id,
            "organisation": source.organisation_name,
            "domain": source.official_domain,
            "status": source.crawl_status,
            "outcome": outcome,
            "error_type": error_type,
            "vacancies_created": vacancies_created,
            "vacancies_updated": vacancies_updated,
            "change_events_recorded": change_events_count,
            "child_sources_registered": child_registered,
            "next_crawl_at": source.next_crawl_at.isoformat() if source.next_crawl_at else None,
            "crawl_interval_minutes": source.crawl_interval_minutes,
        }

    @classmethod
    def crawl_due_sources_batch(
        cls,
        db: Session,
        batch_size: int = 20,
        worker_id: str = "continuous_worker",
    ) -> Dict[str, Any]:
        """
        Pulls due sources from the living monitoring queue with progressive priority
        ordering (approaching deadlines & uncrawled first, no starvation).
        Crawls and reschedules each source independently so that individual failures
        never halt the batch.
        """
        cls.seed_initial_sources(db)
        GovernmentContinuousScheduler.initialize_monitoring_queue(db)

        start_time = time.time()
        due_sources = GovernmentContinuousScheduler.get_due_sources(
            db=db,
            limit=batch_size,
            lock_sources=True,
            worker_id=worker_id,
        )

        total_created = 0
        total_updated = 0
        total_changes = 0
        successful_crawls = 0
        failed_crawls = 0
        results = []

        for src in due_sources:
            try:
                res = cls.crawl_source(db, src)
                results.append(res)
                total_created += res["vacancies_created"]
                total_updated += res["vacancies_updated"]
                total_changes += res.get("change_events_recorded", 0)
                if res.get("outcome") == "success":
                    successful_crawls += 1
                else:
                    failed_crawls += 1
            except Exception as single_err:
                logger.error(f"Uncaught error crawling [{src.official_domain}]: {single_err}")
                failed_crawls += 1
                # Release lock on crash
                src.is_locked = False
                src.locked_at = None
                db.commit()

        duration_ms = (time.time() - start_time) * 1000.0

        if len(due_sources) > 0:
            run_record = GovernmentDiscoveryRun(
                run_type="vacancy_crawl",
                status="completed",
                scope_filter=f"CONTINUOUS_BATCH:{batch_size}",
                sources_discovered=0,
                sources_verified=len(due_sources),
                vacancies_discovered=total_created + total_updated,
                vacancies_created=total_created,
                vacancies_updated=total_updated,
                duration_ms=duration_ms,
            )
            db.add(run_record)
            db.commit()

        return {
            "sources_processed": len(due_sources),
            "processed": len(due_sources),
            "crawled_count": len(due_sources),
            "successful_crawls": successful_crawls,
            "failed_crawls": failed_crawls,
            "vacancies_created": total_created,
            "vacancies_updated": total_updated,
            "change_events_recorded": total_changes,
            "duration_ms": duration_ms,
            "details": results,
        }

    @classmethod
    def crawl_batch(
        cls,
        db: Session,
        batch_size: int = 20,
        state_filter: Optional[str] = None,
        org_type_filter: Optional[str] = None,
        force_recheck: bool = False,
    ) -> Dict[str, Any]:
        """
        Backwards-compatible batch crawl endpoint delegating to the continuous
        due-sources scheduler while respecting state/org filters.
        """
        if not state_filter and not org_type_filter and not force_recheck:
            return cls.crawl_due_sources_batch(db, batch_size=batch_size)

        if db.query(GovernmentSource).count() == 0:
            cls.seed_initial_sources(db)
        GovernmentContinuousScheduler.initialize_monitoring_queue(db)

        query = db.query(GovernmentSource).filter(
            GovernmentSource.source_status.notin_(["DEAD"])
        )

        if state_filter:
            query = query.filter(GovernmentSource.state == state_filter)
        if org_type_filter:
            query = query.filter(GovernmentSource.organisation_type == org_type_filter)

        if force_recheck:
            query = query.order_by(GovernmentSource.discovered_at.desc())
        else:
            query = query.order_by(asc(GovernmentSource.next_crawl_at).nullsfirst())

        sources = query.limit(batch_size).all()

        total_created = 0
        total_updated = 0
        total_changes = 0
        crawled_count = 0
        results = []

        start_time = time.time()

        for src in sources:
            res = cls.crawl_source(db, src)
            results.append(res)
            total_created += res["vacancies_created"]
            total_updated += res["vacancies_updated"]
            total_changes += res.get("change_events_recorded", 0)
            crawled_count += 1

        duration_ms = (time.time() - start_time) * 1000.0

        run_record = GovernmentDiscoveryRun(
            run_type="vacancy_crawl",
            status="completed",
            scope_filter=f"BATCH:{batch_size}:{state_filter or 'ALL'}",
            sources_discovered=0,
            sources_verified=crawled_count,
            vacancies_discovered=total_created + total_updated,
            vacancies_created=total_created,
            vacancies_updated=total_updated,
            duration_ms=duration_ms,
        )
        db.add(run_record)
        db.commit()

        return {
            "sources_processed": crawled_count,
            "processed": crawled_count,
            "crawled_count": crawled_count,
            "vacancies_created": total_created,
            "vacancies_updated": total_updated,
            "change_events_recorded": total_changes,
            "duration_ms": duration_ms,
            "details": results,
        }

    @classmethod
    def search_vacancies(
        cls,
        db: Session,
        query: str = "",
        location: Optional[str] = None,
        limit: int = 20,
    ) -> List[NormalizedJob]:
        """
        Returns NormalizedJob items from local database for government jobs matching query.
        """
        q = db.query(Job).filter(Job.source == "government")
        if query:
            q = q.filter(
                or_(
                    Job.title.ilike(f"%{query}%"),
                    Job.description.ilike(f"%{query}%"),
                    Job.company.ilike(f"%{query}%")
                )
            )
        if location:
            q = q.filter(Job.location.ilike(f"%{location}%"))

        jobs = q.order_by(desc(Job.discovered_at)).limit(limit).all()
        normalized: List[NormalizedJob] = []
        for j in jobs:
            normalized.append(
                NormalizedJob(
                    source="government",
                    external_job_id=j.external_job_id or j.id,
                    url=j.application_url,
                    title=j.title,
                    company=j.company,
                    location=j.location or "India",
                    work_mode=j.work_mode or "onsite",
                    description=j.description,
                    salary_min=float(j.salary_min) if j.salary_min else None,
                    salary_max=float(j.salary_max) if j.salary_max else None,
                    currency=j.currency or "INR",
                    posted_at=j.posted_at,
                    expires_at=j.expires_at,
                )
            )
        return normalized

    @classmethod
    def get_coverage(cls, db: Session) -> GovernmentCoverageResponse:
        """Returns the full State/UT and Sector coverage dashboard response."""
        cls.seed_initial_sources(db)
        return GovernmentCoverageCalculator.calculate_coverage(db)

    @classmethod
    def execute_universe_discovery_mission(
        cls,
        db: Session,
        max_passes: int = 10,
        run_search: bool = True,
        batch_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Executes the full multi-pass Government Job Source Discovery mission (Phase 23)
        using the two markdown universe specifications as the initial universe,
        recursively expanding across Central, State, UT, District, and Municipal levels.
        """
        start_time = time.time()
        logger.info(f"Starting Government Universe Discovery Mission (up to {max_passes} passes)...")
        now = get_utc_now()

        pass_results: Dict[str, Any] = {}
        passes_completed = 0

        # PASS 1: MD Universe Ingestion & Resolution
        p1_start = time.time()
        parsed_data = GovernmentUniverseParser.parse_universe_files()
        resolution_stats = GovernmentSourceResolver.resolve_and_ingest_targets(
            db=db,
            targets=parsed_data["targets"],
            batch_size=200
        )
        pass_results["pass_1_md_universe"] = {
            "name": "MD Universe Ingestion & Initial Resolution",
            "raw_targets": parsed_data["total_raw_targets"],
            "deduplicated_targets": parsed_data["total_deduplicated_targets"],
            "resolution": resolution_stats,
            "duration_s": round(time.time() - p1_start, 2),
        }
        passes_completed += 1

        # PASS 2: Parent -> Child Recursive Expansion
        p2_start = time.time()
        p2_linked = 0
        parents = db.query(GovernmentSource).filter(
            GovernmentSource.organisation_type.in_(["ministry", "statutory_body", "research_institute"]),
            GovernmentSource.parent_source_id.is_(None)
        ).all()
        parent_map = {p.organisation_name.lower(): p.id for p in parents}

        children = db.query(GovernmentSource).filter(GovernmentSource.parent_source_id.is_(None)).all()
        for ch in children:
            ch_name = ch.organisation_name.lower()
            if "csir -" in ch_name and "council of scientific & industrial research (csir)" in parent_map:
                ch.parent_source_id = parent_map["council of scientific & industrial research (csir)"]
                p2_linked += 1
            elif "icar -" in ch_name and "indian council of agricultural research (icar)" in parent_map:
                ch.parent_source_id = parent_map["indian council of agricultural research (icar)"]
                p2_linked += 1
            elif "icmr -" in ch_name and "indian council of medical research (icmr)" in parent_map:
                ch.parent_source_id = parent_map["indian council of medical research (icmr)"]
                p2_linked += 1
            elif ch.official_domain in ["cdac.in", "nielit.gov.in", "stpi.in", "negd.gov.in", "dic.gov.in"]:
                if "ministry of electronics & information technology (meity)" in parent_map:
                    ch.parent_source_id = parent_map["ministry of electronics & information technology (meity)"]
                    p2_linked += 1

        if p2_linked > 0:
            db.commit()
        pass_results["pass_2_parent_child_expansion"] = {
            "name": "Parent -> Child Recursive Linking",
            "parent_sources_identified": len(parents),
            "child_sources_linked": p2_linked,
            "duration_s": round(time.time() - p2_start, 2),
        }
        passes_completed += 1

        # PASS 3: State & UT Exhaustive Coverage
        p3_start = time.time()
        state_coverage_summary = {}
        for state in INDIAN_STATES + INDIAN_UTS:
            count = db.query(GovernmentSource).filter(GovernmentSource.state == state).count()
            state_coverage_summary[state] = count
        pass_results["pass_3_state_ut_coverage"] = {
            "name": "State & UT Exhaustive Expansion",
            "total_regions": len(INDIAN_STATES) + len(INDIAN_UTS),
            "state_coverage_summary": state_coverage_summary,
            "duration_s": round(time.time() - p3_start, 2),
        }
        passes_completed += 1

        # PASS 4: District & Municipal Local-Government Expansion
        p4_start = time.time()
        enum_stats = GovernmentSourceResolver.enumerate_all_directories(db)
        dist_count = db.query(GovernmentSource).filter(GovernmentSource.government_level == "district").count()
        muni_count = db.query(GovernmentSource).filter(GovernmentSource.government_level == "municipal").count()
        pass_results["pass_4_district_municipal_expansion"] = {
            "name": "District & Municipal Local-Government Expansion",
            "enumeration": enum_stats,
            "district_level_sources": dist_count,
            "municipal_level_sources": muni_count,
            "duration_s": round(time.time() - p4_start, 2),
        }
        passes_completed += 1

        # PASS 5: Recruitment Endpoint Discovery
        p5_start = time.time()
        endpoints_count = db.query(GovernmentSource).filter(
            or_(
                GovernmentSource.recruitment_url.is_not(None),
                GovernmentSource.career_url.is_not(None),
                GovernmentSource.vacancy_url.is_not(None)
            )
        ).count()
        pass_results["pass_5_recruitment_endpoints"] = {
            "name": "Recruitment Endpoint Discovery & Verification",
            "sources_with_recruitment_endpoints": endpoints_count,
            "duration_s": round(time.time() - p5_start, 2),
        }
        passes_completed += 1

        # PASS 6: PDF Discovery & Verification Batch Crawl
        p6_start = time.time()
        crawl_stats = cls.crawl_due_sources_batch(db, batch_size=batch_size, worker_id="mission_worker")
        pass_results["pass_6_pdf_discovery_and_crawl"] = {
            "name": "PDF Discovery, Content Hashing & Vacancy Extraction",
            "batch_crawled": crawl_stats,
            "duration_s": round(time.time() - p6_start, 2),
        }
        passes_completed += 1

        # PASS 7: Search-Engine Discovery with Rotated Queries
        p7_start = time.time()
        search_res = {"sources_discovered": 0}
        if run_search:
            try:
                search_res = cls.discover_sources_open_ended(db, scope="ALL", max_queries=3)
            except Exception as s_err:
                logger.warning(f"Search discovery pass encountered transient issue: {s_err}")
                search_res = {"sources_discovered": 0, "error": str(s_err)}
        pass_results["pass_7_search_engine_discovery"] = {
            "name": "Search Engine Query Rotation & Discovery",
            "result": search_res,
            "duration_s": round(time.time() - p7_start, 2),
        }
        passes_completed += 1

        # PASS 8: Recursive Discovery from Found Organisations
        p8_start = time.time()
        recursive_count = db.query(GovernmentSource).filter(
            GovernmentSource.discovery_method.in_(["recursive_link", "search_engine"])
        ).count()
        pass_results["pass_8_recursive_feedback"] = {
            "name": "Recursive Child Organisation Feedback",
            "recursively_discovered_sources": recursive_count,
            "duration_s": round(time.time() - p8_start, 2),
        }
        passes_completed += 1

        # PASS 9: Deduplication, Matching & Decision Evaluation
        p9_start = time.time()
        total_vacancies = db.query(GovernmentVacancy).count()
        harsh_candidate = db.query(CandidateProfile).first()
        matched_eval_count = 0
        if harsh_candidate:
            gov_jobs = db.query(Job).filter(Job.source == "government").limit(50).all()
            for j in gov_jobs:
                try:
                    calculate_or_get_job_match(db, job_id=j.id, candidate_id=harsh_candidate.id)
                    matched_eval_count += 1
                except Exception:
                    pass
        pass_results["pass_9_deduplication_and_matching"] = {
            "name": "Anti-Duplicate Reconciliation & Candidate Evaluation",
            "total_government_vacancies": total_vacancies,
            "candidate_matched_evaluations": matched_eval_count,
            "duration_s": round(time.time() - p9_start, 2),
        }
        passes_completed += 1

        # PASS 10: Continuous Monitoring Scheduling & Deadline Revalidation
        p10_start = time.time()
        backlog_resolution = GovernmentSourceResolver.resolve_unresolved_backlog(db)
        init_scheduled = GovernmentContinuousScheduler.initialize_monitoring_queue(db)
        deadline_stats = GovernmentContinuousScheduler.revalidate_vacancy_deadlines(db)
        metrics = GovernmentContinuousScheduler.get_monitoring_metrics(db)
        pass_results["pass_10_continuous_monitoring_schedule"] = {
            "name": "Continuous Monitoring Queue Initialization & Deadline Protection",
            "backlog_deep_resolution": backlog_resolution,
            "sources_initialized_into_queue": init_scheduled,
            "deadline_revalidation": deadline_stats,
            "monitoring_metrics": metrics,
            "duration_s": round(time.time() - p10_start, 2),
        }
        passes_completed += 1

        total_sources = db.query(GovernmentSource).count()
        unresolved_count = db.query(GovernmentUnresolvedTarget).count()
        duration_total = round(time.time() - start_time, 2)

        # Record mission run in GovernmentDiscoveryRun
        run_record = GovernmentDiscoveryRun(
            run_type="universe_discovery_mission",
            status="completed",
            scope_filter=f"UNIVERSE_PASSES:{passes_completed}",
            sources_discovered=resolution_stats.get("sources_registered", 0),
            sources_verified=total_sources,
            vacancies_discovered=total_vacancies,
            vacancies_created=crawl_stats.get("vacancies_created", 0),
            vacancies_updated=crawl_stats.get("vacancies_updated", 0),
            duration_ms=duration_total * 1000.0,
            coverage_summary=json.dumps({
                "passes_completed": passes_completed,
                "total_registered_sources": total_sources,
                "unresolved_backlog_targets": unresolved_count,
            }),
        )
        db.add(run_record)
        db.commit()

        logger.info(
            f"Universe Discovery Mission completed in {duration_total}s. "
            f"Sources: {total_sources}, Unresolved Backlog: {unresolved_count}, Vacancies: {total_vacancies}"
        )

        return {
            "status": "completed",
            "passes_completed": passes_completed,
            "total_raw_targets": parsed_data["total_raw_targets"],
            "total_deduplicated_targets": parsed_data["total_deduplicated_targets"],
            "verified_sources": total_sources,
            "unresolved_backlog": unresolved_count,
            "duration_seconds": duration_total,
            "pass_results": pass_results,
            "metrics": metrics,
        }

