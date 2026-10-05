"""
Job Operating System - State/UT and Sector Coverage Matrix
Calculates exhaustive coverage telemetry across all 28 Indian States, 8 Union Territories,
Central Government ministries, PSUs, research institutes, regulators, and health missions.
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.government import GovernmentSource, GovernmentVacancy
from app.schemas.government import (
    GovernmentCoverageResponse,
    StateCoverageItem,
    SectorCoverageItem,
)
from app.services.government.seed_registry import INDIAN_STATES, INDIAN_UTS


class GovernmentCoverageCalculator:
    """
    Computes real-time coverage metrics and status across geography and government tiers.
    """

    @classmethod
    def calculate_coverage(cls, db: Session) -> GovernmentCoverageResponse:
        total_sources = db.query(func.count(GovernmentSource.id)).scalar() or 0
        verified_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.source_status.in_(["VERIFIED", "ACTIVE"])
        ).scalar() or 0
        active_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.source_status == "ACTIVE"
        ).scalar() or 0
        manual_access = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.source_status == "REQUIRES_MANUAL_ACCESS"
        ).scalar() or 0
        never_checked = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.last_checked.is_(None)
        ).scalar() or 0

        # Sector breakdown counts
        central_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.government_level == "central"
        ).scalar() or 0
        state_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.government_level == "state"
        ).scalar() or 0
        ut_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.government_level == "ut"
        ).scalar() or 0

        psu_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.organisation_type == "psu"
        ).scalar() or 0
        research_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.organisation_type == "research_institute"
        ).scalar() or 0
        uni_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.organisation_type == "university"
        ).scalar() or 0
        regulator_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.organisation_type == "regulator"
        ).scalar() or 0
        healthcare_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.organisation_type == "hospital"
        ).scalar() or 0
        district_sources = db.query(func.count(GovernmentSource.id)).filter(
            GovernmentSource.organisation_type.in_(["district_administration", "municipal_body"])
        ).scalar() or 0

        # State / UT Matrix
        states_items: List[StateCoverageItem] = []

        # Query counts grouped by state
        state_counts_query = db.query(
            GovernmentSource.state,
            func.count(GovernmentSource.id).label("src_cnt"),
            func.sum(GovernmentSource.vacancies_found).label("vac_cnt"),
        ).group_by(GovernmentSource.state).all()

        state_stats = {
            r[0]: {"sources": r[1] or 0, "vacancies": int(r[2] or 0)}
            for r in state_counts_query if r[0]
        }

        # 28 States
        for state_name in INDIAN_STATES:
            stats = state_stats.get(state_name, {"sources": 0, "vacancies": 0})
            src_count = stats["sources"]
            status = "COVERED" if src_count >= 2 else ("MINIMAL" if src_count == 1 else "UNEXPLORED")
            states_items.append(
                StateCoverageItem(
                    state=state_name,
                    is_ut=False,
                    sources_count=src_count,
                    active_sources=src_count,
                    vacancies_count=stats["vacancies"],
                    status=status,
                )
            )

        # 8 Union Territories
        for ut_name in INDIAN_UTS:
            stats = state_stats.get(ut_name, {"sources": 0, "vacancies": 0})
            src_count = stats["sources"]
            status = "COVERED" if src_count >= 2 else ("MINIMAL" if src_count == 1 else "UNEXPLORED")
            states_items.append(
                StateCoverageItem(
                    state=ut_name,
                    is_ut=True,
                    sources_count=src_count,
                    active_sources=src_count,
                    vacancies_count=stats["vacancies"],
                    status=status,
                )
            )

        # Sector Items
        sectors_items = [
            SectorCoverageItem(sector="Central Ministries & Departments", sources_count=central_sources),
            SectorCoverageItem(sector="State Departments & Directorates", sources_count=state_sources),
            SectorCoverageItem(sector="Union Territories", sources_count=ut_sources),
            SectorCoverageItem(sector="Central & State PSUs", sources_count=psu_sources),
            SectorCoverageItem(sector="Research Institutes (CSIR/ICMR/DRDO)", sources_count=research_sources),
            SectorCoverageItem(sector="IITs / NITs / Universities", sources_count=uni_sources),
            SectorCoverageItem(sector="Regulators & Statutory Authorities", sources_count=regulator_sources),
            SectorCoverageItem(sector="Healthcare & AIIMS", sources_count=healthcare_sources),
            SectorCoverageItem(sector="Districts & Municipal Administrations", sources_count=district_sources),
        ]

        return GovernmentCoverageResponse(
            total_sources_discovered=total_sources,
            verified_sources=verified_sources,
            active_sources=active_sources,
            sources_never_checked=never_checked,
            sources_requiring_manual_access=manual_access,
            central_government_sources=central_sources,
            state_government_sources=state_sources,
            union_territory_sources=ut_sources,
            psu_sources=psu_sources,
            research_institute_sources=research_sources,
            university_sources=uni_sources,
            regulator_sources=regulator_sources,
            healthcare_sources=healthcare_sources,
            district_municipal_sources=district_sources,
            other_sources=max(0, total_sources - (central_sources + state_sources + ut_sources)),
            states_coverage=states_items,
            sectors_coverage=sectors_items,
        )
