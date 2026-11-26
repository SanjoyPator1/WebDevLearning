"""Add role admin to admin user

Revision ID: c345778254d6
Revises: f49d78274f94
Create Date: 2025-07-28 15:36:25.251571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c345778254d6'
down_revision: Union[str, None] = 'f49d78274f94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET role = 'admin'
        WHERE email = 'admin@taskmanager.com';
        """
    )

def downgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET role = 'user'
        WHERE email = 'admin@taskmanager.com';
        """
    )
