"""Add seed data

Revision ID: cd5a4fa1e4ce
Revises: 0e77dc7ab39a
Create Date: 2025-07-28 12:47:09.367666

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy.sql import table, column
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'cd5a4fa1e4ce'
down_revision: Union[str, None] = '0e77dc7ab39a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Insert seed data for development and testing
    """
    # Define table structures for bulk insert
    users_table = table('users',
        column('id', UUID),
        column('email', sa.String),
        column('password_hash', sa.String),
        column('full_name', sa.String),
        column('email_verified', sa.Boolean),
        column('is_active', sa.Boolean),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime),
    )
    
    teams_table = table('teams',
        column('id', UUID),
        column('name', sa.String),
        column('description', sa.String),
        column('is_active', sa.Boolean),
        column('created_by', UUID),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime),
    )
    
    # Generate UUIDs for seed data
    admin_user_id = uuid.uuid4()
    test_user_id = uuid.uuid4()
    team_id = uuid.uuid4()
    now = datetime.utcnow()
    
    # Insert seed users
    op.bulk_insert(users_table, [
        {
            'id': admin_user_id,
            'email': 'admin@taskmanager.com',
            'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8xq9uh1Qxy',  # password: admin123
            'full_name': 'Admin User',
            'email_verified': True,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': test_user_id,
            'email': 'user@taskmanager.com',
            'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8xq9uh1Qxy',  # password: user123
            'full_name': 'Test User',
            'email_verified': True,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }
    ])
    
    # Insert seed team
    op.bulk_insert(teams_table, [
        {
            'id': team_id,
            'name': 'Development Team',
            'description': 'Main development team for task management',
            'is_active': True,
            'created_by': admin_user_id,
            'created_at': now,
            'updated_at': now,
        }
    ])

def downgrade() -> None:
    """
    Remove seed data
    """
    # Delete seed data in reverse dependency order
    op.execute("DELETE FROM teams WHERE name = 'Development Team'")
    op.execute("DELETE FROM users WHERE email IN ('admin@taskmanager.com', 'user@taskmanager.com')")

