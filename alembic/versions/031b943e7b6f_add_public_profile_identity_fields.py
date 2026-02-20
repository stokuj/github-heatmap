"""add public profile identity fields

Revision ID: 031b943e7b6f
Revises: 75e2a6eaa9fe
Create Date: 2026-02-20 11:42:21.466967

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "031b943e7b6f"
down_revision: Union[str, Sequence[str], None] = "75e2a6eaa9fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "github_profiles",
        sa.Column("github_user_id", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "github_profiles", sa.Column("public_id", sa.String(length=36), nullable=True)
    )

    op.execute(
        """
        UPDATE github_profiles
        SET public_id = md5(random()::text || clock_timestamp()::text)
        WHERE public_id IS NULL
        """
    )

    op.alter_column("github_profiles", "public_id", nullable=False)
    op.create_unique_constraint(
        "uq_github_profiles_github_user_id", "github_profiles", ["github_user_id"]
    )
    op.create_unique_constraint(
        "uq_github_profiles_public_id", "github_profiles", ["public_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_github_profiles_public_id", "github_profiles", type_="unique"
    )
    op.drop_constraint(
        "uq_github_profiles_github_user_id", "github_profiles", type_="unique"
    )
    op.drop_column("github_profiles", "public_id")
    op.drop_column("github_profiles", "github_user_id")
