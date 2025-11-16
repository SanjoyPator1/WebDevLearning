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

## 7. Service Layer & Auth Endpoints

### 7.1 Purpose

Implement the **Service Layer** for business logic and **Auth Endpoints** for user authentication.

**Why Service Layer?**

- Separate business logic from HTTP concerns
- Reusable across multiple endpoints
- Easy to test independently
- Orchestrate complex operations

**Architecture:**

```
Endpoints (HTTP) → Services (Business Logic) → Repositories (Data Access) → Database
```

---

### 7.2 Create UserService

**File:** `app/services/user_service.py`

**Key Methods:**

- `get_user(user_id)` - Get user by ID, raise 404 if not found
- `authenticate(username, password)` - Verify credentials, return user or None
- `create_user(user_in)` - Register new user with validation
- `update_user(user_id, user_in)` - Update user with uniqueness checks
- `delete_user(user_id)` - Delete user account
- `get_users()` - List users with pagination

**Business Logic Examples:**

```python
# Validates email/username uniqueness before creating
# Hashes passwords before storing
# Prevents account enumeration (generic auth errors)
# Checks user is_active before authenticating
```

---

### 7.3 Fix: Add create() to BaseRepository

**Issue:** UserService calls `repository.create()` but method doesn't exist.

**Add to `app/db/repositories/base.py`:**

```python
async def create(self, obj_in: dict[str, Any]) -> ModelType:
    """Create a new record."""
    db_obj = self.model(**obj_in)
    self.db.add(db_obj)
    await self.db.commit()
    await self.db.refresh(db_obj)
    return db_obj
```

---

### 7.4 Create Auth Endpoints

**File:** `app/api/v1/endpoints/auth.py`

**Router:** `APIRouter()` for `/auth` routes

#### Endpoint 1: POST `/register`

```python
@router.post("/register", response_model=User, status_code=201)
async def register(user_in: UserCreate, user_service: UserServiceDep):
    return await user_service.create_user(user_in)
```

**What it does:**

- Validates input with UserCreate schema
- Calls service to create user
- Returns User (without password - filtered by response_model)

#### Endpoint 2: POST `/login`

```python
@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserServiceDep
):
    user = await user_service.authenticate(form_data.username, form_data.password)

    if not user:
        raise HTTPException(401, "Incorrect username or password")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return Token(access_token=access_token, refresh_token=refresh_token)
```

**What it does:**

- Accepts OAuth2 form (username + password)
- Authenticates user via service
- Creates JWT tokens (access + refresh)
- Returns tokens to client

#### Endpoint 3: POST `/refresh`

```python
@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    user_service: UserServiceDep
):
    payload = decode_token(refresh_request.refresh_token)

    # Verify token type
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")

    # Get user
    user = await user_service.get_user(int(payload["sub"]))
    if not user.is_active:
        raise HTTPException(401, "User is inactive")

    # Create new tokens
    access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))

    return Token(access_token=access_token, refresh_token=new_refresh_token)
```

**What it does:**

- Validates refresh token
- Checks user still exists and is active
- Issues new access + refresh tokens

---

### 7.5 Create Dependency

