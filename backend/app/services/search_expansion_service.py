import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from connectors.models import SourceCapabilities
from app.schemas.discovery import (
    RoleAliasDefinition,
    SearchStrategyQuery,
    DiscoveryConfig,
    PriorityLevel,
)

logger = logging.getLogger(__name__)

# Curated, justified role synonyms and specializations.
# Every alias has an explicit architectural reason to prevent arbitrary query bloat.
DEFAULT_ROLE_ALIASES: Dict[str, List[RoleAliasDefinition]] = {
    "AI Engineer": [
        RoleAliasDefinition(canonical_role="AI Engineer", alias="AI Engineer", priority="HIGH", strategy="canonical_role", reason="Direct target role"),
        RoleAliasDefinition(canonical_role="AI Engineer", alias="Artificial Intelligence Engineer", priority="HIGH", strategy="role_alias", reason="Full wording title equivalent"),
        RoleAliasDefinition(canonical_role="AI Engineer", alias="Applied AI Engineer", priority="MEDIUM", strategy="role_alias", reason="Applied production AI engineering title"),
        RoleAliasDefinition(canonical_role="AI Engineer", alias="AI Developer", priority="MEDIUM", strategy="role_alias", reason="Standard industry title variation"),
        RoleAliasDefinition(canonical_role="AI Engineer", alias="Machine Learning Engineer", priority="HIGH", strategy="role_alias", reason="Direct overlapping core discipline"),
    ],
    "ML Engineer": [
        RoleAliasDefinition(canonical_role="ML Engineer", alias="ML Engineer", priority="HIGH", strategy="canonical_role", reason="Direct target role"),
        RoleAliasDefinition(canonical_role="ML Engineer", alias="Machine Learning Engineer", priority="HIGH", strategy="role_alias", reason="Unabbreviated core title"),
        RoleAliasDefinition(canonical_role="ML Engineer", alias="MLOps Engineer", priority="MEDIUM", strategy="role_alias", reason="Operational machine learning systems"),
        RoleAliasDefinition(canonical_role="ML Engineer", alias="Deep Learning Engineer", priority="MEDIUM", strategy="role_alias", reason="Neural network engineering specialization"),
    ],
    "Backend Engineer": [
        RoleAliasDefinition(canonical_role="Backend Engineer", alias="Backend Engineer", priority="HIGH", strategy="canonical_role", reason="Direct target role"),
        RoleAliasDefinition(canonical_role="Backend Engineer", alias="Backend Developer", priority="HIGH", strategy="role_alias", reason="Common developer title variant"),
        RoleAliasDefinition(canonical_role="Backend Engineer", alias="Python Backend Engineer", priority="MEDIUM", strategy="role_alias", reason="Candidate primary language alignment"),
        RoleAliasDefinition(canonical_role="Backend Engineer", alias="Software Engineer Backend", priority="MEDIUM", strategy="role_alias", reason="Corporate title inversion"),
    ],
    "Forward Deployed Engineer (FDE)": [
        RoleAliasDefinition(canonical_role="Forward Deployed Engineer", alias="Forward Deployed Engineer", priority="HIGH", strategy="canonical_role", reason="Direct target role"),
        RoleAliasDefinition(canonical_role="Forward Deployed Engineer", alias="Forward-Deployed Engineer", priority="HIGH", strategy="role_alias", reason="Hyphenated title variant"),
        RoleAliasDefinition(canonical_role="Forward Deployed Engineer", alias="FDE", priority="MEDIUM", strategy="role_alias", reason="Standard industry abbreviation"),
        RoleAliasDefinition(canonical_role="Forward Deployed Engineer", alias="Deployment Engineer", priority="LOW", strategy="role_alias", reason="Broader deployment engineering title"),
    ],
    "Forward Deployed Engineer": [
        RoleAliasDefinition(canonical_role="Forward Deployed Engineer", alias="Forward Deployed Engineer", priority="HIGH", strategy="canonical_role", reason="Direct target role"),
        RoleAliasDefinition(canonical_role="Forward Deployed Engineer", alias="Forward-Deployed Engineer", priority="HIGH", strategy="role_alias", reason="Hyphenated title variant"),
        RoleAliasDefinition(canonical_role="Forward Deployed Engineer", alias="FDE", priority="MEDIUM", strategy="role_alias", reason="Standard industry abbreviation"),
        RoleAliasDefinition(canonical_role="Forward Deployed Engineer", alias="Deployment Engineer", priority="LOW", strategy="role_alias", reason="Broader deployment engineering title"),
    ],
    "Technical Consultant": [
        RoleAliasDefinition(canonical_role="Technical Consultant", alias="Technical Consultant", priority="MEDIUM", strategy="canonical_role", reason="Direct target role"),
        RoleAliasDefinition(canonical_role="Technical Consultant", alias="Technology Consultant", priority="MEDIUM", strategy="role_alias", reason="Synonymous phrasing"),
        RoleAliasDefinition(canonical_role="Technical Consultant", alias="Solutions Consultant", priority="MEDIUM", strategy="role_alias", reason="Client-facing solution consulting"),
        RoleAliasDefinition(canonical_role="Technical Consultant", alias="Technical Solutions Consultant", priority="MEDIUM", strategy="role_alias", reason="Compound client architecture role"),
    ],
}

