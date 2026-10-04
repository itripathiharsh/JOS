"""phase4_step7_application_decision_engine

Revision ID: 6a9ecd24b208
Revises: 136fe4467b04
Create Date: 2026-10-04 14:11:01.912602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a9ecd24b208'
down_revision: Union[str, Sequence[str], None] = '136fe4467b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add application_decisions table."""
    op.create_table(
        'application_decisions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('candidate_id', sa.String(length=36), nullable=False),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('risk_level', sa.String(length=20), nullable=False, server_default='LOW'),
        sa.Column('reasons', sa.JSON(), nullable=True),
        sa.Column('supporting_factors', sa.JSON(), nullable=True),
        sa.Column('disqualifying_factors', sa.JSON(), nullable=True),
        sa.Column('review_reasons', sa.JSON(), nullable=True),
        sa.Column('evaluation_metadata', sa.JSON(), nullable=True),
        sa.Column('engine_version', sa.String(length=50), nullable=False, server_default='1.0.0'),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', 'candidate_id', name='uq_decision_job_candidate')
    )
    op.create_index(op.f('ix_application_decisions_candidate_id'), 'application_decisions', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_application_decisions_decision'), 'application_decisions', ['decision'], unique=False)
    op.create_index(op.f('ix_application_decisions_engine_version'), 'application_decisions', ['engine_version'], unique=False)
    op.create_index(op.f('ix_application_decisions_job_id'), 'application_decisions', ['job_id'], unique=False)
    op.create_index(op.f('ix_application_decisions_risk_level'), 'application_decisions', ['risk_level'], unique=False)


def downgrade() -> None:
    """Downgrade schema removing application_decisions table."""
    op.drop_index(op.f('ix_application_decisions_risk_level'), table_name='application_decisions')
    op.drop_index(op.f('ix_application_decisions_job_id'), table_name='application_decisions')
    op.drop_index(op.f('ix_application_decisions_engine_version'), table_name='application_decisions')
    op.drop_index(op.f('ix_application_decisions_decision'), table_name='application_decisions')
    op.drop_index(op.f('ix_application_decisions_candidate_id'), table_name='application_decisions')
    op.drop_table('application_decisions')
