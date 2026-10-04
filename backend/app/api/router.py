from fastapi import APIRouter
from app.api.routes import health, dashboard, profile, jobs, applications, settings, matching, discovery, decisions, memory, automation

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(dashboard.router, tags=["Dashboard"])
api_router.include_router(profile.router, tags=["Profile"])
api_router.include_router(jobs.router, tags=["Jobs"])
api_router.include_router(discovery.router, tags=["Discovery"])
api_router.include_router(matching.router, tags=["Matching"])
api_router.include_router(decisions.router, tags=["Decisions"])
api_router.include_router(applications.router, tags=["Applications"])
api_router.include_router(memory.router, tags=["Memory & Feedback"])
api_router.include_router(automation.router, tags=["Automation & Scheduler"])
api_router.include_router(settings.router, tags=["Settings"])


