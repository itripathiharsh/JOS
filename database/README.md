# Database Architecture

- Engine: PostgreSQL 17
- ORM: SQLAlchemy 2.0
- Migrations: Alembic
- Database Name: `job_agent_db`
- Connection Pooling: Configured with pre-ping validation in `backend/app/db/session.py`.
