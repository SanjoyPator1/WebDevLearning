"""
Test database models and relationships

This module tests:
- Model creation and validation
- Relationships and foreign keys
- Model methods and properties
- Database constraints
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.task import Task, TaskPriority
from app.models.team import Team
from app.models.project import Project
from app.models.team_member import TeamMember, TeamRole

class TestUserModel:
    """Test User model functionality"""
    
    async def test_create_user(self, db_session: AsyncSession):
        """Test user creation with required fields"""
        user = User(
            email="new@example.com",
            password_hash="hashed_password",
            full_name="New User"
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.full_name == "New User"
        assert user.email_verified is False  # Default value
        assert user.is_active is True  # Default value
        assert user.created_at is not None
        assert user.updated_at is not None
    
    async def test_user_display_name(self, sample_user: User):
        """Test user display name property"""
        assert sample_user.display_name == "Test User"
        
        # Test with user that has no full name
        user_no_name = User(
            email="noname@example.com", 
            password_hash="hash",
            full_name=""
        )
        assert user_no_name.display_name == "noname"
    
    async def test_user_relationships(self, db_session: AsyncSession, sample_user: User):
        """Test user relationships with tasks and teams"""
        # Create task created by user
        task = Task(
            title="User's Task",
            created_by=sample_user.id,
            assigned_to=sample_user.id
        )
        db_session.add(task)
        
        # Create team created by user
        team = Team(
            name="User's Team",
            created_by=sample_user.id
        )
        db_session.add(team)
        
        await db_session.commit()
        await db_session.refresh(sample_user)
        
        # Test relationships
        assert len(sample_user.created_tasks) == 1
        assert len(sample_user.assigned_tasks) == 1
        assert len(sample_user.created_teams) == 1
        assert sample_user.created_tasks[0].title == "User's Task"

class TestTaskModel:
    """Test Task model functionality"""
    
    async def test_create_task(self, db_session: AsyncSession, sample_user: User):
        """Test task creation with all fields"""
        due_date = datetime.utcnow() + timedelta(days=7)
        
        task = Task(
            title="Complete Project",
            description="Finish the task management project",
            priority=TaskPriority.HIGH,
            due_date=due_date,
            created_by=sample_user.id,
            assigned_to=sample_user.id
        )
        
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        
        assert task.id is not None
        assert task.title == "Complete Project"
        assert task.priority == TaskPriority.HIGH
        assert task.completed is False
        assert task.due_date == due_date
        assert task.created_by == sample_user.id
    
    async def test_task_completion(self, sample_task: Task):
        """Test task completion functionality"""
        assert not sample_task.completed
        assert sample_task.completed_at is None
        
        # Mark as completed
        sample_task.mark_completed()
        
        assert sample_task.completed is True
        assert sample_task.completed_at is not None
        
        # Mark as incomplete
        sample_task.mark_incomplete()
        
        assert sample_task.completed is False
        assert sample_task.completed_at is None
    
    async def test_task_overdue_property(self, db_session: AsyncSession, sample_user: User):
        """Test overdue property calculation"""
        # Create overdue task
        overdue_task = Task(
            title="Overdue Task",
            due_date=datetime.utcnow() - timedelta(days=1),
            created_by=sample_user.id
        )
        
        # Create future task
        future_task = Task(
            title="Future Task", 
            due_date=datetime.utcnow() + timedelta(days=1),
            created_by=sample_user.id
        )
        
        # Create completed overdue task
        completed_task = Task(
            title="Completed Task",
            due_date=datetime.utcnow() - timedelta(days=1),
            completed=True,
            created_by=sample_user.id
        )
        
        assert overdue_task.is_overdue is True
        assert future_task.is_overdue is False
        assert completed_task.is_overdue is False  # Completed tasks aren't overdue
    
    async def test_days_until_due(self, sample_user: User):
        """Test days until due calculation"""
        # Task due in 5 days
        future_task = Task(
            title="Future Task",
            due_date=datetime.utcnow() + timedelta(days=5),
            created_by=sample_user.id
        )
        
        # Task overdue by 3 days
        overdue_task = Task(
            title="Overdue Task",
            due_date=datetime.utcnow() - timedelta(days=3),
            created_by=sample_user.id
        )
        
        # Task with no due date
        no_due_task = Task(
            title="No Due Date",
            created_by=sample_user.id
        )
        
        assert future_task.days_until_due == 5
        assert overdue_task.days_until_due == -3
        assert no_due_task.days_until_due is None

class TestTeamModel:
    """Test Team model functionality"""
    
    async def test_team_creation(self, db_session: AsyncSession, sample_user: User):
        """Test team creation and properties"""
        team = Team(
            name="Development Team",
            description="Main development team",
            created_by=sample_user.id
        )
        
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)
        
        assert team.id is not None
        assert team.name == "Development Team"
        assert team.is_active is True
        assert team.member_count == 0  # No members yet
        assert team.project_count == 0  # No projects yet
    
    async def test_team_member_relationships(self, db_session: AsyncSession, sample_team: Team, sample_user: User):
        """Test team member relationships"""
        # Add user as team member
        membership = TeamMember(
            team_id=sample_team.id,
            user_id=sample_user.id,
            role=TeamRole.ADMIN
        )
        
        db_session.add(membership)
        await db_session.commit()
        await db_session.refresh(sample_team)
        
        assert sample_team.member_count == 1
        assert len(sample_team.members) == 1
        assert sample_team.members[0].role == TeamRole.ADMIN

class TestSoftDelete:
    """Test soft delete functionality"""
    
    async def test_user_soft_delete(self, sample_user: User):
        """Test user soft delete functionality"""
        assert sample_user.is_active is True
        assert sample_user.is_deleted is False
        assert sample_user.deleted_at is None
        
        # Soft delete user
        sample_user.soft_delete()
        
        assert sample_user.is_active is False
        assert sample_user.is_deleted is True
        assert sample_user.deleted_at is not None
        
        # Restore user
        sample_user.restore()
        
        assert sample_user.is_active is True
        assert sample_user.is_deleted is False
        assert sample_user.deleted_at is None