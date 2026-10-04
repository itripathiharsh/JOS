from pydantic import BaseModel
from typing import Dict, Any


class SettingsResponse(BaseModel):
    app_name: str
    app_version: str
    app_env: str
    database_connected: bool
    database_url_masked: str
    storage_path: str
    log_level: str
    automation_status: Dict[str, Any]
