import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

from app.db.session import SessionLocal
from app.services.government.universe_parser import GovernmentUniverseParser
from app.services.government.source_resolver import GovernmentSourceResolver
from app.models.government import GovernmentSource, GovernmentUnresolvedTarget

db = SessionLocal()
try:
    print("Parsing universe...")
    parsed = GovernmentUniverseParser.parse_universe_files()
    sample_targets = parsed["targets"][:100]

    print(f"Resolving sample {len(sample_targets)} targets...")
    res = GovernmentSourceResolver.resolve_and_ingest_targets(db, sample_targets)
    print("Resolution results:", res)

    total_sources = db.query(GovernmentSource).count()
    total_unresolved = db.query(GovernmentUnresolvedTarget).count()
    print(f"Total Sources in DB: {total_sources}")
    print(f"Total Unresolved in DB: {total_unresolved}")

    # Inspect some resolved with parent or confidence
    sample_srcs = db.query(GovernmentSource).filter(GovernmentSource.confidence_category.is_not(None)).limit(5).all()
    for s in sample_srcs:
        print(f"Source: {s.organisation_name} | Domain: {s.official_domain} | Level: {s.government_level} | Cat: {s.confidence_category} | ParentId: {s.parent_source_id}")

    # Inspect some unresolved backlog
    sample_unres = db.query(GovernmentUnresolvedTarget).limit(5).all()
    for u in sample_unres:
        print(f"Unresolved: {u.target_name} | Type: {u.target_type} | State: {u.state} | Reason: {u.reason} | Attempts: {u.attempts_count}")

finally:
    db.close()
