import sys
import os
import json
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.db.session import SessionLocal
from app.services.government.engine import GovernmentDiscoveryEngine
from app.models.government import GovernmentSource, GovernmentVacancy, GovernmentUnresolvedTarget
from app.models.job import Job

def main():
    print("=== EXECUTING INDIAN GOVERNMENT SOURCE UNIVERSE MISSION (10-PASS) ===")
    db = SessionLocal()
    try:
        start = time.time()
        # Execute mission
        result = GovernmentDiscoveryEngine.execute_universe_discovery_mission(
            db=db,
            max_passes=10,
            run_search=False,  # Keep search deterministic for local mission
            batch_size=10
        )
        duration = time.time() - start

        # Detailed metrics audit
        total_sources = db.query(GovernmentSource).count()
        total_vacancies = db.query(GovernmentVacancy).count()
        total_unresolved = db.query(GovernmentUnresolvedTarget).count()
        
        # Confidence breakdown
        conf_counts = {}
        for row in db.query(GovernmentSource.confidence_category).all():
            val = row[0] or "UNKNOWN"
            conf_counts[val] = conf_counts.get(val, 0) + 1
            
        # Level breakdown
        level_counts = {}
        for row in db.query(GovernmentSource.government_level).all():
            val = row[0] or "UNKNOWN"
            level_counts[val] = level_counts.get(val, 0) + 1
            
        # Parent-child links
        linked_children = db.query(GovernmentSource).filter(GovernmentSource.parent_source_id.is_not(None)).count()
        apex_parents = db.query(GovernmentSource).filter(GovernmentSource.parent_source_id.is_(None)).count()

        # Unresolved by type and status
        unresolved_types = {}
        for row in db.query(GovernmentUnresolvedTarget.target_type).all():
            val = row[0] or "UNKNOWN"
            unresolved_types[val] = unresolved_types.get(val, 0) + 1

        unresolved_statuses = {}
        for row in db.query(GovernmentUnresolvedTarget.discovery_status).all():
            val = row[0] or "UNKNOWN"
            unresolved_statuses[val] = unresolved_statuses.get(val, 0) + 1

        resolved_direct_count = db.query(GovernmentUnresolvedTarget).filter(
            GovernmentUnresolvedTarget.discovery_status == "RESOLVED"
        ).count()
        covered_parent_count = db.query(GovernmentUnresolvedTarget).filter(
            GovernmentUnresolvedTarget.discovery_status == "COVERED_VIA_PARENT"
        ).count()
        covered_central_count = db.query(GovernmentUnresolvedTarget).filter(
            GovernmentUnresolvedTarget.discovery_status == "COVERED_VIA_CENTRAL_RECRUITMENT"
        ).count()
        covered_directory_count = db.query(GovernmentUnresolvedTarget).filter(
            GovernmentUnresolvedTarget.discovery_status == "COVERED_VIA_DIRECTORY"
        ).count()
        verified_duplicate_count = db.query(GovernmentUnresolvedTarget).filter(
            GovernmentUnresolvedTarget.discovery_status == "VERIFIED_DUPLICATE"
        ).count()
        verified_non_org_count = db.query(GovernmentUnresolvedTarget).filter(
            GovernmentUnresolvedTarget.discovery_status == "NOT_AN_ORGANISATION"
        ).count()

        total_covered_targets = resolved_direct_count + covered_parent_count + covered_central_count + covered_directory_count
        total_accounted_targets = total_covered_targets + verified_duplicate_count + verified_non_org_count

        active_unresolved_count = db.query(GovernmentUnresolvedTarget).filter(
            GovernmentUnresolvedTarget.discovery_status.in_(["UNRESOLVED", "UNRESOLVED_DOMAIN", "AMBIGUOUS"])
        ).count()
        uninvestigated_count = db.query(GovernmentUnresolvedTarget).filter(
            GovernmentUnresolvedTarget.attempts_count == 0
        ).count()
        unclassified_count = db.query(GovernmentUnresolvedTarget).filter(
            GovernmentUnresolvedTarget.discovery_status.is_(None)
        ).count()

        # Scheduled for monitoring
        scheduled_count = db.query(GovernmentSource).filter(GovernmentSource.next_crawl_at.is_not(None)).count()

        resolution_rate = round((total_accounted_targets / max(total_unresolved, 1)) * 100.0, 2)

        summary = {
            "mission_status": result.get("status"),
            "passes_completed": result.get("passes_completed"),
            "total_raw_targets": result.get("total_raw_targets"),
            "total_deduplicated_targets": result.get("total_deduplicated_targets"),
            "total_verified_sources": total_sources,
            "confidence_breakdown": conf_counts,
            "level_breakdown": level_counts,
            "hierarchy": {
                "apex_parents": apex_parents,
                "linked_children": linked_children
            },
            "backlog_resolution": {
                "total_targets_evaluated": total_unresolved,
                "total_accounted": total_accounted_targets,
                "total_covered": total_covered_targets,
                "direct_verified_sources": resolved_direct_count,
                "covered_via_parent": covered_parent_count,
                "covered_via_central_recruitment": covered_central_count,
                "covered_via_directory": covered_directory_count,
                "verified_duplicates": verified_duplicate_count,
                "verified_non_organisations": verified_non_org_count,
                "active_unresolved": active_unresolved_count,
                "uninvestigated": uninvestigated_count,
                "unclassified": unclassified_count,
                "temporarily_unavailable": 0,
                "anti_bot": 0,
                "retry_queue": 0,
                "coverage_rate_percent": resolution_rate,
                "by_status": unresolved_statuses,
                "by_type": unresolved_types
            },
            "vacancies_discovered": total_vacancies,
            "continuous_monitoring_scheduled": scheduled_count,
            "duration_seconds": round(duration, 2),
            "pass_results_keys": list(result.get("pass_results", {}).keys())
        }

        print("\n=== UNIVERSE MISSION RESULTS SUMMARY ===")
        print(json.dumps(summary, indent=2))

        # Save output to scratch directory for documentation
        os.makedirs(r"F:\job wala project\govt\discovery_output", exist_ok=True)
        with open(r"F:\job wala project\govt\discovery_output\mission_execution_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print("\nSummary saved to F:\\job wala project\\govt\\discovery_output\\mission_execution_summary.json")

    finally:
        db.close()

if __name__ == "__main__":
    main()
