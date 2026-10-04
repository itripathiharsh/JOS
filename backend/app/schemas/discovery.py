from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


PriorityLevel = Literal["HIGH", "MEDIUM", "LOW"]


class RoleAliasDefinition(BaseModel):
    """Configuration definition for a single role alias / search synonym."""
    canonical_role: str = Field(..., description="Root canonical role name, e.g. 'AI Engineer'")
    alias: str = Field(..., description="Expanded role title or search synonym")
    priority: PriorityLevel = Field("MEDIUM", description="Query execution priority")
    strategy: str = Field("synonym", description="Strategy category: canonical, synonym, specialization, variant, acronym")
    reason: str = Field("", description="Justification for this specific alias")
    enabled: bool = Field(True, description="Whether this alias is active for query generation")


class SearchStrategyQuery(BaseModel):
    """A generated, normalized search query strategy ready for execution."""
    query: str = Field(..., description="Exact query string to submit to source")
    canonical_role: str = Field(..., description="Root candidate target role this query originated from")
    strategy: str = Field(..., description="Generation strategy: canonical_role, role_alias, work_mode_modifier, location_modifier, tech_modifier")
    priority: PriorityLevel = Field("MEDIUM", description="Execution priority rank")
    reason: str = Field(..., description="Architectural reasoning explaining why this query exists")
    location_filter: Optional[str] = Field(None, description="Optional location filter if supported by source")
    remote_filter: Optional[bool] = Field(None, description="Optional remote work filter if supported by source")
    limit: int = Field(20, description="Max jobs to request for this query")


class DiscoveryConfig(BaseModel):
    """Bounded configuration controlling discovery run limits and strategy toggles."""
    max_total_queries: int = Field(20, ge=1, le=50, description="Hard cap on total queries executed in one discovery run")
    max_queries_per_role: int = Field(5, ge=1, le=10, description="Max queries generated for any single canonical role")
    max_tech_modifiers: int = Field(3, ge=0, le=5, description="Max technology-modified queries generated")
    max_location_modifiers: int = Field(2, ge=0, le=5, description="Max location-modified queries generated")
    include_aliases: bool = Field(True, description="Whether to expand roles into synonyms / aliases")
    include_work_mode_modifiers: bool = Field(True, description="Whether to generate work mode variants (e.g. Remote)")
    include_location_modifiers: bool = Field(True, description="Whether to generate location variants (e.g. India)")
    include_tech_modifiers: bool = Field(True, description="Whether to generate tech skill variants (e.g. Python, PyTorch)")
    min_priority: PriorityLevel = Field("LOW", description="Lowest priority level to include: HIGH, MEDIUM, LOW")


class DiscoveryPreviewResponse(BaseModel):
    """Preview of generated search strategies without performing network ingestion."""
    candidate_id: Optional[str] = None
    candidate_name: str
    target_roles: List[str]
    total_strategies: int
    priority_breakdown: Dict[str, int]
    queries: List[SearchStrategyQuery]


class DiscoveryRunRequest(BaseModel):
    """Payload to trigger a discovery run."""
    source: str = Field("remotive", description="Target job source identifier")
    config: Optional[DiscoveryConfig] = Field(default_factory=DiscoveryConfig)
    dry_run: bool = Field(False, description="If True, only previews generated queries without making live requests")


class DiscoveryQueryExecution(BaseModel):
    """Telemetry record for an individual query executed during a discovery run."""
    query: str
    canonical_role: str
    strategy: str
    priority: str
    status: str  # completed, failed
    jobs_fetched: int = 0
    jobs_created: int = 0
    jobs_updated: int = 0
    jobs_skipped: int = 0
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class DiscoveryRunSummary(BaseModel):
    """Comprehensive summary of a completed or in-progress discovery run."""
    id: str
    source: str
    status: str  # in_progress, completed, failed
    queries_generated: int
    queries_executed: int
    successful_queries: int
    failed_queries: int
    jobs_fetched: int
    jobs_created: int
    jobs_updated: int
    jobs_skipped: int
    duration_ms: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    executed_queries: List[DiscoveryQueryExecution] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DiscoveryRunListResponse(BaseModel):
    items: List[DiscoveryRunSummary]
    total: int
