"""
Job Operating System - Autonomous Background Scheduler Daemon
₹0, 100% Local, Step 12 Controlled Autonomy.
Conservative Scheduling: Enqueues bounded tasks into PostgreSQL queue; NEVER executes tasks directly.
"""
import sys
import os
import time
import signal
import logging
from pathlib import Path

# Setup paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal, check_db_connection
from app.services.automation.scheduler_service import AutomationSchedulerService

setup_logging("scheduler.log")
logger = logging.getLogger("scheduler_daemon")

_stop_requested = False


def _signal_handler(signum, frame):
    global _stop_requested
    sig_name = "SIGINT (Ctrl+C)" if signum == signal.SIGINT else f"Signal {signum}"
    logger.info(f"Scheduler received {sig_name}. Initiating graceful shutdown...")
    _stop_requested = True


def run_scheduler_loop(
    interval: float = None,
    candidate_id: str = None,
    run_once: bool = False
):
    global _stop_requested
    interval = interval or settings.SCHEDULER_INTERVAL_SECONDS

    # Register OS signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info(
        f"Starting Scheduler Daemon | "
        f"Evaluation Interval: {interval}s | "
        f"Default Discovery: every {settings.SCHEDULER_DEFAULT_DISCOVERY_INTERVAL_HOURS}h | "
        f"DB: {settings.DATABASE_URL.split('@')[-1]}"
    )

    if not check_db_connection():
        logger.error("Initial database connectivity check failed. Scheduler cannot start.")
        sys.exit(1)

    consecutive_errors = 0

    while not _stop_requested:
        db = SessionLocal()
        try:
            result = AutomationSchedulerService.run_scheduler_tick(
                db=db,
                candidate_id=candidate_id
            )

            consecutive_errors = 0

            if result.enqueued_count > 0:
                types_str = ", ".join(result.task_types_enqueued) if result.task_types_enqueued else "various"
                logger.info(
                    f"Scheduler Tick: Enqueued {result.enqueued_count} task(s) "
                    f"({types_str}). Skipped {result.skipped_count} existing."
                )

            if run_once:
                logger.info("Scheduler single cycle (--once) completed.")
                break

            step = 1.0
            elapsed = 0.0
            while elapsed < interval and not _stop_requested:
                time.sleep(step)
                elapsed += step

        except Exception as e:
            consecutive_errors += 1
            backoff = min(60, 2 ** min(consecutive_errors, 6))
            logger.exception(f"Scheduler iteration encountered an exception: {e}. Backing off {backoff}s...")
            time.sleep(backoff)
        finally:
            db.close()

    logger.info("Scheduler Daemon shut down gracefully.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Job Operating System Scheduler Daemon.")
    parser.add_argument("--interval", type=float, default=None, help="Evaluation interval in seconds.")
    parser.add_argument("--candidate-id", type=str, default=None, help="Specific candidate profile ID.")
    parser.add_argument("--once", action="store_true", help="Execute single cycle and exit.")
    args = parser.parse_args()

    run_scheduler_loop(
        interval=args.interval,
        candidate_id=args.candidate_id,
        run_once=args.once
    )
