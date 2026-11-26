"""Update admin and user password hashes

Revision ID: daa59265cea2
Revises: cd5a4fa1e4ce
Create Date: 2025-07-28 14:56:41.520868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'daa59265cea2'
down_revision: Union[str, None] = 'cd5a4fa1e4ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Update admin password
    op.execute(
        """
        UPDATE users
        SET password_hash = '$2b$12$UUMYvhx4v2PS.MToHX8INuRhiKzLi6UK8ZOIbvaf76xCoKj4zqKy6'
        WHERE email = 'admin@taskmanager.com';
        """
    )
    # Update user password
    op.execute(
        """
        UPDATE users
        SET password_hash = '$2b$12$k2rjhW068uWvygj3aO0aNuiKDUY9sgoJcwQjGj9UxHu8cfaCeUkji'
        WHERE email = 'user@taskmanager.com';
        """
    )

def downgrade():
    # Optionally, you can set these back to some previous value or NULL
    pass
