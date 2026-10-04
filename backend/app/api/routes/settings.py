from fastapi import APIRouter
from app.schemas.settings import SettingsResponse
from app.services.settings_service import get_system_settings

router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
def get_settings():
    return get_system_settings()