# High-value discovery technology keywords.
# Candidate skills are intersected with this curated set so we only generate tech-modified queries
# for skills that are genuinely meaningful in job search queries (avoiding obscure libraries).
HIGH_VALUE_SEARCH_TECHNOLOGIES = {
    "python",
    "pytorch",
    "tensorflow",
    "fastapi",
    "sql",
    "postgresql",
    "llm",
    "rag",
    "transformers",
    "docker",
    "kubernetes",
    "deep learning",
    "machine learning",
    "nlp",
}

PRIORITY_RANK: Dict[PriorityLevel, int] = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
}


def normalize_query_string(query: str) -> str:
    """Normalize query for deduplication (case-insensitive, whitespace-collapsed)."""
    if not query:
        return ""
    # Collapse multiple whitespace characters into single space and lowercase
    cleaned = re.sub(r'\s+', ' ', query.strip().lower())
    return cleaned


def clean_location_string(location: str) -> Optional[str]:
    """Clean candidate preferred location phrases into concise search terms."""
    if not location or not location.strip():
        return None
    loc = location.strip()
    loc_lower = loc.lower()

    if "anywhere in india" in loc_lower or loc_lower == "india":
        return "India"
    if "remote" in loc_lower:
        return "Remote"
    if "uttar pradesh" in loc_lower or "up" == loc_lower:
        return "Uttar Pradesh"
    if "lucknow" in loc_lower:
        return "Lucknow"
    return loc


