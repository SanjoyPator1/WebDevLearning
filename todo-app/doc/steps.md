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

## 4. Database Setup with PostgreSQL & Alembic

### 4.1 Initialize Alembic

```bash
alembic init alembic
```

Creates migration infrastructure in `alembic/` directory.

### 4.2 Create Database Models

**Created files:**

- `app/db/base.py` - Base class and TimestampMixin for all models
- `app/models/user.py` - User model with authentication fields
- `app/models/todo.py` - Todo model with status, priority, enums
- `app/models/__init__.py` - Imports all models for Alembic discovery
- `app/db/session.py` - Database session management and `get_db()` dependency

**Key concepts:**

- Base class for model inheritance
- Relationships (User has many Todos)
- Async session management
- Connection pooling

### 4.3 Configure Alembic

**Updated files:**

- `alembic/env.py` - Import models, set database URL from config, async support
- `alembic.ini` - Comment out hardcoded database URL
- `app/config.py` - Add `database_url_asyncpg` and `database_url_sync` properties
- `.env` - Add `DATABASE_URL` and `DATABASE_URL_SYNC`

**Key points:**

- Alembic uses sync URL (without `+asyncpg`)
- FastAPI uses async URL (with `+asyncpg`)
- Models imported via `import app.models` in `env.py`

### 4.4 Create and Apply Migration

```bash
# Generate migration
alembic revision --autogenerate -m "Initial schema with users and todos"

# Apply migration
alembic upgrade head

# Verify tables
docker exec -it todo_postgres psql -U postgres -d todo_app -c "\dt"
```

**Result:** Creates `users`, `todos`, and `alembic_version` tables.

### 4.5 Common Commands

```bash
alembic current              # Show current version
alembic history              # Show migration history
alembic upgrade head         # Apply pending migrations
alembic downgrade -1         # Rollback one migration
```

---

## 5. Security Utilities

### 5.1 Install Dependencies

```bash
uv add passlib[bcrypt] python-jose[cryptography]
```

### 5.2 Create Security Module

**File:** `app/core/security.py`

**Functions:**

- `get_password_hash()` - Hash passwords with bcrypt
- `verify_password()` - Verify password during login
- `create_access_token()` - Create JWT (expires in 30 min)
- `create_refresh_token()` - Create refresh JWT (expires in 7 days)
- `decode_token()` - Verify and decode JWT

### 5.3 Update Configuration

**Added to `app/config.py`:**

- `SECRET_KEY` - For JWT signing (generate with `openssl rand -hex 32`)
- `ALGORITHM` - HS256
- `ACCESS_TOKEN_EXPIRE_MINUTES` - 30
- `REFRESH_TOKEN_EXPIRE_DAYS` - 7

**Added to `.env`:**

```env
SECRET_KEY=<generated-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 5.4 Key Concepts

- **bcrypt** - Slow hashing prevents brute-force
- **JWT** - Stateless authentication tokens
- **Access tokens** - Short-lived for API calls
- **Refresh tokens** - Long-lived to get new access tokens

---

## 6. Repository Layer (Data Access)

### 6.1 Purpose

Separate database queries from business logic using the Repository Pattern.

**Benefits:**

- Centralized data access
- Reusable across application
- Easy to test (mockable)
- Type-safe with generics

### 6.2 Create Repositories

**File:** `app/db/repositories/base.py`

Generic CRUD operations for any model:

- `get(id)` - Get single record
- `get_multi()` - Get multiple with pagination/filters
- `update()` - Update existing record
- `delete(id)` - Delete record
- `count()` - Count records with filters

**File:** `app/db/repositories/user.py`

User-specific operations extending BaseRepository:

- `get_by_email()` - Find user by email
- `get_by_username()` - Find user by username
- `get_by_email_or_username()` - Flexible login
- `exists_by_email()` - Check email exists
- `exists_by_username()` - Check username exists
- `get_active_users()` - List active users

**File:** `app/db/repositories/__init__.py` - Export repositories

### 6.3 Key Concepts

**Generic Programming:**

- `TypeVar` and `Generic[ModelType]` for type safety
- One base class works for all models (User, Todo, etc.)
- IDE autocomplete with exact types

**Dynamic Filters:**

```python
# Can pass any model attributes as filters
users = await repo.get_multi(is_active=True, is_superuser=False)
```

### 6.4 Usage Pattern

```python
# Create repository instance
user_repo = UserRepository(db)

# Use repository methods
user = await user_repo.get_by_email("user@example.com")
exists = await user_repo.exists_by_username("john")
users = await user_repo.get_multi(skip=0, limit=10, is_active=True)
```

### 6.5 Architecture

```
Endpoints → Services → Repositories → Database
                          ↑
                       YOU ARE HERE
```

**Repositories only handle:**

- Database queries
- CRUD operations
- No business logic
- No validation
- No HTTP concerns

---

**Status after Step 6:** ✅ Data access layer complete, ready for service layer
