from fastapi import APIRouter
from app.schemas.health import HealthResponse
from app.db.session import check_db_connection
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    db_connected = check_db_connection()
    return HealthResponse(
        status="ok",
        database="connected" if db_connected else "disconnected",
        environment=settings.APP_ENV,
        version=settings.APP_VERSION
    )
