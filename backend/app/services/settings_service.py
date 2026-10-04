import re
from app.core.config import settings
from app.db.session import check_db_connection
from app.schemas.settings import SettingsResponse


def mask_database_url(url: str) -> str:
    """Mask password in database URL for safe exposure."""
    return re.sub(r':([^@]+)@', ':****@', url)


def get_system_settings() -> SettingsResponse:
    db_ok = check_db_connection()
    masked_url = mask_database_url(settings.DATABASE_URL)

    return SettingsResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        app_env=settings.APP_ENV,
        database_connected=db_ok,
        database_url_masked=masked_url,
        storage_path=settings.STORAGE_DIR,
        log_level=settings.LOG_LEVEL,
        automation_status={
            "job_scraping": "Disabled (Phase 1 Foundation)",
            "ai_matching": "Disabled (Phase 1 Foundation)",
            "auto_apply": "Disabled (Phase 1 Foundation)",
            "browser_agent": "Disabled (Phase 1 Foundation)",
        }
    )
