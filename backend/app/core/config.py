import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine workspace root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "Job Operating System"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "local_production"  # development | local_production | test
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "job_agent_local_prod_secret_key_f_drive_2026"

    # Server Binding
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"

    # Database Configuration (PostgreSQL 100% Local)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://job_agent_user@localhost:5432/job_agent_db"
    )
    TEST_DATABASE_URL: str = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres@localhost:5432/job_agent_test_db"
    )

    # Storage & Cache Directories (Mandatory F: Drive)
    WORKSPACE_ROOT: str = str(ROOT_DIR)
    STORAGE_DIR: str = str(ROOT_DIR / "storage")
    DOCUMENTS_DIR: str = str(ROOT_DIR / "storage" / "documents")
    LOG_DIR: str = str(ROOT_DIR / "logs")
    TMP_DIR: str = str(ROOT_DIR / "tmp")
    CACHE_DIR: str = str(ROOT_DIR / ".cache")

    # Playwright & Browser Automation Configuration
    PLAYWRIGHT_BROWSERS_PATH: str = str(ROOT_DIR / ".cache" / "ms-playwright")
    PLAYWRIGHT_HEADLESS: bool = True
    BROWSER_DATA_DIR: str = str(ROOT_DIR / "storage" / "browser_sessions")
    BROWSER_TIMEOUT_MS: int = 30000

    # Controlled Worker Configuration (Step 12 Invariants)
    WORKER_POLL_INTERVAL_SECONDS: int = 5
    WORKER_MAX_BATCH_SIZE: int = 5
    WORKER_LEASE_TIMEOUT_SECONDS: int = 300

    # Controlled Scheduler Configuration (Step 12 Conservative Generation)
    SCHEDULER_INTERVAL_SECONDS: int = 60
    SCHEDULER_DEFAULT_DISCOVERY_INTERVAL_HOURS: int = 6
    SCHEDULER_STALE_JOB_THRESHOLD_DAYS: int = 30

    model_config = SettingsConfigDict(
        env_file=(
            os.getenv("ENV_FILE") or
            str(ROOT_DIR / ".env") if (ROOT_DIR / ".env").exists() else
            str(BACKEND_DIR / ".env")
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
