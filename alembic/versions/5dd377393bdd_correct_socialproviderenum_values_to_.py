"""Correct socialproviderenum values to uppercase

Revision ID: 5dd377393bdd
Revises: db710733b455
Create Date: 2025-06-18 06:08:54.794467

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5dd377393bdd"
down_revision: Union[str, None] = "db710733b455"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE socialproviderenum ADD VALUE IF NOT EXISTS 'NAVER'")
    op.execute("ALTER TYPE socialproviderenum ADD VALUE IF NOT EXISTS 'KAKAO'")
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
