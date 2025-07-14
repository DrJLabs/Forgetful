"""Add user_id to memory_access_logs

Revision ID: 20161c9931da
Revises: migrate_vector_to_pgvector
Create Date: 2025-07-13 23:22:51.071521

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20161c9931da"
down_revision: Union[str, None] = "migrate_vector_to_pgvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id field to memory_access_logs table."""
    # Add user_id column - initially nullable to avoid issues with existing data
    with op.batch_alter_table("memory_access_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            "fk_memory_access_logs_user_id", "users", ["user_id"], ["id"]
        )
        batch_op.create_index("idx_access_user_time", ["user_id", "accessed_at"])

    # Note: In production, you would need to populate user_id values for existing records
    # before making the column NOT NULL


def downgrade() -> None:
    """Remove user_id field from memory_access_logs table."""
    with op.batch_alter_table("memory_access_logs", schema=None) as batch_op:
        batch_op.drop_index("idx_access_user_time")
        batch_op.drop_constraint("fk_memory_access_logs_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")
