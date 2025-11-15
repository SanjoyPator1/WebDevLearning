# steps of creating this project - quick rough

## 1. inital project setup - folder files uv venv

- created the folder structure and initial files

```
todo-app/
├── app/
│   ├── api/v1/endpoints/    # REST API endpoints
│   ├── core/                # Security & logging
│   ├── db/repositories/     # Data access layer
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic validation
│   ├── services/            # Business logic
│   └── middleware/          # Custom middleware
├── alembic/                 # Database migrations
├── Dockerfile               # Container definition
├── docker-compose.yml       # Multi-container setup
└── requirements.txt         # Dependencies
```

- INITIALIZE UV / PROJECT VENV / DEPENDENCIES

  - cd into the project directory and select your python version example

    ```bash
        pyenv local 3.11.8
    ```

  - initialize the uv project

    ```bash
    uv init
    ```

  - add project dependencies and after that the .venv will be created

    ```bash
    uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pydantic python-dotenv
    ```

  - activate venv

    ```bash
    source .venv/bin/activate
    ```

  - verify with

    ```bash
    uv pip list
    ```

  - for vs code select python interpreter -> `ctrl + shift + p` and type `Python: Select Interpreter` and enter the full path like this `/home/user/Desktop/dev/backend/WebDevLearning/todo-app/.venv/bin/python`

  - run via

    ```
    uv run uvicorn app.main:app --reload
    ```

  - can also see pyproject.toml for the dependencies list

  - Export for Docker

    When you later build Docker images, it’s cleaner to use a `requirements.txt` inside Docker.  
    `uv` can generate that automatically:

    ```
    uv export --frozen > requirements.txt
    ```

    Then in Dockerfile, you’ll use:

    ```dockerfile
     COPY requirements.txt .
     RUN pip install --no-cache-dir -r requirements.txt
    ```

## 2. Docker Setup & Commands

- **Create Dockerfile**

  - Multi-stage build for smaller final image
  - Install system dependencies (Postgres client, gcc)
  - Create virtual environment and install Python dependencies
  - Copy app code and switch to non-root user
  - Expose port `8000` and set healthcheck

- **Create docker-compose.yml**

  - Define 3 services: `db` (Postgres), `app` (FastAPI), `pgadmin` (optional)
  - Add volumes for persistent storage (`postgres_data`)
  - Create network (`todo_network`) for container communication
  - Use `depends_on + healthcheck` to ensure FastAPI waits for Postgres

- **Create .env file**

  - Store DB credentials, secrets, API configs, ports
  - Example:

    ```
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    POSTGRES_DB=todo_app
    SECRET_KEY=...
    DEBUG=True
    ```

- **Build and run containers**

  ```bash
  docker compose up --build
  ```

- **Check running containers**

  ```bash
  docker compose ps
  ```

- **View logs**

  ```bash
  docker compose logs -f app
  docker compose logs -f db
  ```

- **Stop containers**

  ```bash
  docker compose down
  ```

- **Connect to Postgres from host / DBeaver**

  - Host: `localhost`
  - Port: `5433`
  - User: `postgres`
  - Password: `postgres`
  - DB: `todo_app`

- **Connect to pgAdmin**

  - Open `http://localhost:5055`
  - Login: `admin@admin.com` / `admin`
  - Add new server: Host = `db`, Port = `5433`, Username / Password from .env

- **Connect via terminal**

  ```bash
  psql -h localhost -p 5433 -U postgres -d todo_app
  ```

  and use password - `postgres`

- **Test FastAPI**

  - Browser / Postman: `http://localhost:8000/health` → should return `{"status": "ok"}`

- **Optional: wait-for-db script**

  - Ensure FastAPI waits until Postgres is ready before starting
  - Can be added in Dockerfile / docker-compose command

---

## 3. Pydantic Models and Simple Routes

In this stage, we define **data validation schemas** using **Pydantic** and create a few **basic FastAPI routes** to test how our backend behaves before connecting it to the database or services. This step helps establish a clear data flow between the API request/response and the business logic.

---

### **1. Purpose of Pydantic in FastAPI**

Pydantic models define the **structure**, **type safety**, and **validation rules** for data moving in and out of your application.
They are used in:

- Request bodies (input validation)
- Response models (structured outputs)
- Internal logic (data consistency between layers)

