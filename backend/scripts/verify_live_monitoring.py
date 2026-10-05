import os
import sys
import json
from datetime import datetime, timezone, timedelta

# Ensure backend path and root path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

from app.db.session import SessionLocal
from app.models.government import (
    GovernmentSource,
    GovernmentVacancy,
    GovernmentChangeEvent,
    GovernmentDiscoveryRun,
)
from app.services.government.scheduler import GovernmentContinuousScheduler, get_utc_now
from app.services.government.engine import GovernmentDiscoveryEngine


def run_live_verification():
    db = SessionLocal()
    try:
        print("=== 1. INITIALIZING / ENSURING FULL REGISTRY SCHEDULING ===")
        init_count = GovernmentContinuousScheduler.initialize_monitoring_queue(db)
        print(f"Initialized {init_count} sources into living monitoring queue.")

        print("\n=== 2. DEADLINE REVALIDATION TICK ===")
        deadline_stats = GovernmentContinuousScheduler.revalidate_vacancy_deadlines(db)
        print(f"Deadline stats: {deadline_stats}")

        print("\n=== 3. CRAWL DUE SOURCES BATCH (REAL SOURCES) ===")
        # Crawl a small batch of due sources to exercise live crawl, hashing & rescheduling
        batch_res = GovernmentDiscoveryEngine.crawl_due_sources_batch(
            db=db,
            batch_size=3,
            worker_id="live_verification_worker"
        )
        print(f"Crawled batch: processed={batch_res.get('sources_processed')}, successful={batch_res.get('successful_crawls')}, failed={batch_res.get('failed_crawls')}, vacancies_created={batch_res.get('vacancies_created')}, vacancies_updated={batch_res.get('vacancies_updated')}")

        print("\n=== 4. LIVE METRICS TELEMETRY ===")
        metrics = GovernmentContinuousScheduler.get_monitoring_metrics(db)
        print(json.dumps(metrics, indent=2, default=str))

        print("\n=== 5. SAMPLE SCHEDULED SOURCES ===")
        sources = db.query(GovernmentSource).order_by(GovernmentSource.next_crawl_at.asc()).limit(5).all()
        for s in sources:
            print(f"- {s.official_domain}: interval={s.crawl_interval_minutes}m, next_crawl={s.next_crawl_at}, last_crawled={s.last_crawled_at}, status={s.source_status}, failures={s.consecutive_failures}")

        print("\n=== 6. RECENT CHANGE EVENTS ===")
        changes = db.query(GovernmentChangeEvent).order_by(GovernmentChangeEvent.detected_at.desc()).limit(5).all()
        print(f"Total Change Events: {len(changes)}")
        for ch in changes:
            print(f"- [{ch.change_type}] {ch.url}: {ch.change_summary} ({ch.detected_at})")

    finally:
        db.close()

if __name__ == "__main__":
    run_live_verification()
