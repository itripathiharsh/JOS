import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

from app.services.government.universe_parser import GovernmentUniverseParser

res = GovernmentUniverseParser.parse_universe_files()
print(f"Total Raw Targets: {res['total_raw_targets']}")
print(f"Total Deduplicated Targets: {res['total_deduplicated_targets']}")
print("\nCounts By Type:")
for k, v in res["counts_by_type"].items():
    print(f"  {k}: {v}")

print("\nSample Targets:")
for t in res["targets"][:15]:
    print(f"  [{t.target_type}] {t.target_name} (State={t.state}, OrgType={t.organisation_type}, Term={t.hiring_term})")