When a request hits an endpoint, FastAPI:

1. Parses JSON into Python objects.
2. Validates the data using Pydantic schemas.
3. Returns automatic and informative error messages if validation fails.

Example:

```python
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(..., min_length=3)
    price: float = Field(..., gt=0)
```

If a client sends `{ "name": "a", "price": -5 }`, FastAPI automatically responds with a 422 validation error, no manual checks needed.

---

### **2. Creating Todo Schemas**

A **Todo** item usually includes fields like title, description, status, and priority.
We define multiple schemas to handle different use cases (create, update, list, etc.).

#### Base Schema

Contains shared fields across models:

```python
class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    completed: bool = False
    priority: TodoPriority = TodoPriority.MEDIUM
    status: TodoStatus = TodoStatus.PENDING
    category: str | None = None
    due_date: datetime | None = None
```

#### Validators

Pydantic allows you to validate fields using `@field_validator`:

```python
@field_validator("due_date")
@classmethod
def validate_due_date(cls, v):
    if v is not None and v < datetime.now(v.tzinfo):
        raise ValueError("Due date cannot be in the past")
    return v
```

This ensures that no invalid due date can be sent to the server.

#### Derived Schemas

- **TodoCreate** → used when creating a new todo.
- **TodoUpdate** → all fields optional, used for PATCH/PUT operations.
- **TodoInDB** → internal representation (includes database fields).
- **Todo** → public response schema for API.
- **TodoList** → for paginated responses.

---

### **3. User and Token Schemas**

#### User Schemas

Used to validate and return structured data about users.

```python
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str | None = None
    is_active: bool = True
```

Separate classes are used for different actions:

- **UserCreate** → for registration (includes password).
- **UserUpdate** → partial updates.
- **UserInDB** → internal model with DB fields.
- **User** → returned to client without sensitive data.

#### Token Schemas

For authentication and session handling:

```python
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

---

### **4. Setting Up Simple Routes**

After defining schemas, we can quickly test routes using dummy data before connecting real services.

#### Example: Authentication Endpoints

```python
@router.post("/register", response_model=User)
async def register(user_in: UserCreate):
    return dummy_user
