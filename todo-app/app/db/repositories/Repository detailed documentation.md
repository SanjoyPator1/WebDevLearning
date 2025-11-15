# Repository Layer Documentation - Detailed Explanation

## 📚 Table of Contents

1. [What is the Repository Pattern?](#what-is-the-repository-pattern)
2. [Base Repository (`base.py`)](#base-repository-basepy)
3. [User Repository (`user.py`)](#user-repository-userpy)
4. [How Repositories Fit in the Architecture](#how-repositories-fit-in-the-architecture)
5. [Advanced Concepts](#advanced-concepts)
6. [Usage Examples](#usage-examples)

---

## 🎯 What is the Repository Pattern?

### The Problem Without Repositories

Imagine writing database queries directly in your API endpoints:

```python
# ❌ BAD: Database logic mixed with API logic
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)
    return user

@router.get("/todos")
async def get_todos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo).where(Todo.owner_id == current_user.id))
    todos = result.scalars().all()
    return todos
```

**Problems:**

- 🔴 Database queries scattered everywhere
- 🔴 Code duplication (same queries in multiple places)
- 🔴 Hard to test (need real database)
- 🔴 Hard to change database logic (affects many files)
- 🔴 Violates Single Responsibility Principle

### The Solution: Repository Pattern

```python
# ✅ GOOD: Separate data access from business logic
@router.get("/users/{user_id}")
async def get_user(user_id: int, user_repo: UserRepository = Depends()):
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user

@router.get("/todos")
async def get_todos(todo_repo: TodoRepository = Depends()):
    todos = await todo_repo.get_by_owner(current_user.id)
    return todos
```

**Benefits:**

- ✅ Centralized data access logic
- ✅ Reusable across application
- ✅ Easy to test (can mock repositories)
- ✅ Easy to maintain (change once, works everywhere)
- ✅ Clean separation of concerns

### Repository Pattern Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Endpoints                         │
│  (Handle HTTP requests, validate input, return response) │
└─────────────────┬───────────────────────────────────────┘
                  │ Uses
                  ▼
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                          │
│     (Business logic, orchestrate operations)             │
└─────────────────┬───────────────────────────────────────┘
                  │ Uses
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Repository Layer ← YOU ARE HERE             │
│        (Data access, database operations)                │
└─────────────────┬───────────────────────────────────────┘
                  │ Uses
                  ▼
┌─────────────────────────────────────────────────────────┐
│                  Database Models                         │
│           (SQLAlchemy ORM models)                        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL Database                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🏗️ Base Repository (`base.py`)

### Complete Code Breakdown

```python
"""
Base repository pattern implementation.
Provides generic CRUD operations for all models.
"""
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

# Define a type variable bound to Base
ModelType = TypeVar("ModelType", bound=Base)
```

#### Understanding TypeVar and Generic

**What is `TypeVar`?**

A TypeVar is a placeholder for a type that will be specified later.

```python
ModelType = TypeVar("ModelType", bound=Base)
#           ↑                      ↑
#           Type variable name     Must inherit from Base
```

**Why `bound=Base`?**

This means `ModelType` can be any class that inherits from `Base`:

- ✅ `User` (inherits from Base) - Valid
- ✅ `Todo` (inherits from Base) - Valid
- ❌ `str` (doesn't inherit from Base) - Invalid
- ❌ `dict` (doesn't inherit from Base) - Invalid

**Example in action:**

```python
# When you use UserRepository
user_repo = UserRepository(db)
# ModelType = User (automatically inferred)

# When you use TodoRepository
todo_repo = TodoRepository(db)
# ModelType = Todo (automatically inferred)
```

**What is `Generic[ModelType]`?**

Makes the class generic - can work with any type that satisfies ModelType.

```python
class BaseRepository(Generic[ModelType]):
    #                  ↑
    #    This class can work with different model types
```

**Why this is powerful:**

```python
# Same BaseRepository works for different models
class UserRepository(BaseRepository[User]):    # ModelType = User
    pass

class TodoRepository(BaseRepository[Todo]):    # ModelType = Todo
    pass

# IDE knows the exact return types!
user_repo = UserRepository(db)
user = await user_repo.get(1)  # IDE knows this returns User | None

todo_repo = TodoRepository(db)
todo = await todo_repo.get(1)  # IDE knows this returns Todo | None
```

---

### The BaseRepository Class

```python
class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    This implements the Repository pattern to abstract data access logic.
    """

    def __init__(self, model: type[ModelType], db: AsyncSession):
        """
        Initialize repository with model and database session.

        Args:
            model: SQLAlchemy model class
            db: Async database session
        """
        self.model = model
        self.db = db
```

**Constructor Breakdown:**

```python
def __init__(self, model: type[ModelType], db: AsyncSession):
    #            ↑                            ↑
    #    The model class (User, Todo)    Database session
```

**What is `type[ModelType]`?**

This means "the class itself, not an instance":

```python
# ❌ WRONG - Instance of User
user_instance = User(username="john")
repo = BaseRepository(user_instance, db)  # Error!

# ✅ CORRECT - User class itself
repo = BaseRepository(User, db)  # Works!
```

**Why store both model and db?**

```python
self.model = model  # ← Know which table to query
self.db = db        # ← Know which database connection to use
```

**Usage:**

```python
# Later in methods
query = select(self.model)  # ← Uses the stored model class
result = await self.db.execute(query)  # ← Uses the stored session
```

---

### Method 1: `get()` - Get Single Record by ID

```python
async def get(self, id: int) -> ModelType | None:
    """
    Get a single record by ID.

    Args:
        id: Record ID

    Returns:
        Model instance or None if not found
    """
    result = await self.db.execute(select(self.model).where(self.model.id == id))
    return result.scalar_one_or_none()
```

**Line-by-line breakdown:**

**1. Build the query:**

```python
select(self.model).where(self.model.id == id)
#      ↑                 ↑
#  SELECT * FROM users   WHERE id = 5
```

If `self.model = User`, this generates:

```sql
SELECT * FROM users WHERE id = 5
```

If `self.model = Todo`, this generates:

```sql
SELECT * FROM todos WHERE id = 5
```

**2. Execute the query:**

```python
result = await self.db.execute(query)
#        ↑      ↑
#     Wait for   Execute query on database
#   completion
```

The `await` keyword:

- Pauses execution until query completes
- Allows other code to run meanwhile (non-blocking)
- Returns result when database responds

**3. Extract the result:**

```python
return result.scalar_one_or_none()
#             ↑
#  Get single value or None if not found
```

**What is `scalar_one_or_none()`?**

```python
# If found:
result.scalar_one_or_none()  # Returns: User(id=5, username="john")

# If not found:
result.scalar_one_or_none()  # Returns: None

# If multiple rows (error case):
result.scalar_one_or_none()  # Raises: MultipleResultsFound exception
```

**Return type explained:**

```python
-> ModelType | None
#  ↑          ↑
#  User/Todo  Or None if not found
```

**Usage example:**

```python
user_repo = UserRepository(db)
user = await user_repo.get(5)

if user:
    print(f"Found: {user.username}")
else:
    print("User not found")
```

---

### Method 2: `get_multi()` - Get Multiple Records with Pagination

```python
async def get_multi(
        self, skip: int = 0, limit: int = 100, **filters: Any
) -> list[ModelType]:
    """
    Get multiple records with pagination and filters.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        **filters: Additional filter conditions

    Returns:
        List of model instances
    """
    query = select(self.model)

    # apply filters
    for key, value in filters.items():
        if value is not None and hasattr(self.model, key):
            query = query.where(getattr(self.model, key) ==  value)

    query = query.offset(skip).limit(limit)
    result = await self.db.execute(query)
    return list(result.scalars().all())
```

**Understanding the parameters:**

**1. `skip` and `limit` (Pagination):**

```python
skip: int = 0    # How many records to skip
limit: int = 100 # Maximum records to return
```

**Example:**

```python
# Page 1: First 10 users
users = await repo.get_multi(skip=0, limit=10)   # Users 1-10

# Page 2: Next 10 users
users = await repo.get_multi(skip=10, limit=10)  # Users 11-20

# Page 3: Next 10 users
users = await repo.get_multi(skip=20, limit=10)  # Users 21-30
```

Generated SQL:

```sql
SELECT * FROM users OFFSET 0 LIMIT 10;   -- Page 1
SELECT * FROM users OFFSET 10 LIMIT 10;  -- Page 2
SELECT * FROM users OFFSET 20 LIMIT 10;  -- Page 3
```

**2. `**filters: Any` (Dynamic Filters):\*\*

The `**` means "any number of keyword arguments":

```python
# Can call with any filters
users = await repo.get_multi(is_active=True)
users = await repo.get_multi(is_active=True, is_superuser=False)
users = await repo.get_multi(username="john")
```

Inside the function, `filters` is a dictionary:

```python
filters = {"is_active": True, "is_superuser": False}
```

**Building the query:**

**Step 1: Start with base query**

```python
query = select(self.model)  # SELECT * FROM users
```

**Step 2: Apply dynamic filters**

```python
for key, value in filters.items():
    #   ↓       ↓
    # "is_active" True
    # "is_superuser" False

    if value is not None and hasattr(self.model, key):
        #  ↑                 ↑
        #  Skip None values  Check model has this attribute

        query = query.where(getattr(self.model, key) == value)
        #                   ↑
        #      Dynamically access model attribute
```

**Understanding `hasattr()` and `getattr()`:**

```python
hasattr(User, "is_active")    # True - User has is_active field
hasattr(User, "nonexistent")  # False - User doesn't have this field

getattr(User, "is_active")    # Returns: User.is_active column
```

**Why check `hasattr`?**

Prevents SQL injection or errors from invalid fields:

```python
# ✅ Safe: Field exists
await repo.get_multi(is_active=True)  # Works

# ✅ Safe: Invalid field ignored
await repo.get_multi(hacker_field=True)  # Ignored, doesn't crash
```

**Step 3: Add pagination**

```python
query = query.offset(skip).limit(limit)
#             ↑           ↑
#       Skip N records   Return max M records
```

**Step 4: Execute and return**

```python
result = await self.db.execute(query)
return list(result.scalars().all())
#      ↑    ↑       ↑
# Convert Get all  Get just the objects
# to list  rows    (not full row metadata)
```

**What is `scalars().all()`?**

```python
# Without scalars()
result.all()
# Returns: [(User(...),), (User(...),), ...]
# (Tuples with one element)

# With scalars()
result.scalars().all()
# Returns: [User(...), User(...), ...]
# (Just the objects)
```

**Complete example:**

```python
# Get active users, page 2 (skip 10, get 10 more)
users = await user_repo.get_multi(
    skip=10,
    limit=10,
    is_active=True
)

# Generates SQL:
# SELECT * FROM users
# WHERE is_active = true
# OFFSET 10 LIMIT 10
```

---

### Method 3: `create()` – Create a New Record

```python
async def create(self, obj_in: dict[str, Any]) -> ModelType:
    """
    Create a new record.

    Args:
        obj_in: Dictionary with data for new record

    Returns:
        Created model instance
    """
    db_obj = self.model(**obj_in)
    self.db.add(db_obj)
    await self.db.commit()
    await self.db.refresh(db_obj)
    return db_obj

```

**Purpose:**  
Create and store a new database record using the provided data.

---

**Step-by-step:**

**Step 1: Convert input data into a database model instance**

```python
db_obj = self.model(**obj_in)
#        ↑
# Create a new SQLAlchemy model object using keyword arguments

```

- `self.model` → SQLAlchemy model class (e.g., `User`, `Todo`)
- `obj_in` → dictionary of fields and values  
  (`{"title": "Buy milk", "priority": "HIGH"}`)

This line transforms raw dict data into a proper ORM object ready to be inserted.

---

**Step 2: Add the object to the database session**

```python
self.db.add(db_obj)
#        ↑
# Stage the object for insertion, but NOT saved yet

```

`add()` tells SQLAlchemy: “This object should be inserted in the next commit.”

---

**Step 3: Commit the transaction**

```python
await self.db.commit()
#     ↑
# Executes the INSERT operation in the database

```

Actual SQL `INSERT` happens at this step.

---

### **Step 4: Refresh the object with database-generated values**

```python
await self.db.refresh(db_obj)
#     ↑
# Reload object from DB to populate fields like id, timestamps, etc.

```

Why needed?

- Auto-generated fields (like `id`, `created_at`) won’t be available until `refresh()` loads them from DB.

---

**Step 5: Return the created object**

```python
return db_obj
# Return populated model instance

```

Caller receives the full model object, NOT raw dictionary.

---

**Database operations:**

Here’s what SQLAlchemy generates internally:

```sql
INSERT INTO todos (title, description, priority, user_id)
VALUES ('Buy milk', 'Buy dairy milk', 'HIGH', 1)
RETURNING id, created_at, updated_at;

```

After `refresh()`, the model instance includes:

```python
Todo(
    id=42,
    title="Buy milk",
    priority="HIGH",
    created_at=datetime(...),
    updated_at=datetime(...)
)

```

---

**Usage example:**

```python
new_todo = await todo_repo.create({
    "title": "Study FastAPI",
    "description": "Learn repository pattern",
    "priority": "MEDIUM",
    "user_id": 1
})

print(new_todo.id)         # e.g., 17
print(new_todo.created_at) # auto-filled

```

---

**Why accept a dictionary instead of a Pydantic model?**

Flexibility:

```python
# Convert Pydantic → dict automatically
todo_data = todo_in.dict()
await todo_repo.create(todo_data)

```

This makes the repository layer independent of FastAPI/Pydantic.

---

**When to use `create()`?**

- Signup new user
- Create new todo
- Save any entity into DB for the first time

### Method 4: `update()` - Update Existing Record

```python
async def update(self, db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
    """
    Update an existing record.

    Args:
        db_obj: Existing database object
        obj_in: Dictionary with updated data

    Returns:
        Updated model instance
    """
    for field, value in obj_in.items():
        if value is not None and hasattr(db_obj, field):
            setattr(db_obj, field, value)

    await self.db.commit()
    await self.db.refresh(db_obj)
    return db_obj
```

**Parameters:**

```python
db_obj: ModelType           # Existing object from database
obj_in: dict[str, Any]      # New values to update
```

**Example:**

```python
# Get existing user
user = await user_repo.get(5)

# Update some fields
updated_user = await user_repo.update(
    db_obj=user,
    obj_in={
        "full_name": "John Doe",
        "email": "john@example.com"
    }
)
```

**Step-by-step breakdown:**

**Step 1: Update object attributes**

```python
for field, value in obj_in.items():
    #   ↓         ↓
    # "full_name" "John Doe"
    # "email"     "john@example.com"

    if value is not None and hasattr(db_obj, field):
        #  ↑                 ↑
        # Skip None         Check field exists on object

        setattr(db_obj, field, value)
        #       ↑       ↑      ↑
        #    Object   Field   New value
```

**What is `setattr()`?**

```python
# These are equivalent:
setattr(user, "full_name", "John Doe")
user.full_name = "John Doe"

# Dynamic version (field name from variable):
field_name = "email"
setattr(user, field_name, "john@example.com")
```

**Why use `setattr()`?**

Allows dynamic field updates without knowing field names in advance:

```python
# Can update any fields dynamically
updates = {"username": "john", "email": "john@example.com"}
for field, value in updates.items():
    setattr(user, field, value)
```

**Step 2: Commit the transaction**

```python
await self.db.commit()
#     ↑
# Save changes to database
```

**What happens during commit?**

```
Before commit:
- Changes only in Python object (user.full_name = "John Doe")
- Database still has old value

After commit:
- Changes written to database
- SQL: UPDATE users SET full_name = 'John Doe' WHERE id = 5
```

**Step 3: Refresh the object**

```python
await self.db.refresh(db_obj)
#                     ↑
#          Reload object from database
```

**Why refresh?**

Gets database-generated values like `updated_at`:

```
Before refresh:
user.updated_at = "2024-01-01 10:00:00"  # Old value

After refresh:
user.updated_at = "2024-01-01 11:30:00"  # New value from database
```

**Step 4: Return updated object**

```python
return db_obj  # Now has all latest values
```

**Full flow:**

```python
# 1. Get user
user = await user_repo.get(5)
print(user.full_name)  # "John Smith"

# 2. Update
updated = await user_repo.update(user, {"full_name": "John Doe"})

# 3. Check result
print(updated.full_name)  # "John Doe"
print(updated.updated_at) # "2024-01-01 11:30:00" (refreshed from DB)
```

---

### Method 5: `delete()` - Delete Record by ID

```python
async def delete(self, id: int) -> bool:
    """
    Delete a record by ID.

    Args:
        id: Record ID

    Returns:
        True if deleted, False if not found
    """
    db_obj = await self.get(id)
    if db_obj:
        await self.db.delete(db_obj)
        await self.db.commit()
        return True
    return False
```

**Step-by-step:**

**Step 1: Try to get the object**

```python
db_obj = await self.get(id)
#              ↑
#  Reuses the get() method we already wrote
```

**Step 2: If found, delete it**

```python
if db_obj:  # If object exists
    await self.db.delete(db_obj)
    #     ↑
    # Mark for deletion (doesn't delete yet)

    await self.db.commit()
    #     ↑
    # Actually delete from database

    return True  # Success
```

**Step 3: If not found, return False**

```python
return False  # Object didn't exist
```

**Database operations:**

```sql
-- If object exists:
DELETE FROM users WHERE id = 5;
-- Returns: True

-- If object doesn't exist:
-- (No SQL executed)
-- Returns: False
```

**Usage example:**

```python
# Try to delete user
was_deleted = await user_repo.delete(5)

if was_deleted:
    print("User deleted successfully")
else:
    print("User not found")
```

**Why return bool instead of raising exception?**

Gives caller flexibility:

```python
# Caller can decide how to handle
if not await repo.delete(id):
    raise HTTPException(status_code=404, detail="Not found")
```

---

### Method 6: `count()` - Count Records with Filters

```python
async def count(self, **filters: Any) -> int:
    """
    Count records with optional filters.

    Args:
        **filters: Filter conditions

    Returns:
        Number of matching records
    """
    query = select(self.model)

    # Apply filters
    for key, value in filters.items():
        if value is not None and hasattr(self.model, key):
            query = query.where(getattr(self.model, key) == value)

    result = await self.db.execute(query)
    return len(result.scalars().all())
```

**Similar to `get_multi()` but returns count instead of objects.**

**Examples:**

```python
# Count all users
total_users = await user_repo.count()
# SQL: SELECT * FROM users

# Count active users
active_count = await user_repo.count(is_active=True)
# SQL: SELECT * FROM users WHERE is_active = true

# Count active superusers
admin_count = await user_repo.count(is_active=True, is_superuser=True)
# SQL: SELECT * FROM users WHERE is_active = true AND is_superuser = true
```

**Return value:**

```python
return len(result.scalars().all())
#      ↑   ↑
# Count  Get all matching rows
```

**Usage in pagination:**

```python
# Get total count for pagination metadata
total = await user_repo.count(is_active=True)
page_size = 10
total_pages = (total + page_size - 1) // page_size

print(f"Total: {total} users")
print(f"Pages: {total_pages}")
```

---

## 👤 User Repository (`user.py`)

### Extending BaseRepository

```python
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    """Repository for User model with custom methods."""

    def __init__(self, db: AsyncSession):
        """Initialize user repository."""
        super().__init__(User, db)
        #     ↑         ↑     ↑
        # Call parent   Model Session
```

**Understanding the inheritance:**

```python
class UserRepository(BaseRepository[User]):
#                    ↑               ↑
#    Inherits from   ModelType = User
```

**What UserRepository gets automatically:**

```python
user_repo = UserRepository(db)

# All these methods work automatically:
user = await user_repo.get(5)              # ← From BaseRepository
users = await user_repo.get_multi()        # ← From BaseRepository
await user_repo.update(user, {...})        # ← From BaseRepository
await user_repo.delete(5)                  # ← From BaseRepository
count = await user_repo.count()            # ← From BaseRepository
```

**Plus custom User-specific methods:**

```python
user = await user_repo.get_by_email("john@example.com")  # ← User-specific
user = await user_repo.get_by_username("john")           # ← User-specific
exists = await user_repo.exists_by_email("...")          # ← User-specific
```

**Why `super().__init__(User, db)`?**

Calls the parent class constructor:

```python
super().__init__(User, db)
# Equivalent to:
# BaseRepository.__init__(self, User, db)
# Which sets:
# self.model = User
# self.db = db
```

---

### Custom Method 1: `get_by_email()`

```python
async def get_by_email(self, email: str) -> User | None:
    """
    Get user by email address.

    Args:
        email: User's email address

    Returns:
        User instance or None
    """
    result = await self.db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
```

**Why not use the base `get()` method?**

`get()` only works with ID:

```python
# ✅ Works
user = await repo.get(5)  # Get by ID

# ❌ Can't do this
user = await repo.get("john@example.com")  # ID must be int
```

**SQL generated:**

```sql
SELECT * FROM users WHERE email = 'john@example.com'
```

**Usage:**

```python
# During login
user = await user_repo.get_by_email("john@example.com")
if user:
    # Verify password
    if verify_password(password, user.hashed_password):
        # Login successful
```

---

### Custom Method 2: `get_by_username()`

```python
async def get_by_username(self, username: str) -> User | None:
    """
    Get user by username.

    Args:
        username: User's username

    Returns:
        User instance or None
    """
    result = await self.db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()
```

**SQL generated:**

```sql
SELECT * FROM users WHERE username = 'john'
```

**Usage:**

```python
# Check if username is taken
existing = await user_repo.get_by_username("john")
if existing:
    raise HTTPException(status_code=400, detail="Username already taken")
```

---

### Custom Method 3: `get_by_email_or_username()`

```python
async def get_by_email_or_username(self, identifier: str) -> User | None:
    """
    Get user by email or username.

    Args:
        identifier: Email or username

    Returns:
        User instance or None
    """
    result = await self.db.execute(
        select(User).where(or_(User.email == identifier, User.username == identifier))
    )
    return result.scalar_one_or_none()
```

**Understanding `or_()`:**

```python
or_(User.email == identifier, User.username == identifier)
#   ↑                          ↑
# Condition 1                 Condition 2
```

**SQL generated:**

```sql
SELECT * FROM users
WHERE email = 'john@example.com' OR username = 'john@example.com'
```

**Why is this useful?**

Allows flexible login - user can use either email or username:

```python
# Login with email
user = await user_repo.get_by_email_or_username("john@example.com")

# Login with username
user = await user_repo.get_by_email_or_username("john")

# Both work!
```

**Usage in authentication:**

```python
async def authenticate(identifier: str, password: str):
    # User can login with email OR username
    user = await user_repo.get_by_email_or_username(identifier)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
```

---

### Custom Method 4: `exists_by_email()`

```python
async def exists_by_email(self, email: str) -> bool:
    """
    Check if user exists by email.

    Args:
        email: Email to check

    Returns:
        True if exists, False otherwise
    """
    user = await self.get_by_email(email)
    return user is not None
```

**Why have a separate exists method?**

**More readable:**

```python
# ✅ Clear intent
if await user_repo.exists_by_email("john@example.com"):
    raise HTTPException(400, "Email already registered")

# ❌ Less clear
if await user_repo.get_by_email("john@example.com"):
    raise HTTPException(400, "Email already registered")
```

**More efficient (could be optimized):**

```python
# Current implementation
user = await self.get_by_email(email)
return user is not None

# Could be optimized to:
result = await self.db.execute(
    select(exists().where(User.email == email))
)
return result.scalar()
# SQL: SELECT EXISTS(SELECT 1 FROM users WHERE email = '...')
```

**Usage:**

```python
# Before registration
if await user_repo.exists_by_email(email):
    raise HTTPException(status_code=400, detail="Email already exists")
```

---

### Custom Method 5: `exists_by_username()`

```python
async def exists_by_username(self, username: str) -> bool:
    """
    Check if user exists by username.

    Args:
        username: Username to check

    Returns:
        True if exists, False otherwise
    """
    user = await self.get_by_username(username)
    return user is not None
```

**Same concept as `exists_by_email()`.**

**Usage:**

```python
# Validation during registration
if await user_repo.exists_by_username(username):
    raise HTTPException(status_code=400, detail="Username already taken")
```

---

### Custom Method 6: `get_active_users()`

```python
async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
    """
    Get all active users.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records

    Returns:
        List of active users
    """
    return await self.get_multi(skip=skip, limit=limit, is_active=True)
    #                                                    ↑
    #                             Uses the dynamic filters from BaseRepository
```

**This leverages the base `get_multi()` method:**

```python
# Instead of writing:
result = await self.db.execute(
    select(User).where(User.is_active == True).offset(skip).limit(limit)
)
return result.scalars().all()

# We can just use:
return await self.get_multi(skip=skip, limit=limit, is_active=True)
```

**SQL generated:**

```sql
SELECT * FROM users
WHERE is_active = true
OFFSET 0 LIMIT 100
```

**Usage:**

```python
# Admin dashboard - show all active users
active_users = await user_repo.get_active_users(skip=0, limit=50)
```

---

## 🔗 How Repositories Fit in the Architecture

### Complete Flow Example

```python
# 1. API Endpoint receives request
@router.post("/auth/register")
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # 2. Create repository instance
    user_repo = UserRepository(db)

    # 3. Check if email exists
    if await user_repo.exists_by_email(user_in.email):
        raise HTTPException(400, "Email already registered")

    # 4. Check if username exists
    if await user_repo.exists_by_username(user_in.username):
        raise HTTPException(400, "Username already taken")

    # 5. Create user (this would be in a service layer)
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hashed_password
    )

    # 6. Save to database
    self.db.add(user)
    await self.db.commit()
    await self.db.refresh(user)

    return user
```

### Layer Separation

```
┌─────────────────────────────────────────┐
│  Endpoint: /auth/register               │
│  - Validates input (Pydantic)           │
│  - Handles HTTP concerns                │
│  - Returns HTTP response                │
└─────────────┬───────────────────────────┘
              │ Calls
              ▼
┌─────────────────────────────────────────┐
│  Service: AuthService                   │
│  - Business logic                       │
│  - Orchestrates operations              │
│  - Checks business rules                │
└─────────────┬───────────────────────────┘
              │ Uses
              ▼
┌─────────────────────────────────────────┐
│  Repository: UserRepository             │
│  - Data access only                     │
│  - CRUD operations                      │
│  - Database queries                     │
└─────────────┬───────────────────────────┘
              │ Queries
              ▼
┌─────────────────────────────────────────┐
│  Database: PostgreSQL                   │
└─────────────────────────────────────────┘
```

---

## 🧪 Advanced Concepts

### Why Async?

**Synchronous (Blocking):**

```python
def get_user(id):
    user = db.query(User).filter(User.id == id).first()  # ← Blocks for 100ms
    return user

# Server can only handle one request at a time
Request 1 → Wait 100ms → Response
Request 2 → Wait 100ms → Response
Total: 200ms for 2 requests
```

**Asynchronous (Non-blocking):**

```python
async def get_user(id):
    user = await db.execute(select(User).where(User.id == id))  # ← Yields control
    return user

# Server can handle multiple requests concurrently
Request 1 → Start query → Yield
Request 2 → Start query → Yield
Request 1 → Complete → Response
Request 2 → Complete → Response
Total: 100ms for 2 requests (parallel)
```

**Benefits:**

- ⚡ Better performance under load
- 🔄 Can handle more concurrent requests
- 💰 Lower server costs (fewer servers needed)

---

### Generic Programming Benefits

**Without Generics:**

```python
# Need separate repository for each model
class UserRepository:
    async def get(self, id: int) -> User | None:
        # Code for getting user
        pass

class TodoRepository:
    async def get(self, id: int) -> Todo | None:
        # Duplicate code for getting todo
        pass

# Code duplication! 😞
```

**With Generics:**

```python
# One base class, reused for all models
class BaseRepository(Generic[ModelType]):
    async def get(self, id: int) -> ModelType | None:
        # Shared code
        pass

class UserRepository(BaseRepository[User]):
    pass  # Inherits get()

class TodoRepository(BaseRepository[Todo]):
    pass  # Inherits get()

# No duplication! 😊
```

---

### Repository vs Direct Database Access

**Direct Access (Bad):**

```python
@router.get("/users/{id}")
async def get_user(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == id))
    return result.scalar_one_or_none()

@router.get("/profile")
async def get_profile(current_user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == current_user_id))
    return result.scalar_one_or_none()

# Same query duplicated! 😞
```

**Repository Pattern (Good):**

```python
@router.get("/users/{id}")
async def get_user(id: int, user_repo: UserRepository = Depends()):
    return await user_repo.get(id)

@router.get("/profile")
async def get_profile(current_user_id: int, user_repo: UserRepository = Depends()):
    return await user_repo.get(current_user_id)

# Reusable! 😊
```

---

## 📝 Usage Examples

### Example 1: User Registration

```python
async def register_user(user_in: UserCreate, db: AsyncSession):
    user_repo = UserRepository(db)

    # Check duplicates
    if await user_repo.exists_by_email(user_in.email):
        raise ValueError("Email already exists")

    if await user_repo.exists_by_username(user_in.username):
        raise ValueError("Username already taken")

    # Create user
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hashed_password
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
```

### Example 2: User Authentication

```python
async def authenticate_user(identifier: str, password: str, db: AsyncSession):
    user_repo = UserRepository(db)

    # Find user by email or username
    user = await user_repo.get_by_email_or_username(identifier)

    if not user:
        return None

    # Check if active
    if not user.is_active:
        return None

    # Verify password
    if not verify_password(password, user.hashed_password):
        return None

    return user
```

### Example 3: Get User's Todos

```python
async def get_user_todos(user_id: int, db: AsyncSession):
    user_repo = UserRepository(db)

    # Get user
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Access todos through relationship
    return user.todos
```

### Example 4: Update User Profile

```python
async def update_profile(
    user_id: int,
    updates: dict[str, Any],
    db: AsyncSession
):
    user_repo = UserRepository(db)

    # Get user
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Check for email/username conflicts
    if "email" in updates:
        if await user_repo.exists_by_email(updates["email"]):
            raise HTTPException(400, "Email already exists")

    if "username" in updates:
        if await user_repo.exists_by_username(updates["username"]):
            raise HTTPException(400, "Username already taken")

    # Update
    updated_user = await user_repo.update(user, updates)
    return updated_user
```

---

## 🎯 Key Takeaways

### Repository Pattern Benefits

1. **Separation of Concerns**

   - Data access logic separated from business logic
   - Endpoints don't know about database details

2. **Reusability**

   - Write query once, use everywhere
   - Base class provides common operations

3. **Testability**

   - Easy to mock repositories in tests
   - Can test without real database

4. **Maintainability**

   - Change query in one place
   - Consistent data access patterns

5. **Type Safety**
   - Generics provide IDE autocomplete
   - Catch errors at compile time

### When to Use Repositories

✅ **Use for:**

- CRUD operations
- Simple queries
- Data access abstraction

❌ **Don't use for:**

- Complex business logic (use services)
- HTTP concerns (keep in endpoints)
- Validation (use Pydantic schemas)

---

This repository layer provides a clean, reusable foundation for all your data access needs!
