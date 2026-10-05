import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))
sys.path.insert(0, backend_dir)
sys.path.insert(0, root_dir)

from sqlalchemy import create_engine, text

TEST_DB_URL = "postgresql://postgres:postgres@localhost:5432/job_agent_test_db"
engine = create_engine(TEST_DB_URL)

with engine.connect() as conn:
    print("Applying missing columns and tables to job_agent_test_db...")
    conn.execute(text("""
        ALTER TABLE government_sources ADD COLUMN IF NOT EXISTS district VARCHAR(100);
        ALTER TABLE government_sources ADD COLUMN IF NOT EXISTS parent_source_id VARCHAR(36);
        ALTER TABLE government_sources ADD COLUMN IF NOT EXISTS confidence_category VARCHAR(50) DEFAULT 'AUTHORITATIVE';
        
        CREATE TABLE IF NOT EXISTS government_unresolved_targets (
            id VARCHAR(36) PRIMARY KEY,
            target_name VARCHAR(255) NOT NULL,
            target_type VARCHAR(100) NOT NULL,
            state VARCHAR(100),
            district VARCHAR(100),
            reason VARCHAR(255) NOT NULL,
            attempted_queries TEXT,
            attempted_domains TEXT,
            discovery_status VARCHAR(50) NOT NULL,
            attempts_count INTEGER NOT NULL,
            last_attempted_at TIMESTAMP WITH TIME ZONE NOT NULL,
            retry_at TIMESTAMP WITH TIME ZONE,
            resolved_source_id VARCHAR(36) REFERENCES government_sources(id) ON DELETE SET NULL,
            metadata_json TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL
        );

        CREATE INDEX IF NOT EXISTS ix_government_sources_district ON government_sources(district);
        CREATE INDEX IF NOT EXISTS ix_government_sources_parent_source_id ON government_sources(parent_source_id);
        CREATE INDEX IF NOT EXISTS ix_government_sources_confidence_category ON government_sources(confidence_category);
        CREATE INDEX IF NOT EXISTS ix_government_unresolved_targets_target_name ON government_unresolved_targets(target_name);
        CREATE INDEX IF NOT EXISTS ix_government_unresolved_targets_target_type ON government_unresolved_targets(target_type);
        CREATE INDEX IF NOT EXISTS ix_government_unresolved_targets_state ON government_unresolved_targets(state);
        CREATE INDEX IF NOT EXISTS ix_government_unresolved_targets_discovery_status ON government_unresolved_targets(discovery_status);
    """))
    conn.commit()
    print("job_agent_test_db successfully updated with hierarchy and unresolved targets columns!")