```

- Accepts a `UserCreate` object.
- Returns a `User` response.
- Uses dummy data for now to verify route and schema integration.

```python
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return dummy_token
```

This simulates authentication, later to be connected to a real service.

---

### **5. Todo Routes Overview**

We add routes for CRUD operations on todos using dummy in-memory data.

- `GET /todos` → list todos with filters and pagination
- `POST /todos` → create new todo
- `GET /todos/{id}` → fetch specific todo
- `PUT /todos/{id}` → update a todo
- `DELETE /todos/{id}` → delete a todo
- `PATCH /todos/{id}/complete` → mark as completed

Example:

```python
@router.post("", response_model=Todo, status_code=status.HTTP_201_CREATED)
async def create_todo(todo_in: TodoCreate):
    new_todo = {
        "id": 4,
        "owner_id": 101,
        "title": todo_in.title,
        "description": todo_in.description,
        "completed": False,
        "priority": todo_in.priority,
        "status": TodoStatus.PENDING,
        "category": todo_in.category,
        "due_date": todo_in.due_date,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    return new_todo
```

---

### **6. Simple User Routes**

These routes allow testing of user profile behavior with mock data:

```python
@router.get("/me", response_model=User)
async def get_current_user_profile():
    return dummy_user
```

```python
@router.put("/me", response_model=User)
async def update_current_user(user_in: UserUpdate):
    updated_user = dummy_user.copy()
    updated_user.update(user_in.model_dump(exclude_unset=True))
    updated_user["updated_at"] = datetime.now()
    return updated_user
```

These are quick, self-contained routes that demonstrate how **Pydantic models** integrate with **FastAPI route handlers**.

---

### **7. Summary**

- **Pydantic models** define strict contracts for request/response data.
- **Validation** happens automatically, reducing boilerplate.
- **Response models** help document and constrain output structures.
- **Routes** can use dummy data for early development and testing.
- This setup creates a stable foundation for later connecting real database and service layers.

Once these Pydantic schemas and routes are in place, you can verify them via:

```
uv run uvicorn app.main:app --reload
```

and visit `http://localhost:8000/docs` to explore all endpoints with automatic validation and schema-based documentation.

## 4. Setting up Database and PostgreSQL

### 4.1 Initialize Alembic

```bash
alembic init alembic
```

The last word `alembic` is the name of the folder where migrations will be stored.

**What this creates:**

```
alembic/
├── env.py              # Migration environment config
├── script.py.mako      # Template for new migrations
├── versions/           # Directory for migration files (empty initially)
└── README
alembic.ini             # Alembic configuration file
```

---

### 4.2 Create Database Base and Models

**Purpose:** Define the foundation for all database models and create the actual data models.

#### Create `app/db/base.py`

```python
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TimestampMixin:
    """Adds automatic created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

**Key concepts:**

- `Base`: All models must inherit from this
- `TimestampMixin`: Reusable component for automatic timestamps
- `Mapped[type]`: SQLAlchemy 2.0 type hints for better IDE support

#### Create `app/models/user.py`

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship: one user has many todos
    todos: Mapped[list["Todo"]] = relationship(
        "Todo",
        back_populates="owner",
        cascade="all, delete-orphan"
    )
```

#### Create `app/models/todo.py`

```python
from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class TodoPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Todo(Base, TimestampMixin):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TodoStatus] = mapped_column(default=TodoStatus.PENDING, nullable=False, index=True)
    priority: Mapped[TodoPriority] = mapped_column(default=TodoPriority.MEDIUM, nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    completed: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Foreign key linking to User
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Relationship: each todo belongs to one user
    owner: Mapped["User"] = relationship("User", back_populates="todos")
```

**Key concepts:**

- `Enum`: Type-safe constants for status and priority
- `ForeignKey`: Links todos to users
- `relationship()`: Creates Python attributes for easy access (not a DB column)

#### Create `app/models/__init__.py`

```python
"""Import all models so Alembic can discover them."""
from app.db.base import Base
from app.models.user import User
from app.models.todo import Todo, TodoStatus, TodoPriority

__all__ = [
    "Base",
    "User",
    "Todo",
    "TodoStatus",
    "TodoPriority",
]
```

**Why this matters:** Alembic imports this file to discover all your models.

---

### 4.3 Create Database Session Management

**Purpose:** Manage database connections and provide sessions to your routes.

#### Create `app/db/session.py`

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings


# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url_asyncpg,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    Automatically creates and closes sessions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

**Key concepts:**

- `engine`: Manages connection pool
- `AsyncSessionLocal`: Factory that creates sessions
- `get_db()`: FastAPI dependency that provides sessions to routes

**Usage in routes:**

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

@app.get("/todos")
async def list_todos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo))
    return result.scalars().all()
```

---

### 4.4 Update Configuration

**Purpose:** Provide database connection URLs and other settings.

#### Update `app/config.py`

```python
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        case_sensitive=True,
        extra="ignore"
    )

    # Database URLs
    DATABASE_URL: PostgresDsn
    DATABASE_URL_SYNC: PostgresDsn

    # ... other settings ...

    @property
    def database_url_asyncpg(self) -> str:
        """Async URL for FastAPI (with +asyncpg driver)."""
        return str(self.DATABASE_URL)

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic (without +asyncpg driver)."""
        return str(self.DATABASE_URL_SYNC)


settings = Settings()
```

#### Update `.env` file

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/todo_app
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5433/todo_app

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=True
ENVIRONMENT=development
API_V1_PREFIX=/api/v1
```

**Important:** Your PostgreSQL is running on port `5433` (not 5432) because of docker-compose port mapping.

---

### 4.5 Configure Alembic

**Purpose:** Tell Alembic how to connect to your database and find your models.

#### Update `alembic/env.py`

Replace the entire contents with:

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import config and models
from app.config import settings
from app.db.base import Base
import app.models  # This imports ALL models

# Alembic config
config = context.config

# Set database URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL scripts)."""
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
    """Execute migrations with given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode (connects to DB)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations."""
    asyncio.run(run_async_migrations())


# Determine mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Key changes:**

- Added project to Python path
- Imported your config and models
- Set database URL from settings
- Configured for async operations

#### Update `alembic.ini`

Find and comment out the sqlalchemy.url line:

```ini
# sqlalchemy.url is now set programmatically in env.py
; sqlalchemy.url = driver://user:pass@localhost/dbname
```

---

### 4.6 Install Required Dependencies