class SearchStrategyEngine:
    """
    Controlled discovery strategy and query expansion engine.
    Transforms candidate preferences into an orderly, bounded, deduplicated list of search queries.
    """

    def __init__(self, role_aliases: Optional[Dict[str, List[RoleAliasDefinition]]] = None):
        self.role_aliases = role_aliases or DEFAULT_ROLE_ALIASES

    def generate_strategies(
        self,
        target_roles: List[str],
        preferred_locations: Optional[List[str]] = None,
        work_modes: Optional[List[str]] = None,
        candidate_skills: Optional[List[str]] = None,
        capabilities: Optional[SourceCapabilities] = None,
        config: Optional[DiscoveryConfig] = None,
    ) -> List[SearchStrategyQuery]:
        """
        Generate a prioritized, bounded, deduplicated list of search queries.
        """
        cfg = config or DiscoveryConfig()
        caps = capabilities or SourceCapabilities()
        preferred_locations = preferred_locations or []
        work_modes = work_modes or []
        candidate_skills = candidate_skills or []

        # 1. Fallback if no target roles provided
        if not target_roles:
            target_roles = ["AI Engineer", "Backend Engineer"]

        # 2. Extract high-signal technology modifiers present in candidate profile
        candidate_tech_keywords: List[str] = []
        for s in candidate_skills:
            clean_s = s.strip()
            if clean_s.lower() in HIGH_VALUE_SEARCH_TECHNOLOGIES:
                if clean_s.capitalize() not in candidate_tech_keywords:
                    candidate_tech_keywords.append(clean_s)

        # 3. Clean location modifiers
        cleaned_locations: List[str] = []
        for loc in preferred_locations:
            clean_loc = clean_location_string(loc)
            if clean_loc and clean_loc not in cleaned_locations and clean_loc != "Remote":
                cleaned_locations.append(clean_loc)

        # 4. Check if remote is desired
        is_remote_desired = any("remote" in wm.lower() for wm in work_modes) or any("remote" in loc.lower() for loc in preferred_locations)

        generated_queries: List[SearchStrategyQuery] = []
        seen_normalized: Set[str] = set()

        def try_add_query(query_candidate: SearchStrategyQuery, role_query_count: int) -> bool:
            """Validate, deduplicate, and record a candidate query."""
            if role_query_count >= cfg.max_queries_per_role:
                return False

            norm_key = normalize_query_string(query_candidate.query)
            if not norm_key or norm_key in seen_normalized:
                return False

            # Check min priority filter
            cand_rank = PRIORITY_RANK.get(query_candidate.priority, 2)
            min_rank = PRIORITY_RANK.get(cfg.min_priority, 2)
            if cand_rank > min_rank:
                return False

            seen_normalized.add(norm_key)
            generated_queries.append(query_candidate)
            return True

        tech_modifier_count = 0
        location_modifier_count = 0

        # 5. Generate queries per target role
        for target_role in target_roles:
            role_clean = target_role.strip()
            role_queries_count = 0

            # Match role in alias registry (handles exact matches or substring matches like "Forward Deployed Engineer (FDE)")
            definitions = self._resolve_role_definitions(role_clean)
            canonical_name = definitions[0].canonical_role if definitions else role_clean

            # a. Add Canonical Role Query (HIGH priority)
            canonical_q = SearchStrategyQuery(
                query=canonical_name,
                canonical_role=canonical_name,
                strategy="canonical_role",
                priority="HIGH",
                reason=f"Primary canonical search for candidate target role '{canonical_name}'",
                remote_filter=True if is_remote_desired else None,
                limit=caps.max_limit,
            )
            if try_add_query(canonical_q, role_queries_count):
                role_queries_count += 1

            # b. Add Work Mode Modifier ("{role} Remote") directly modifying canonical role
            if cfg.include_work_mode_modifiers and is_remote_desired:
                remote_query_str = f"{canonical_name} Remote"
                remote_q = SearchStrategyQuery(
                    query=remote_query_str,
                    canonical_role=canonical_name,
                    strategy="work_mode_modifier",
                    priority="HIGH" if canonical_name in ["AI Engineer", "Backend Engineer"] else "MEDIUM",
                    reason="Explicit remote work modifier query variant",
                    remote_filter=True,
                    limit=caps.max_limit,
                )
                if try_add_query(remote_q, role_queries_count):
                    role_queries_count += 1

            # c. Add Role Aliases & Synonyms
            if cfg.include_aliases and definitions:
                for defn in definitions:
                    if not defn.enabled or defn.alias.lower() == canonical_name.lower():
                        continue
                    alias_q = SearchStrategyQuery(
                        query=defn.alias,
                        canonical_role=canonical_name,
                        strategy=defn.strategy,
                        priority=defn.priority,
                        reason=f"Synonym search: {defn.reason}",
                        remote_filter=True if is_remote_desired else None,
                        limit=caps.max_limit,
                    )
                    if try_add_query(alias_q, role_queries_count):
                        role_queries_count += 1
                        if role_queries_count >= cfg.max_queries_per_role:
                            break

            # d. Add Technology Modifiers ("{role} {tech}")
            if cfg.include_tech_modifiers and tech_modifier_count < cfg.max_tech_modifiers:
                # Select the most suitable technology for this role
                relevant_tech = self._pick_relevant_tech_for_role(canonical_name, candidate_tech_keywords)
                for tech in relevant_tech:
                    if tech_modifier_count >= cfg.max_tech_modifiers or role_queries_count >= cfg.max_queries_per_role:
                        break
                    tech_query_str = f"{canonical_name} {tech}"
                    tech_q = SearchStrategyQuery(
                        query=tech_query_str,
                        canonical_role=canonical_name,
                        strategy="tech_modifier",
                        priority="MEDIUM",
                        reason=f"High-signal technology specialization '{tech}' verified in candidate profile",
                        remote_filter=True if is_remote_desired else None,
                        limit=caps.max_limit,
                    )
                    if try_add_query(tech_q, role_queries_count):
                        role_queries_count += 1
                        tech_modifier_count += 1

            # e. Add Location Modifiers ("{role} {location}")
            if cfg.include_location_modifiers and location_modifier_count < cfg.max_location_modifiers:
                for loc in cleaned_locations:
                    if location_modifier_count >= cfg.max_location_modifiers or role_queries_count >= cfg.max_queries_per_role:
                        break
                    loc_query_str = f"{canonical_name} {loc}"
                    loc_q = SearchStrategyQuery(
                        query=loc_query_str,
                        canonical_role=canonical_name,
                        strategy="location_modifier",
                        priority="MEDIUM",
                        reason=f"Geographical candidate preference '{loc}'",
                        location_filter=loc if caps.supports_location_filter else None,
                        remote_filter=True if is_remote_desired else None,
                        limit=caps.max_limit,
                    )
                    if try_add_query(loc_q, role_queries_count):
                        role_queries_count += 1
                        location_modifier_count += 1

        # 6. Priority-based Sorting (HIGH -> MEDIUM -> LOW)
        generated_queries.sort(key=lambda q: (PRIORITY_RANK.get(q.priority, 2), q.canonical_role))

        # 7. Strictly enforce max_total_queries limit
        bounded_queries = generated_queries[: cfg.max_total_queries]

        logger.info(
            f"Generated {len(bounded_queries)} search strategies (from {len(generated_queries)} pre-bounds) "
            f"across {len(target_roles)} target roles. Priority breakdown: "
            f"HIGH={sum(1 for q in bounded_queries if q.priority == 'HIGH')}, "
            f"MEDIUM={sum(1 for q in bounded_queries if q.priority == 'MEDIUM')}, "
            f"LOW={sum(1 for q in bounded_queries if q.priority == 'LOW')}"
        )

        return bounded_queries

    def _resolve_role_definitions(self, role_name: str) -> List[RoleAliasDefinition]:
        """Match role string against alias registry with fuzzy/alias support."""
        if role_name in self.role_aliases:
            return self.role_aliases[role_name]

        # Case-insensitive check
        for reg_role, defs in self.role_aliases.items():
            if reg_role.lower() == role_name.lower():
                return defs

        # Substring / acronym match (e.g. "Forward Deployed Engineer (FDE)" matches "Forward Deployed Engineer")
        for reg_role, defs in self.role_aliases.items():
            if reg_role.lower() in role_name.lower() or role_name.lower() in reg_role.lower():
                return defs

        # Unknown custom role fallback: create a single canonical definition
        return [
            RoleAliasDefinition(
                canonical_role=role_name,
                alias=role_name,
                priority="HIGH",
                strategy="canonical_role",
                reason="User-specified custom target role",
            )
        ]

    def _pick_relevant_tech_for_role(self, role_name: str, candidate_techs: List[str]) -> List[str]:
        """Pick 1-2 most relevant technologies for a specific role from candidate's verified skills."""
        role_lower = role_name.lower()
        if "backend" in role_lower:
            preferred_order = ["Python", "FastAPI", "SQL", "PostgreSQL"]
        elif "ai" in role_lower or "ml" in role_lower or "machine learning" in role_lower:
            preferred_order = ["PyTorch", "Python", "TensorFlow", "Transformers", "LLM", "RAG"]
        elif "forward" in role_lower or "fde" in role_lower:
            preferred_order = ["Python", "Docker", "Kubernetes"]
        else:
            preferred_order = ["Python"]

        picked = [t for t in preferred_order if any(t.lower() == ct.lower() for ct in candidate_techs)]
        return picked[:2]
