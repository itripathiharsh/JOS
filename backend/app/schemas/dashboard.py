from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    jobs_discovered: int
    relevant_jobs: int
    strong_matches: int
    applications: int
    needs_attention: int