```bash
# Make sure you have all necessary packages
uv add psycopg2-binary  # Sync driver for Alembic
uv add asyncpg          # Async driver for FastAPI
uv add alembic          # Migration tool
uv add sqlalchemy[asyncio]  # ORM with async support

# Export for Docker
uv export --frozen > requirements.txt
```

---

### 4.7 Create and Apply First Migration

#### Step 1: Ensure PostgreSQL is Running

```bash
# Check if containers are running
docker ps

# You should see:
# - todo_postgres (port 5433)
# - todo_app (port 8000)
```

#### Step 2: Test Database Connection

```bash
# Connect to PostgreSQL
docker exec -it todo_postgres psql -U postgres -d todo_app

# Inside psql, test connection:
\dt  # Should show no tables yet
\q   # Quit
```

#### Step 3: Generate Initial Migration

```bash
# From project root (where alembic.ini is)
alembic revision --autogenerate -m "Initial schema with users and todos"
```

**Expected output:**

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.autogenerate.compare] Detected added table 'users'
INFO  [alembic.autogenerate.compare] Detected added index 'ix_users_email' on '('email',)'
INFO  [alembic.autogenerate.compare] Detected added index 'ix_users_username' on '('username',)'
INFO  [alembic.autogenerate.compare] Detected added table 'todos'
INFO  [alembic.autogenerate.compare] Detected added index 'ix_todos_title' on '('title',)'
  Generating alembic/versions/890d073d940d_initial_schema_with_users_and_todos.py ... done
```

**What happened:**

1. Alembic imported your models
2. Compared models to database (which is empty)
3. Generated SQL to create tables
4. Saved SQL in a migration file

#### Step 4: Review the Migration File

```bash
# Check what was generated
cat alembic/versions/890d073d940d_initial_schema_with_users_and_todos.py
```

Look for:

- `upgrade()` function - creates tables
- `downgrade()` function - drops tables
- All columns, indexes, foreign keys

#### Step 5: Apply the Migration

```bash
alembic upgrade head
```

**Expected output:**

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 890d073d940d, Initial schema with users and todos
```

**What happened:**

1. Connected to database
2. Ran `upgrade()` function
3. Created `users` and `todos` tables
4. Created `alembic_version` table to track migration state

#### Step 6: Verify Tables Were Created

```bash
# Check tables in database
docker exec -it todo_postgres psql -U postgres -d todo_app -c "\dt"
```

**Expected output:**

```
              List of relations
 Schema |      Name       | Type  |  Owner
--------+-----------------+-------+----------
 public | alembic_version | table | postgres
 public | todos           | table | postgres
 public | users           | table | postgres
(3 rows)
```

**Success!** Your database schema is now created and ready to use.

---

### 4.8 Common Alembic Commands

```bash
# Check current migration version
alembic current

# Show migration history
alembic history

# Show verbose history with details
alembic history --verbose

# Create new migration (manual)
alembic revision -m "description"

# Create new migration (auto-detect changes)
alembic revision --autogenerate -m "Add new field"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Generate SQL without applying (review changes)
alembic upgrade head --sql

# Stamp database as current without running migrations
alembic stamp head
```

---

### 4.9 Testing Database Connection from FastAPI

Create a simple test script:

```python
# test_db.py
import asyncio
from app.db.session import AsyncSessionLocal
from app.models import User
from sqlalchemy import select


async def test_connection():
    """Test database connection."""
    async with AsyncSessionLocal() as session:
        # Query users table
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Connected! Found {len(users)} users")


if __name__ == "__main__":
    asyncio.run(test_connection())
```

Run it:

```bash
python test_db.py
# Output: Connected! Found 0 users
```

---

### 4.10 Key Takeaways

**What we accomplished:**

1. Initialized Alembic for database migrations
2. Created database models (User, Todo)
3. Set up database session management
4. Configured Alembic to work with our models
5. Created and applied first migration
6. Verified tables were created successfully

**How it all connects:**

```
Models (User, Todo)
    ↓
Alembic reads models via Base.metadata
    ↓
Generates migration files
    ↓
Applies migrations to PostgreSQL
    ↓
FastAPI uses sessions from get_db()
    ↓
Routes query data using sessions
```

**Next steps:**

- Add authentication endpoints
- Create repository layer for data access
- Add service layer for business logic
- Create API endpoints for CRUD operations
