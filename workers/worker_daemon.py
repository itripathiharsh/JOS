"""
Job Operating System - Autonomous Background Worker Daemon
₹0, 100% Local, Step 12 Controlled Autonomy.
Strict Safety: APPLICATION != SUBMISSION. Real submission is approval-gated.
"""
import sys
import os
import time
import signal
import uuid
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
from app.services.automation.worker_service import AutomationWorkerService

setup_logging("worker.log")
logger = logging.getLogger("worker_daemon")

_stop_requested = False


def _signal_handler(signum, frame):
    global _stop_requested
    sig_name = "SIGINT (Ctrl+C)" if signum == signal.SIGINT else f"Signal {signum}"
    logger.info(f"Worker received {sig_name}. Initiating graceful shutdown...")
    _stop_requested = True


def run_worker_loop(
    poll_interval: float = None,
    max_batch_size: int = None,
    run_once: bool = False,
    worker_id: str = None
):
    global _stop_requested
    poll_interval = poll_interval or settings.WORKER_POLL_INTERVAL_SECONDS
    max_batch_size = max_batch_size or settings.WORKER_MAX_BATCH_SIZE
    w_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"

    # Register OS signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info(
        f"Starting Worker Daemon [{w_id}] | "
        f"Poll Interval: {poll_interval}s | "
        f"Batch Size: {max_batch_size} | "
        f"DB: {settings.DATABASE_URL.split('@')[-1]}"
    )

    if not check_db_connection():
        logger.error("Initial database connectivity check failed. Worker cannot start.")
        sys.exit(1)

    consecutive_errors = 0

    while not _stop_requested:
        db = SessionLocal()
        try:
            result = AutomationWorkerService.run_worker_tick(
                db=db,
                worker_id=w_id,
                max_tasks=max_batch_size,
            )

            consecutive_errors = 0

            if result.claimed_count > 0 or result.recovered_count > 0:
                logger.info(
                    f"Worker Tick [{w_id}]: "
                    f"Claimed={result.claimed_count}, "
                    f"Succeeded={result.succeeded_count}, "
                    f"Failed={result.failed_count}, "
                    f"Blocked={result.blocked_count}, "
                    f"Recovered={result.recovered_count}"
                )

            if run_once:
                logger.info("Worker single tick (--once) completed.")
                break

            # If work was processed, poll quickly for the next batch; otherwise sleep full interval
            sleep_time = 0.5 if result.claimed_count >= max_batch_size else poll_interval
            step = 0.25
            elapsed = 0.0
            while elapsed < sleep_time and not _stop_requested:
                time.sleep(step)
                elapsed += step

        except Exception as e:
            consecutive_errors += 1
            backoff = min(30, 2 ** min(consecutive_errors, 5))
            logger.exception(f"Worker iteration encountered an exception: {e}. Backing off {backoff}s...")
            time.sleep(backoff)
        finally:
            db.close()

    logger.info(f"Worker Daemon [{w_id}] shut down gracefully. Active leases protected.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Job Operating System Worker Daemon.")
    parser.add_argument("--interval", type=float, default=None, help="Polling interval in seconds.")
    parser.add_argument("--batch-size", type=int, default=None, help="Max tasks claimed per tick.")
    parser.add_argument("--once", action="store_true", help="Execute single tick and exit.")
    parser.add_argument("--id", type=str, default=None, help="Custom worker ID.")
    args = parser.parse_args()

    run_worker_loop(
        poll_interval=args.interval,
        max_batch_size=args.batch_size,
        run_once=args.once,
        worker_id=args.id
    )
