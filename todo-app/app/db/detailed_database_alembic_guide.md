# Comprehensive Database & Alembic Integration Guide

## 📚 Table of Contents

1. [Overview: The Database Architecture](#overview-the-database-architecture)
2. [Understanding Each Component](#understanding-each-component)
3. [Step-by-Step Setup Process](#step-by-step-setup-process)
4. [How Everything Connects](#how-everything-connects)
5. [Alembic Commands Reference](#alembic-commands-reference)
6. [Common Database Operations](#common-database-operations)
7. [Troubleshooting Guide](#troubleshooting-guide)

---

## 🏗️ Overview: The Database Architecture

### The Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐   │
│  │   Routes     │ ───> │   Services   │ ───> │ Repositories │   │
│  │ (endpoints)  │      │ (business    │      │ (data access)│   │
│  └──────────────┘      │  logic)      │      └──────────────┘   │
│                        └──────────────┘              │          │
│                                                      │          │
│                        ┌──────────────┐              │          │
│                        │  get_db()    │ <────────────┘          │
│                        │  dependency  │                         │
│                        └──────────────┘                         │
│                               │                                 │
└───────────────────────────────┼─────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   AsyncSessionLocal   │
                    │   (session factory)   │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    async_engine       │
                    │  (connection pool)    │
                    └───────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   PostgreSQL Database │
                    │   (running in Docker) │
                    └───────────────────────┘
                                ▲
                                │
                    ┌───────────────────────┐
                    │   Alembic Migrations  │
                    │  (schema management)  │
                    └───────────────────────┘
```

### Key Relationships

1. **Models** define what tables look like
2. **Alembic** reads models and creates SQL to build/modify tables
3. **Session.py** creates database connections
4. **get_db()** provides sessions to your routes
5. **Routes** use sessions to query/modify data

---

## 🔍 Understanding Each Component

### 1. Configuration (`app/config.py`)

**Purpose:** Centralized configuration management using Pydantic Settings

**What it does:**

```python
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file='.env',              # ← Loads .env file
        env_file_encoding="utf-8",
        case_sensitive=True,           # ← DATABASE_URL ≠ database_url
        extra="ignore"                 # ← Ignore unknown env vars
    )

    # Database URLs
    DATABASE_URL: PostgresDsn          # ← Validates PostgreSQL URL format
    DATABASE_URL_SYNC: PostgresDsn
```

**Key Features:**

- **Type Validation**: `PostgresDsn` ensures URLs are valid PostgreSQL connection strings
- **Automatic Loading**: Reads from `.env` file on startup
- **Type Safety**: Wrong types cause startup errors, not runtime bugs
- **Case Sensitive**: `DATABASE_URL` in .env must match exactly

**Properties for Database URLs:**

```python
@property
def database_url_asyncpg(self) -> str:
    """Get async database URL."""
    return str(self.DATABASE_URL)  # postgresql+asyncpg://...

@property
def database_url_sync(self) -> str:
    """Get sync database URL for Alembic."""
    return str(self.DATABASE_URL_SYNC)  # postgresql://...
```

**Why two URLs?**

- **Async URL** (`+asyncpg`): Used by FastAPI for non-blocking database operations
- **Sync URL** (no `+asyncpg`): Used by Alembic which doesn't support async

---

### 2. Base Model (`app/db/base.py`)

**Purpose:** Foundation for all database models

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
from datetime import datetime


class Base(DeclarativeBase):
    """
    Base class for all database models.

    What it does:
    - Provides SQLAlchemy ORM functionality
    - Tracks all models that inherit from it
    - Stores metadata about all tables
    """
    pass
```

**Key Concept:** All your models (User, Todo) MUST inherit from this Base class. This allows:

- SQLAlchemy to track all models
- Alembic to discover what tables exist
- Metadata to be collected for migrations

```python
class TimestampMixin:
    """
    Mixin to add automatic timestamps.

    What it does:
    - Adds created_at field (set once on creation)
    - Adds updated_at field (updated on every change)
    - Uses database server time (server_default=func.now())
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),      # ← Store with timezone
        server_default=func.now(),    # ← Database sets this automatically
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),          # ← Updates automatically on change
        nullable=False,
    )
```

**Why use a Mixin?**

- Avoids code duplication
- Just inherit `TimestampMixin` in any model to get timestamps
- Single source of truth for timestamp behavior

---

### 3. Database Models (`app/models/`)

#### User Model (`app/models/user.py`)

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    User model - represents 'users' table.

    Inheritance:
    - Base: Makes it a SQLAlchemy model
    - TimestampMixin: Adds created_at/updated_at
    """

    __tablename__ = "users"  # ← Actual table name in database

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # ↑ Mapped[int]: Type hint for SQLAlchemy and Python
    # ↑ primary_key=True: Auto-incrementing unique identifier
    # ↑ index=True: Creates database index for fast lookups

    # User Credentials
    email: Mapped[str] = mapped_column(
        String(255),          # ← Max 255 characters
        unique=True,          # ← No duplicate emails allowed
        index=True,           # ← Fast lookups by email
        nullable=False        # ← Must be provided
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # ↑ Store password hash, NEVER plain password

    # Optional Fields
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # ↑ str | None: Python 3.10+ union syntax for Optional[str]

    # Status Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship to Todos
    todos: Mapped[list["Todo"]] = relationship(
        "Todo",                      # ← Related model name
        back_populates="owner",      # ← Field in Todo model that points back
        cascade="all, delete-orphan" # ← Delete todos when user is deleted
    )
    # ↑ This creates a Python attribute (not a database column)
    # ↑ user.todos returns a list of Todo objects
```

**Key Concepts:**

1. **`Mapped[type]`**: Modern SQLAlchemy 2.0 type hints

   - Tells Python the type
   - Tells SQLAlchemy the type
   - Better IDE support

2. **`mapped_column()`**: Defines column properties

   - Type: `String(255)`, `Boolean`, `Integer`
   - Constraints: `unique`, `nullable`, `default`
   - Indexes: `index=True` for faster queries

3. **`relationship()`**: Defines connections between models
   - NOT a database column
   - Creates Python attribute for easy access
   - `user.todos` automatically queries related todos

#### Todo Model (`app/models/todo.py`)

```python
from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class TodoPriority(str, Enum):
    """
    Enum for todo priority levels.

    Why Enum?
    - Type safety: Can't use invalid values
    - IDE autocomplete
    - Database constraint: Only these values allowed
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TodoStatus(str, Enum):
    """Enum for todo status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Todo(Base, TimestampMixin):
    """Todo model - represents 'todos' table."""

    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Content Fields
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ↑ Text: For long strings (no length limit)

    # Enum Fields
    status: Mapped[TodoStatus] = mapped_column(
        default=TodoStatus.PENDING,  # ← Default value
        nullable=False,
        index=True
    )
    # ↑ SQLAlchemy automatically handles enum storage

    priority: Mapped[TodoPriority] = mapped_column(
        default=TodoPriority.MEDIUM,
        nullable=False,
        index=True
    )

    # Optional Fields
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    completed: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Foreign Key - Links to User
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),  # ← References users.id column
        nullable=False,
        index=True
    )
    # ↑ This IS a database column
    # ↑ Creates a constraint: owner_id must exist in users.id

    # Relationship back to User
    owner: Mapped["User"] = relationship("User", back_populates="todos")
    # ↑ This is NOT a database column
    # ↑ todo.owner returns the User object
```

**Foreign Key Relationship:**

```
users table          todos table
┌─────────┐         ┌──────────────┐
│ id  = 1 │ <────── │ owner_id = 1 │
│ id  = 2 │         │ owner_id = 1 │
│ id  = 3 │ <────── │ owner_id = 3 │
└─────────┘         └──────────────┘
```

---

### 4. Models Package (`app/models/__init__.py`)

**Purpose:** Central import point for all models

```python
"""
Models package.
Import all models here so Alembic can discover them.
"""

# Import Base first - required for all models
from app.db.base import Base

# Import all models
from app.models.user import User
from app.models.todo import Todo, TodoStatus, TodoPriority

# Export for easy importing
__all__ = [
    "Base",
    "User",
    "Todo",
    "TodoStatus",
    "TodoPriority",
]
```

**Why this matters:**

- When you `import app.models`, ALL models are imported
- Alembic imports `app.models` to discover all tables
- Without this, Alembic won't see your models
- Makes imports cleaner: `from app.models import User, Todo`

---

### 5. Database Session (`app/db/session.py`)

**Purpose:** Create and manage database connections

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings


# Step 1: Create the Engine
engine = create_async_engine(
    settings.database_url_asyncpg,  # ← Connection URL
    echo=settings.DEBUG,            # ← Log all SQL (helpful for debugging)
    pool_pre_ping=True,             # ← Verify connection before use
    pool_size=5,                    # ← Keep 5 connections ready
    max_overflow=10,                # ← Allow 10 more if needed (max 15 total)
)
```

**What is an Engine?**

- Manages connection pool (reuses connections)
- Handles database driver (asyncpg)
- Translates SQLAlchemy to PostgreSQL SQL

**Connection Pool:**

```
Application          Connection Pool         Database
                    ┌─────────────────┐
Request 1 ────────> │ Conn 1 (in use) │ ───> PostgreSQL
Request 2 ────────> │ Conn 2 (in use) │ ───> PostgreSQL
Request 3 ────────> │ Conn 3 (idle)   │
                    │ Conn 4 (idle)   │
                    │ Conn 5 (idle)   │
                    └─────────────────┘
```

Benefits:

- Reuse connections (faster than creating new ones)
- Limit total connections (prevent overwhelming database)
- Automatic cleanup

```python
# Step 2: Create Session Factory
AsyncSessionLocal = async_sessionmaker(
    engine,                    # ← Use our engine
    class_=AsyncSession,       # ← Async session type
    expire_on_commit=False,    # ← Don't clear objects after commit
    autocommit=False,          # ← Manual transaction control
    autoflush=False,           # ← Manual flush control
)
```

**What is a Session?**

- Workspace for database operations
- Tracks changes to objects
- Manages transactions (commit/rollback)
- One session = one transaction

```python
# Step 3: Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    How it works:
    1. Creates a new session
    2. Yields it to the route function
    3. Automatically closes it when done
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session  # ← Route function gets this
        finally:
            await session.close()  # ← Always closes, even on error
```

**Usage in Routes:**

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

@app.get("/todos")
async def list_todos(db: AsyncSession = Depends(get_db)):
    # ↑ FastAPI calls get_db() and injects the session
    result = await db.execute(select(Todo))
    return result.scalars().all()
    # ↑ Session automatically closes after response
```

---

### 6. Alembic Configuration

#### Alembic Environment (`alembic/env.py`)

**Purpose:** Tell Alembic how to connect and what to migrate

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

import sys
from pathlib import Path

# Step 1: Add project to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
# ↑ Allows importing from 'app' package
```

**Why this matters:**

- Alembic runs as a separate process
- Needs to import your app code
- Without this, `from app.config import settings` fails

```python
# Step 2: Import configuration and models
from app.config import settings
from app.db.base import Base
import app.models  # ← This imports ALL models

# Step 3: Configure Alembic
config = context.config

# Override database URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url_sync)
# ↑ Uses sync URL (Alembic doesn't support async)

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata - tells Alembic about models
target_metadata = Base.metadata
# ↑ This contains info about all tables from all models
```

**Migration Functions:**

```python
def run_migrations_offline() -> None:
    """
    Offline mode - generate SQL scripts without connecting.

    Use case: Generate SQL to run manually
    Command: alembic upgrade --sql head > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Execute migrations with the given connection.

    What it does:
    - Compares current DB schema to target_metadata
    - Generates and runs SQL to sync them
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,          # ← Detect column type changes
        compare_server_default=True # ← Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Online mode with async - connects and runs migrations.

    This is what runs when you use: alembic upgrade head
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # ← No pooling for migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


# Determine mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## 📝 Step-by-Step Setup Process

### Phase 1: Project Initialization

```bash
# 1. Create project structure
mkdir todo-app && cd todo-app
mkdir -p app/{api/v1/endpoints,core,db/repositories,models,schemas,services,middleware}

# 2. Initialize Python environment
pyenv local 3.11.8
uv init

# 3. Install dependencies
uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pydantic python-dotenv pydantic-settings psycopg2-binary
```

### Phase 2: Configuration

**Step 1: Create `.env` file**

```env
# Database URLs
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/todo_app
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5433/todo_app

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=True
ENVIRONMENT=development
```

**Step 2: Create `app/config.py`**

- Define Settings class with Pydantic
- Add database URL properties
- Configure CORS, pagination, etc.

### Phase 3: Database Models

**Step 1: Create `app/db/base.py`**

- Define `Base` class (DeclarativeBase)
- Define `TimestampMixin` for automatic timestamps

**Step 2: Create model files**

- `app/models/user.py` - User model
- `app/models/todo.py` - Todo model with enums

**Step 3: Create `app/models/__init__.py`**

- Import all models
- Export for easy access

### Phase 4: Database Session

**Create `app/db/session.py`**

- Create async engine
- Create session factory
- Define `get_db()` dependency

### Phase 5: Alembic Setup

**Step 1: Initialize Alembic**

```bash
alembic init alembic
```

This creates:

```
alembic/
├── env.py           # Migration environment
├── script.py.mako   # Migration template
├── versions/        # Migration files go here
└── README
alembic.ini          # Alembic configuration
```

**Step 2: Configure `alembic/env.py`**

- Add project to Python path
- Import config and models
- Set target_metadata
- Configure async migrations

**Step 3: Update `alembic.ini`**

- Comment out sqlalchemy.url (we set it programmatically)

### Phase 6: Create Migrations

**Step 1: Generate initial migration**

```bash
alembic revision --autogenerate -m "Initial schema with users and todos"
```

**What happens:**

1. Alembic imports your models via `env.py`
2. Compares models to current database (empty)
3. Generates migration file with SQL to create tables

**Step 2: Review migration file**

```bash
# Check the generated file
cat alembic/versions/890d073d940d_initial_schema_with_users_and_todos.py
```

Look for:

- `upgrade()` function - creates tables
- `downgrade()` function - drops tables
- Verify all columns, indexes, constraints are correct

**Step 3: Apply migration**

```bash
alembic upgrade head
```

**What happens:**

1. Connects to database
2. Runs `upgrade()` function
3. Creates tables
4. Records version in `alembic_version` table

**Step 4: Verify**

```bash
# Check tables
docker exec -it todo_postgres psql -U postgres -d todo_app -c "\dt"

# You should see:
# - alembic_version (tracks current version)
# - users
# - todos
```

---

## 🔗 How Everything Connects

### Database Query Flow

```python
# 1. User makes request
GET /api/v1/todos

# 2. FastAPI routes to endpoint
@router.get("/todos")
async def list_todos(db: AsyncSession = Depends(get_db)):
    # 3. get_db() is called
    #    - Creates session from AsyncSessionLocal
    #    - Yields session to function

    # 4. Execute query using session
    result = await db.execute(
        select(Todo).where(Todo.owner_id == user_id)
    )

    # 5. SQLAlchemy:
    #    - Converts select() to SQL
    #    - Sends to PostgreSQL
    #    - Receives rows
    #    - Converts rows to Todo objects

    todos = result.scalars().all()

    # 6. Return data
    return todos

    # 7. get_db() cleanup
    #    - Session automatically closed
    #    - Connection returned to pool
```

### Migration Creation Flow

```
1. You modify models
   └─> Add new field to Todo model

2. Run: alembic revision --autogenerate -m "Add tags field"

3. Alembic process:
   ├─> Imports alembic/env.py
   ├─> env.py imports app.models
   ├─> env.py sets target_metadata = Base.metadata
   ├─> Connects to database
   ├─> Reads current schema from database
   ├─> Compares to Base.metadata (from models)
   ├─> Detects differences
   └─> Generates migration file

4. Migration file contains:
   ├─> upgrade() - SQL to add tags column
   └─> downgrade() - SQL to remove tags column

5. Run: alembic upgrade head
   ├─> Connects to database
   ├─> Checks alembic_version table
   ├─> Runs pending migrations
   └─> Updates alembic_version
```

### Data Flow Example

```python
# Example: Creating a todo

# 1. Request comes in
POST /api/v1/todos
Body: {"title": "Buy milk", "priority": "high"}

# 2. Pydantic validates request
todo_in = TodoCreate(**request_body)

# 3. Service layer receives validated data
async def create_todo(db: AsyncSession, todo_in: TodoCreate, owner_id: int):
    # 4. Create model instance
    db_todo = Todo(
        title=todo_in.title,
        priority=todo_in.priority,
        owner_id=owner_id,
        # created_at, updated_at set automatically by database
    )

    # 5. Add to session
    db.add(db_todo)

    # 6. Commit transaction
    await db.commit()
    # SQL: INSERT INTO todos (...) VALUES (...)

    # 7. Refresh to get database-generated values
    await db.refresh(db_todo)

    # 8. Return created todo
    return db_todo
```

---

## 🛠️ Alembic Commands Reference

### Basic Commands

```bash
# Initialize Alembic in your project
alembic init alembic
# Creates: alembic/ directory and alembic.ini

# Create a new migration (manual)
alembic revision -m "Add column to users"
# Creates: alembic/versions/abc123_add_column_to_users.py
# You must write upgrade() and downgrade() yourself

# Create a new migration (auto-detect changes)
alembic revision --autogenerate -m "Add tags field to todos"
# Creates: alembic/versions/def456_add_tags_field_to_todos.py
# Automatically generates upgrade() and downgrade()

# Apply all pending migrations
alembic upgrade head
# Runs all migrations not yet applied

# Rollback one migration
alembic downgrade -1
# Runs the downgrade() of the last applied migration

# Rollback to specific version
alembic downgrade abc123
# Rolls back to version abc123

# Show current version
alembic current
# Shows which migration is currently applied

# Show migration history
alembic history
# Lists all migrations with their IDs and messages

# Show verbose history
alembic history --verbose
# Shows full details of each migration
```

### Advanced Commands

```bash
# Generate SQL without applying (offline mode)
alembic upgrade head --sql > migration.sql
# Creates SQL script you can review or run manually

# Upgrade to specific version
alembic upgrade def456
# Applies migrations up to and including def456

# Downgrade to specific version
alembic downgrade abc123
# Rolls back to abc123

# Show difference between DB and models (diagnostic)
alembic check
# Reports if DB schema differs from models

# Stamp database without running migrations
alembic stamp head
# Marks database as up-to-date without running migrations
# Useful if you manually applied changes

# Merge multiple heads (if you have branches)
alembic merge heads -m "Merge migrations"
# Combines divergent migration paths

# Edit migration before applying
alembic revision --autogenerate -m "description"
# Then manually edit the generated file before:
alembic upgrade head
```

### Useful Patterns

```bash
# Create migration with specific revision ID
alembic revision -m "description" --rev-id=001

# Create empty migration (for data migrations)
alembic revision -m "Populate default categories"
# Edit the file to add data operations, not schema changes

# Show SQL for last migration without applying
alembic upgrade head --sql

# Test migration (upgrade then downgrade)
alembic upgrade head
alembic downgrade -1
# If downgrade works, your migration is reversible

# Force revision in specific directory
alembic revision --autogenerate -m "msg" --version-path=alembic/versions
```

---

## 🔄 Common Database Operations

### 1. Adding a New Column

**Step 1: Update the model**

```python
# app/models/todo.py
class Todo(Base, TimestampMixin):
    # ... existing fields ...

    # Add new field
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

**Step 2: Create migration**

```bash
alembic revision --autogenerate -m "Add tags column to todos"
```

**Step 3: Review migration**

```python
# alembic/versions/xyz_add_tags_column_to_todos.py
def upgrade():
    op.add_column('todos', sa.Column('tags', sa.String(500), nullable=True))

def downgrade():
    op.drop_column('todos', 'tags')
```

**Step 4: Apply**

```bash
alembic upgrade head
```

### 2. Modifying a Column

**Example: Increase title length from 200 to 300**

**Step 1: Update model**

```python
title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
# Changed from String(200) to String(300)
```

**Step 2: Create migration**

```bash
alembic revision --autogenerate -m "Increase title length to 300"
```

**Step 3: Review and apply**

```bash
# Review the generated file
cat alembic/versions/latest_file.py

# Apply
alembic upgrade head
```

### 3. Adding an Index

**Step 1: Update model**

```python
# Add index=True to existing column
category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
```

**Step 2: Create and apply migration**

```bash
alembic revision --autogenerate -m "Add index to category"
alembic upgrade head
```

### 4. Renaming a Column

**⚠️ Alembic can't auto-detect renames!**

**Step 1: Create manual migration**

```bash
alembic revision -m "Rename full_name to display_name"
```

**Step 2: Edit migration file**

```python
def upgrade():
    op.alter_column('users', 'full_name', new_column_name='display_name')

def downgrade():
    op.alter_column('users', 'display_name', new_column_name='full_name')
```

**Step 3: Update model**

```python
# Change field name in model AFTER creating migration
display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

**Step 4: Apply**

```bash
alembic upgrade head
```

### 5. Adding a New Table

**Step 1: Create new model file**

```python
# app/models/comment.py
class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    todo_id: Mapped[int] = mapped_column(ForeignKey("todos.id"), nullable=False)
```

**Step 2: Import in `__init__.py`**

```python
# app/models/__init__.py
from app.models.comment import Comment

__all__ = [
    "Base",
    "User",
    "Todo",
    "Comment",  # Add to exports
]
```

**Step 3: Create and apply migration**

```bash
alembic revision --autogenerate -m "Add comments table"
alembic upgrade head
```

### 6. Data Migrations

**Example: Set default value for existing rows**

```bash
alembic revision -m "Set default priority for existing todos"
```

**Edit the migration:**

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Update existing NULL priorities to 'medium'
    op.execute(
        "UPDATE todos SET priority = 'medium' WHERE priority IS NULL"
    )

    # Now make column NOT NULL
    op.alter_column('todos', 'priority', nullable=False)

def downgrade():
    # Reverse: make nullable again
    op.alter_column('todos', 'priority', nullable=True)
```

### 7. Testing Migrations

```bash
# 1. Create test database
docker exec -it todo_postgres psql -U postgres -c "CREATE DATABASE todo_app_test;"

# 2. Set test database URL
export DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5433/todo_app_test

# 3. Run all migrations
alembic upgrade head

# 4. Test downgrade
alembic downgrade base  # Removes all tables

# 5. Test upgrade again
alembic upgrade head

# 6. Cleanup
docker exec -it todo_postgres psql -U postgres -c "DROP DATABASE todo_app_test;"
```

---

## 🐛 Troubleshooting Guide

### Problem 1: "Target database is not up to date"

**Error:**

```
FAILED: Target database is not up to date.
```

**Solution:**

```bash
# Check current version
alembic current

# Show what migrations are pending
alembic history

# Apply pending migrations
alembic upgrade head
```

### Problem 2: Alembic doesn't detect model changes

**Possible causes:**

1. **Model not imported**

```python
# Fix: Add to app/models/__init__.py
from app.models.new_model import NewModel
```

2. **Base.metadata not accessible**

```python
# Fix: Ensure model inherits from Base
class NewModel(Base):
    __tablename__ = "new_table"
```

3. **Alembic cache issue**

```bash
# Fix: Remove cache and try again
rm -rf alembic/versions/__pycache__
alembic revision --autogenerate -m "Try again"
```

### Problem 3: Migration conflicts

**Error:**

```
Multiple head revisions are present
```

**Solution:**

```bash
# Show heads
alembic heads

# Merge heads
alembic merge heads -m "Merge migrations"

# Apply merged migration
alembic upgrade head
```

### Problem 4: Can't rollback migration

**Error:**

```
Can't locate revision identified by 'abc123'
```

**Solution:**

```bash
# Show history
alembic history

# Use correct revision ID from history
alembic downgrade def456
```

### Problem 5: Database connection issues

**Error:**

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**

1. **Check database is running**

```bash
docker ps | grep postgres
```

2. **Test connection**

```bash
docker exec -it todo_postgres psql -U postgres -d todo_app
```

3. **Check environment variables**

```bash
python -c "from app.config import settings; print(settings.database_url_sync)"
```

4. **Verify port**

```bash
# Your database is on port 5433, not 5432
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5433/todo_app
```

### Problem 6: Import errors in env.py

**Error:**

```
ModuleNotFoundError: No module named 'app'
```

**Solution:**

```python
# Add to alembic/env.py at the top
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Problem 7: Manual intervention needed

**When to edit migrations manually:**

1. **Renaming columns** - Alembic sees this as drop + add
2. **Data transformations** - Moving data between columns
3. **Complex constraints** - Multi-column unique constraints
4. **Performance** - Adding indexes on large tables

**Best practice:**

```bash
# 1. Generate migration
alembic revision --autogenerate -m "Complex change"

# 2. Review and edit generated file
vim alembic/versions/latest_*.py

# 3. Test in development
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# 4. Apply to production
```

---

## 📚 Best Practices

### 1. Always Review Auto-generated Migrations

```bash
# After creating migration
alembic revision --autogenerate -m "description"

# ALWAYS review the file before applying
cat alembic/versions/latest_file.py

# Look for:
# - Unexpected drops
# - Missing columns
# - Wrong data types
# - Missing indexes
```

### 2. Test Migrations Both Ways

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Test upgrade again
alembic upgrade head
```

### 3. Use Descriptive Migration Messages

```bash
# ❌ Bad
alembic revision --autogenerate -m "update"

# ✅ Good
alembic revision --autogenerate -m "Add email verification fields to users table"
```

### 4. Keep Migrations Small

```bash
# ❌ Don't combine multiple changes
alembic revision -m "Add fields, modify indexes, rename columns, add tables"

# ✅ One logical change per migration
alembic revision -m "Add email_verified field to users"
alembic revision -m "Add index to created_at column"
```

### 5. Never Modify Applied Migrations

```bash
# ❌ DON'T edit a migration that's been applied
vim alembic/versions/old_migration.py  # DANGER!

# ✅ Create a new migration
alembic revision -m "Fix issue from previous migration"
```

### 6. Backup Before Major Changes

```bash
# Backup database before major migrations
docker exec -it todo_postgres pg_dump -U postgres todo_app > backup.sql

# Run migration
alembic upgrade head

# If something goes wrong:
docker exec -i todo_postgres psql -U postgres todo_app < backup.sql
```

### 7. Use Transactions

Alembic automatically wraps migrations in transactions, but be aware:

```python
# Each migration runs in a transaction
def upgrade():
    op.add_column('users', sa.Column('new_field', sa.String(100)))
    # If this fails, previous changes are rolled back
    op.add_column('todos', sa.Column('another_field', sa.Integer()))
```

---

## 🎯 Quick Reference

### Common Workflows

**Adding a new field:**

```bash
# 1. Edit model
# 2. Generate migration
alembic revision --autogenerate -m "Add field"
# 3. Review migration
# 4. Apply
alembic upgrade head
```

**Fixing a mistake:**

```bash
# 1. Rollback
alembic downgrade -1
# 2. Edit model
# 3. Create new migration
alembic revision --autogenerate -m "Fix previous change"
# 4. Apply
alembic upgrade head
```

**Starting fresh (development only):**

```bash
# Drop all tables
docker exec -it todo_postgres psql -U postgres -d todo_app -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
# Run all migrations
alembic upgrade head
```

### File Locations

```
todo-app/
├── .env                          # Environment variables
├── alembic.ini                   # Alembic config
├── alembic/
│   ├── env.py                    # Migration environment
│   └── versions/                 # Migration files
│       └── 890d073d940d_*.py     # Your migrations
├── app/
│   ├── config.py                 # Settings
│   ├── db/
│   │   ├── base.py              # Base & TimestampMixin
│   │   └── session.py           # Engine & get_db()
│   └── models/
│       ├── __init__.py          # Import all models
│       ├── user.py              # User model
│       └── todo.py              # Todo model
```

---

This guide should cover everything you need to understand how the database, models, and Alembic work together in your FastAPI application!
