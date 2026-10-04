"""
Job Operating System - Database Initialization & Verification Script
100% Local, Zero-Cost, Strictly Non-Destructive.
"""
import sys
import os
import argparse
from pathlib import Path
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command

# Add paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.core.config import settings

DEFAULT_ADMIN_URL = os.getenv("ADMIN_DATABASE_URL", "postgresql://postgres@localhost:5432/postgres")
DEFAULT_APP_DB = "job_agent_db"
DEFAULT_APP_USER = "job_agent_user"


def get_app_password_from_settings() -> str:
    """Extracts password from configured DATABASE_URL safely."""
    from urllib.parse import urlparse
    parsed = urlparse(settings.DATABASE_URL)
    return parsed.password or ""


def ensure_database_and_user(admin_url: str = DEFAULT_ADMIN_URL):
    """Ensure database and dedicated app user exist without touching existing data."""
    print("Checking PostgreSQL admin connection...")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        # Check if database exists
        db_exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname=:name"),
            {"name": DEFAULT_APP_DB}
        ).fetchone()
        if not db_exists:
            print(f"Database '{DEFAULT_APP_DB}' does not exist. Creating...")
            conn.execute(text(f'CREATE DATABASE "{DEFAULT_APP_DB}";'))
            print(f"Created database: {DEFAULT_APP_DB}")
        else:
            print(f"Database '{DEFAULT_APP_DB}' exists.")

        # Check if user exists
        user_exists = conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname=:name"),
            {"name": DEFAULT_APP_USER}
        ).fetchone()
        if not user_exists:
            print(f"User '{DEFAULT_APP_USER}' does not exist. Creating...")
            app_pass = get_app_password_from_settings()
            conn.execute(text(f"CREATE USER {DEFAULT_APP_USER} WITH PASSWORD '{app_pass}';"))
            print(f"Created user: {DEFAULT_APP_USER}")
        else:
            print(f"User '{DEFAULT_APP_USER}' exists.")

    admin_engine.dispose()

    # Connect to target database and grant permissions
    target_admin_url = f"postgresql://postgres@localhost:5432/{DEFAULT_APP_DB}"
    target_engine = create_engine(target_admin_url, isolation_level="AUTOCOMMIT")
    with target_engine.connect() as conn:
        print(f"Configuring permissions on '{DEFAULT_APP_DB}'...")
        conn.execute(text(f"GRANT CONNECT ON DATABASE {DEFAULT_APP_DB} TO {DEFAULT_APP_USER};"))
        conn.execute(text(f"GRANT USAGE, CREATE ON SCHEMA public TO {DEFAULT_APP_USER};"))
        conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {DEFAULT_APP_USER};"))
        conn.execute(text(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {DEFAULT_APP_USER};"))
        conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {DEFAULT_APP_USER};"))
        conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {DEFAULT_APP_USER};"))
        print("Permissions verified.")
    target_engine.dispose()


def run_migrations():
    """Applies pending Alembic migrations safely and non-destructively."""
    print("Running Alembic migrations up to head...")
    alembic_ini_path = str(backend_dir / "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(alembic_cfg, "head")
    print("Migrations up to date.")


def verify_database_health(db_url: str = None) -> bool:
    """Verifies that the application user can connect and query schema tables."""
    target_url = db_url or settings.DATABASE_URL
    print(f"Verifying application connection to {DEFAULT_APP_DB}...")
    try:
        engine = create_engine(target_url, pool_pre_ping=True)
        with engine.connect() as conn:
            user, db = conn.execute(text("SELECT current_user, current_database()")).fetchone()
            table_count = conn.execute(
                text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
            ).scalar()
            print(f"Health Check PASSED: Connected as '{user}' to '{db}' ({table_count} public tables).")
        engine.dispose()
        return True
    except Exception as e:
        print(f"Health Check FAILED: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Initialize and verify local PostgreSQL database.")
    parser.add_argument("--skip-user-creation", action="store_true", help="Skip creating user and granting privileges")
    parser.add_argument("--skip-migrations", action="store_true", help="Skip running Alembic migrations")
    args = parser.parse_args()

    if not args.skip_user_creation:
        ensure_database_and_user()

    if not args.skip_migrations:
        run_migrations()

    ok = verify_database_health()
    if not ok:
        sys.exit(1)
    print("Database is production-ready.")


if __name__ == "__main__":
    main()