**File:** `app/api/dependencies.py`

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.user_service import UserService


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance."""
    return UserService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
```

**Usage:**

```python
async def my_endpoint(user_service: UserServiceDep):
    # user_service is automatically injected
```

---

### 7.6 Update Router Configuration

**File:** `app/api/v1/router.py`

```python
from fastapi import APIRouter
from app.api.v1.endpoints import auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
```

**File:** `app/main.py`

```python
from app.api.v1.router import api_router

app = FastAPI()
app.include_router(api_router, prefix="/api/v1")
```

**Routes created:**

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`

---

### 7.7 Key Concepts

#### Service vs Repository

**Repository:**

- Only database operations
- CRUD methods
- No business logic

**Service:**

- Business logic and validation
- Orchestrates repository calls
- Handles errors and exceptions
- Transforms data between layers

#### Security Patterns

**Password Security:**

- Always hash before storing (`get_password_hash()`)
- Verify with bcrypt (`verify_password()`)
- Never store plain passwords

**Authentication Security:**

- Generic error messages (prevent user enumeration)
- Check `is_active` status
- Verify token type (access vs refresh)

**Token Flow:**

```
Login → Access token (30 min) + Refresh token (7 days)
  ↓
Make API calls with access token
  ↓
Access token expires → Use refresh token to get new one
  ↓
Repeat until refresh token expires (7 days)
  ↓
Login again
```

---

### 7.8 Testing Auth Flow

**1. Register:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123",
    "full_name": "Test User"
  }'
```

**2. Login:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=testuser&password=password123"
```

**3. Use Access Token:**

```bash
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

**4. Refresh Token:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

---

### 7.9 Directory Structure

```
app/
├── api/
│   ├── dependencies.py          # ✅ Created - Service dependencies
│   └── v1/
│       ├── router.py            # ✅ Created - Main router
│       └── endpoints/
│           └── auth.py          # ✅ Created - Auth routes
├── services/
│   ├── __init__.py
│   └── user_service.py          # ✅ Created - Business logic
├── db/repositories/
│   └── base.py                  # ✅ Updated - Added create() method
└── core/
    └── security.py              # Uses for password/JWT
```

---

### 7.10 What We Accomplished

✅ **Created UserService** - Business logic for user operations  
✅ **Created Auth Endpoints** - Registration, login, refresh  
✅ **Added create() to BaseRepository** - For creating new records  
✅ **Set up dependency injection** - Clean service access  
✅ **Implemented JWT authentication** - Stateless auth system

---

### 7.11 Common Issues & Solutions

**Issue 1:** `repository.create()` doesn't exist  
**Solution:** Add create() method to BaseRepository (see 7.3)

**Issue 2:** Broad exception handling in refresh endpoint  
**Solution:** Use specific exceptions (jwt.ExpiredSignatureError, jwt.JWTError)

**Issue 3:** Password in response  
**Solution:** Use `response_model=User` which excludes password

---

### 7.12 Next Steps

With auth complete, you can now:

1. **Add protected endpoints** - Require authentication
2. **Create current user dependency** - `get_current_user()`
3. **Todo endpoints** - CRUD operations for todos
4. **User endpoints** - Profile management

---

**Status:** ✅ Authentication system complete, ready for protected endpoints

## 7.5 Dependency Injection Setup (In detail)

### 7.5.1 Purpose

Create reusable dependencies for:

- **Service injection** - Provide service instances to endpoints
- **Authentication** - Extract and validate JWT tokens
- **Authorization** - Check user permissions (active, superuser)

**Benefits:**

- Clean endpoint code (no boilerplate)
- Automatic resource cleanup
- Easy to test (mockable dependencies)
- Consistent across all endpoints

---

### 7.5.2 Create Dependencies Module

**File:** `app/api/dependencies.py`

#### OAuth2 Scheme

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
```

**What it does:**

- Extracts token from `Authorization: Bearer <token>` header
- Validates header format
- Shows login form in Swagger UI
- Returns token string

---

#### Service Dependencies

```python
async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance."""
    return UserService(db)

# Type alias for cleaner code
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
```

**Usage:**

```python
@router.post("/register")
async def register(user_service: UserServiceDep):  # ← Clean!
    # Instead of:
    # user_service: UserService = Depends(get_user_service)
```

---

#### Authentication Dependencies

```python
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """Get current authenticated user from JWT token."""

    # 1. Decode JWT token
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    # 2. Extract user ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Could not validate credentials")

    # 3. Get user from database
    user = await user_service.get_user(int(user_id))

    # 4. Check if active
    if not user.is_active:
        raise HTTPException(400, "Inactive user")

    return user
```

**Dependency chain:**

```
get_current_user
  ├─ oauth2_scheme (extracts token from header)
  └─ get_user_service
     └─ get_db (creates database session)
```

---

#### Authorization Dependencies

**Active User Check:**

```python
async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(400, "Inactive user")
    return current_user

# Type alias
CurrentUser = Annotated[User, Depends(get_current_active_user)]
```

**Superuser Check:**

```python
async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Ensure user is superuser."""
    if not current_user.is_superuser:
        raise HTTPException(403, "Not enough permissions")
    return current_user
```

---

### 7.5.3 How Dependencies Connect

#### Dependency Resolution Order

```
Protected Endpoint
    ↓
CurrentUser (get_current_active_user)
    ↓
get_current_user
    ├─ oauth2_scheme → Extracts token
    └─ get_user_service
       └─ get_db → Creates session
```

**FastAPI automatically:**

1. Calls dependencies in correct order
2. Reuses dependencies within same request (single DB session)
3. Handles cleanup after response (closes session)

---

### 7.5.4 Usage in Endpoints

#### Public Endpoint (No Auth)

```python
@router.post("/register")
async def register(user_in: UserCreate, user_service: UserServiceDep):
    return await user_service.create_user(user_in)
```

**Dependencies injected:**

- `UserServiceDep` → UserService instance with DB session

---

#### Protected Endpoint (Auth Required)

```python
@router.get("/me")
async def get_profile(current_user: CurrentUser):
    return current_user
```

**Dependencies injected:**

- `CurrentUser` → Authenticated active user
- Automatically validates JWT token
- Automatically gets user from database
- Automatically checks is_active

---

#### Admin Endpoint (Superuser Only)

```python
@router.get("/users")
async def list_all_users(
    current_user: User = Depends(get_current_superuser),
    user_service: UserServiceDep
):
    return await user_service.get_users()
```

**Dependencies injected:**

- Validates token → Gets user → Checks superuser
- UserService instance
- Returns 403 if not superuser

---

### 7.5.5 Complete Request Flow

**Example: GET /users/me with token**

```
1. Request: GET /users/me
   Headers: Authorization: Bearer eyJ...

2. FastAPI sees: current_user: CurrentUser

3. Dependency resolution:
   a. oauth2_scheme
      → Extracts "eyJ..." from header

   b. get_db()
      → Creates database session

   c. get_user_service(session)
      → Creates UserService instance

   d. get_current_user(token, user_service)
      → Decodes JWT
      → Gets user from DB
      → Validates is_active
      → Returns User object

   e. get_current_active_user(user)
      → Double-checks is_active
      → Returns User object

4. Endpoint executes:
   → current_user available as User object

5. FastAPI cleanup:
   → Closes database session

6. Return response
```

---

### 7.5.6 Error Codes

| Code | Meaning      | When                                    |
| ---- | ------------ | --------------------------------------- |
| 401  | Unauthorized | Invalid/missing token, user not found   |
| 403  | Forbidden    | Not superuser, insufficient permissions |
| 400  | Bad Request  | Inactive user                           |

**Security best practice:**

- Use 401 for authentication failures (generic message)
- Use 403 for authorization failures (specific permission issue)

---

### 7.5.7 Type Aliases Summary

```python
# Clean type aliases for common patterns
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]

# Usage - clean and readable:
async def my_endpoint(
    user: CurrentUser,              # ← Authenticated active user
    service: UserServiceDep         # ← Service instance
):
    pass

# Instead of verbose:
async def my_endpoint(
    user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service)
):
    pass
```

---

### 7.5.8 Key Concepts

**Dependency Injection:**

- FastAPI automatically creates and injects dependencies
- Dependencies can depend on other dependencies (chaining)
- Same dependency reused within single request (cached)

**OAuth2PasswordBearer:**

- Extracts JWT from Authorization header
- Provides Swagger UI login integration
- Raises 401 if header missing/invalid

**Type Hints:**

- `Annotated[Type, Depends(func)]` for dependency injection
- Type aliases make code cleaner and reusable

---

### 7.5.9 Directory Structure

```
app/
├── api/
│   ├── dependencies.py          # ✅ Created - All dependencies
│   └── v1/
│       └── endpoints/
│           └── auth.py          # Uses: UserServiceDep
└── services/
    └── user_service.py          # Used by: get_user_service
```

---

### 7.5.10 Testing Dependencies

```python
# In tests, you can override dependencies:
from fastapi.testclient import TestClient

def mock_get_current_user():
    return User(id=1, username="test")

app.dependency_overrides[get_current_user] = mock_get_current_user

# Now all endpoints use mock instead of real authentication
client = TestClient(app)
response = client.get("/users/me")  # No token needed in tests!
```

---

**Status:** ✅ Dependency injection setup complete, endpoints are clean and testable
