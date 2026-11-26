# Database Models Explanation

This document provides an in-depth explanation of the User and Todo database models, their structure, relationships, and the SQLAlchemy concepts used in their implementation.

## Table of Contents

1. [Overview](#overview)
2. [User Model](#user-model)
3. [Todo Model](#todo-model)
4. [Relationships](#relationships)
5. [SQLAlchemy Concepts](#sqlalchemy-concepts)
6. [Database Schema Diagram](#database-schema-diagram)

---

## Overview

This FastAPI application uses SQLAlchemy as the Object-Relational Mapping (ORM) tool. SQLAlchemy allows us to define database tables as Python classes, where each class represents a table and each instance of the class represents a row in that table.

Both models inherit from two base classes:

- `Base`: The declarative base that SQLAlchemy uses to track all models
- `TimestampMixin`: A custom mixin that adds `created_at` and `updated_at` fields automatically

---

## User Model

### Class Definition

```python
class User(Base, TimestampMixin):
```

**Explanation:**

- `User` is the class name that represents the users table
- `Base` is SQLAlchemy's declarative base - all models must inherit from this
- `TimestampMixin` adds automatic timestamp fields (created_at, updated_at)
- Multiple inheritance allows the class to have features from both parent classes

### Table Name

```python
__tablename__ = "users"
```

**Explanation:**

- This tells SQLAlchemy what the actual database table should be called
- Without this, SQLAlchemy would use the class name (User) and make it lowercase
- Explicitly setting it gives you control over the exact table name

### Primary Key Field

```python
id: Mapped[int] = mapped_column(primary_key=True, index=True)
```

**Detailed breakdown:**

**`id:`**

- The field name that will be used in Python code and as the column name in the database

**`Mapped[int]`**

- This is SQLAlchemy 2.0 type annotation syntax
- `Mapped` is a special type hint that tells SQLAlchemy this is a database column
- `[int]` specifies the Python type (integer)
- This helps with IDE autocomplete and type checking

**`mapped_column(...)`**

- The function that creates the actual database column
- Replaces the older `Column()` syntax from SQLAlchemy 1.x

**`primary_key=True`**

- Makes this column the primary key of the table
- Primary keys must be unique and cannot be null
- Used to uniquely identify each row
- Automatically creates an index

**`index=True`**

- Creates a database index on this column
- Indexes speed up queries that search by this column
- Primary keys are automatically indexed, so this is redundant here but shown for clarity

### Email Field

```python
email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
```

**Detailed breakdown:**

**`Mapped[str]`**

- Indicates this column stores text (string) data in Python

**`String(255)`**

- SQLAlchemy column type for variable-length strings
- `255` is the maximum character length
- In the database, this becomes VARCHAR(255)
- 255 is a common choice because some databases have optimization thresholds at 255

**`unique=True`**

- Enforces uniqueness at the database level
- No two users can have the same email
- Database will reject INSERT or UPDATE that creates duplicates
- Automatically creates a unique constraint

**`index=True`**

- Creates a B-tree index on this column
- Dramatically speeds up queries like `SELECT * FROM users WHERE email = 'user@example.com'`
- Essential for login operations which search by email

**`nullable=False`**

- This column cannot contain NULL values
- Database will reject any INSERT or UPDATE that tries to leave this blank
- Equivalent to `NOT NULL` in SQL

### Username Field

```python
username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
```

**Explanation:**

- Similar to email but with a shorter maximum length (50 characters)
- Also unique and indexed for fast lookups during login
- Usernames are typically shorter than emails, hence the smaller size

### Full Name Field

```python
full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

**Detailed breakdown:**

**`Mapped[str | None]`**

- Python 3.10+ union type syntax
- Means this field can be either a string OR None (null)
- The `| None` indicates it is optional

**`nullable=True`**

- This column CAN contain NULL values
- Users can register without providing their full name
- Makes the field optional in the database

**Why no index?**

- Full name is not typically used in WHERE clauses for searching
- Indexing every column wastes disk space and slows down INSERT/UPDATE
- Only index columns that are frequently searched or joined

### Hashed Password Field

```python
hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
```

**Explanation:**

- Stores the bcrypt hash of the user's password, not the actual password
- Never store passwords in plain text
- String(255) because bcrypt hashes are typically 60 characters, but we allow room for longer hashes
- Not indexed because you never search by password hash
- nullable=False because every user must have a password

### Boolean Status Fields

```python
is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

**Detailed breakdown:**

**`Mapped[bool]`**

- Boolean type in Python (True/False)
- In PostgreSQL, this becomes the BOOLEAN type
- In MySQL, this becomes TINYINT(1)

**`Boolean`**

- SQLAlchemy's database-agnostic boolean column type
- Handles differences between database systems

**`default=True` / `default=False`**

- Python-side default value
- When you create a User object without specifying this field, it gets this value
- This is applied before the object is sent to the database

**Why two separate flags?**

- `is_active`: For soft-deletion or account suspension (user can be deactivated without deletion)
- `is_superuser`: For admin privileges (separate from active status)
- Allows flexible user management

### Relationships

```python
todos: Mapped[list["Todo"]] = relationship(
    "Todo", back_populates="owner", cascade="all, delete-orphan"
)
```

**Detailed breakdown:**

**`todos:`**

- Field name used in Python code
- Not a database column (no mapped_column)
- Exists only in Python, SQLAlchemy manages it

**`Mapped[list["Todo"]]`**

- Type hint indicating this returns a list of Todo objects
- `"Todo"` is a string because the Todo class is defined later (forward reference)
- When you access `user.todos`, you get a Python list

**`relationship(...)`**

- SQLAlchemy function that defines relationships between models
- Creates a virtual field that SQLAlchemy populates automatically
- Allows navigation: `user.todos` gives all todos belonging to the user

**`"Todo"`**

- The target model class name
- String because of forward reference (Todo defined after User)

**`back_populates="owner"`**

- Creates a bidirectional relationship
- The Todo model has an `owner` field that points back to User
- Keeps both sides synchronized automatically
- When you add a todo to `user.todos`, the todo's `owner` is automatically set

**`cascade="all, delete-orphan"`**

- Defines what happens to todos when a user is deleted
- `"all"`: All operations cascade (save, update, delete, etc.)
- `"delete-orphan"`: If a todo is removed from `user.todos`, it is deleted from the database
- Result: Deleting a user automatically deletes all their todos
- Prevents orphaned records (todos without an owner)

### Representation Method

```python
def __repr__(self) -> str:
    return f"<User(id={self.id}, email={self.email}, username={self.username})>"
```

**Explanation:**

- Special Python method for string representation
- Used when you print a User object or view it in a debugger
- Makes debugging easier by showing key identifying information
- Returns a string like: `<User(id=1, email=user@example.com, username=john_doe)>`

---

## Todo Model

### Enumerations

Before defining the Todo model, two enums are created:

#### TodoPriority Enum

```python
class TodoPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
```

**Explanation:**

- Python's Enum class for defining a fixed set of values
- Inherits from both `str` and `Enum`
- Inheriting from `str` makes enum members string-serializable (important for JSON APIs)
- Restricts priority to exactly four values
- In the database, stores the string value ("low", "medium", etc.)
- In Python code, you use `TodoPriority.HIGH` instead of magic strings

**Benefits:**

- Type safety: Cannot assign invalid priority values
- IDE autocomplete: Your editor knows the valid options
- Self-documenting: Clear what values are allowed
- Prevents typos: `TodoPriority.HIHG` gives an error, `"hihg"` does not

#### TodoStatus Enum

```python
class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

**Explanation:**

- Similar to TodoPriority but for tracking todo status
- Represents the lifecycle of a todo item
- Stored as strings in the database
- Provides a clear state machine for todos

### Class Definition

```python
class Todo(Base, TimestampMixin):
    __tablename__ = "todos"
```

**Explanation:**

- Same inheritance pattern as User
- Creates a table named "todos"

### Basic Fields

#### ID Field

```python
id: Mapped[int] = mapped_column(primary_key=True, index=True)
```

Same as User's id field - auto-incrementing primary key.

#### Title Field

```python
title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
```

**Explanation:**

- Maximum 200 characters for the todo title
- Required field (nullable=False)
- Indexed because we search todos by title
- String(200) is sufficient for a short title while not being too restrictive

#### Description Field

```python
description: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Detailed breakdown:**

**`Text`**

- SQLAlchemy column type for long text
- No character limit (database-dependent, but typically 65,535+ characters)
- In PostgreSQL becomes TEXT
- In MySQL becomes TEXT
- Use Text for long content, String for short content

**Why nullable?**

- Not all todos need detailed descriptions
- A title might be sufficient
- Allows quick todo creation

#### Completed Field

```python
completed: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
```

**Explanation:**

- Boolean flag for completion status
- Defaults to False (uncompleted)
- Indexed because we frequently filter by completion status
- Common queries: "Show all incomplete todos"

#### Priority Field

```python
priority: Mapped[TodoPriority] = mapped_column(
    default=TodoPriority.MEDIUM, nullable=False, index=True
)
```

**Detailed breakdown:**

**`Mapped[TodoPriority]`**

- Type annotation using the TodoPriority enum
- SQLAlchemy knows to treat this as an enum
- In Python, you work with enum members
- In database, stores the string value

**`default=TodoPriority.MEDIUM`**

- If no priority specified, defaults to MEDIUM
- Reasonable default (not everything is urgent)

**`index=True`**

- Indexed because users filter by priority
- Enables fast queries: "Show all high priority todos"

#### Status Field

```python
status: Mapped[TodoStatus] = mapped_column(
    default=TodoStatus.PENDING, nullable=False, index=True
)
```

**Explanation:**

- Similar to priority but uses TodoStatus enum
- Defaults to PENDING (newly created todos)
- Indexed for filtering by status
- Separates completion (boolean) from status (enum) for more granular state tracking

#### Category Field

```python
category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
```

**Explanation:**

- Optional text field for categorizing todos
- Examples: "work", "personal", "shopping", "urgent"
- Nullable because not all todos need categories
- Indexed because users filter todos by category
- String(50) is sufficient for category names

#### Due Date Field

```python
due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**Detailed breakdown:**

**`Mapped[datetime | None]`**

- Python's datetime type from the datetime module
- Optional field (can be None)

**`DateTime(timezone=True)`**

- SQLAlchemy column type for dates and times
- `timezone=True` is critical: stores timezone-aware datetimes
- In PostgreSQL, becomes TIMESTAMP WITH TIME ZONE
- Prevents timezone-related bugs
- Always stores in UTC internally

**Why nullable?**

- Not all todos have deadlines
- Users can create quick todos without setting due dates

**Why no index?**

- Less frequently used in WHERE clauses
- Range queries on dates can be slower even with indexes
- Trade-off: save disk space and faster inserts

### Foreign Key

```python
owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
```

**Detailed breakdown:**

**`owner_id`**

- Column name that stores the user's ID who owns this todo
- Physical column in the database
- Stores an integer

**`ForeignKey("users.id")`**

- Creates a foreign key constraint in the database
- `"users.id"` refers to the id column in the users table
- Enforces referential integrity at the database level
- Cannot insert a todo with an owner_id that does not exist in users table
- Database will reject invalid foreign keys

**`nullable=False`**

- Every todo MUST have an owner
- Cannot create orphaned todos
- Business rule: todos always belong to someone

**`index=True`**

- Critical for performance
- Frequent query: "Get all todos for user 123"
- Without index, database must scan entire todos table
- With index, lookup is instant

### Relationship to User

```python
owner: Mapped["User"] = relationship("User", back_populates="todos")
```

**Detailed breakdown:**

**`owner:`**

- Virtual field (not a database column)
- When you access `todo.owner`, SQLAlchemy automatically fetches the User

**`Mapped["User"]`**

- Type hint: this field returns a User object
- String "User" is a forward reference

**`relationship("User", ...)`**

- Defines the relationship to the User model
- SQLAlchemy uses owner_id to fetch the correct User

**`back_populates="todos"`**

- Matches the `todos` field in the User model
- Creates bidirectional relationship
- Keeps both sides in sync

**How it works:**

- When you access `todo.owner`, SQLAlchemy executes: `SELECT * FROM users WHERE id = todo.owner_id`
- When you access `user.todos`, SQLAlchemy executes: `SELECT * FROM todos WHERE owner_id = user.id`
- Both sides stay synchronized

---

## Relationships

### One-to-Many Relationship

The User and Todo models demonstrate a classic one-to-many relationship:

- One User can have many Todos
- Each Todo belongs to exactly one User

### How It Works

**From the User side:**

```python
user = session.get(User, 1)
todos = user.todos  # SQLAlchemy loads all todos where owner_id = 1
```

**From the Todo side:**

```python
todo = session.get(Todo, 1)
owner = todo.owner  # SQLAlchemy loads the user where id = todo.owner_id
```

### Cascade Delete Behavior

When you delete a user:

```python
session.delete(user)
session.commit()
```

Because of `cascade="all, delete-orphan"`:

1. SQLAlchemy finds all todos where `owner_id = user.id`
2. Deletes all those todos
3. Then deletes the user
4. All in one transaction (atomic)

This prevents orphaned todos in the database.

---

## SQLAlchemy Concepts

### Mapped Type Annotations (New in SQLAlchemy 2.0)

**Old way (SQLAlchemy 1.x):**

```python
id = Column(Integer, primary_key=True)
email = Column(String(255), unique=True)
```

**New way (SQLAlchemy 2.0):**

```python
id: Mapped[int] = mapped_column(primary_key=True)
email: Mapped[str] = mapped_column(String(255), unique=True)
```

**Benefits:**

- Type checkers (mypy) can verify your code
- IDE autocomplete works better
- More Pythonic and explicit
- Separates Python type (Mapped[int]) from SQL type (Integer)

### Declarative Base

```python
class User(Base, TimestampMixin):
```

**What is Base?**

- Created by SQLAlchemy's `declarative_base()` function
- Registry that tracks all your models
- Provides common functionality to all models
- Required for SQLAlchemy to recognize a class as a model

### Mixins

```python
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
```

**Benefits:**

- DRY principle: Define once, use everywhere
- Every model automatically gets timestamps
- Consistent behavior across all tables

### Indexes

**What are indexes?**

- Data structures that improve query performance
- Like an index in a book: helps find information quickly
- Trade-off: Faster reads, slower writes, more disk space

**When to index:**

- Primary keys (automatic)
- Foreign keys (for joins)
- Columns in WHERE clauses
- Columns in ORDER BY clauses
- Unique columns

**When NOT to index:**

- Columns rarely searched
- Small tables (< 1000 rows)
- Columns with low cardinality (few unique values)
- Columns frequently updated

### Constraints

**Primary Key Constraint:**

- Ensures uniqueness
- Cannot be NULL
- One per table

**Unique Constraint:**

- Ensures uniqueness
- Can be NULL (depending on database)
- Multiple allowed per table

**Foreign Key Constraint:**

- Ensures referential integrity
- Value must exist in referenced table
- Prevents orphaned records

**Not Null Constraint:**

- Column must have a value
- Database rejects NULL values

---

## Database Schema Diagram

```
+------------------+          +------------------+
|      users       |          |      todos       |
+------------------+          +------------------+
| id (PK)          |<------+  | id (PK)          |
| email (UQ, IDX)  |       |  | title (IDX)      |
| username (UQ,IDX)|       |  | description      |
| full_name        |       |  | completed (IDX)  |
| hashed_password  |       |  | priority (IDX)   |
| is_active        |       |  | status (IDX)     |
| is_superuser     |       |  | category (IDX)   |
| created_at       |       |  | due_date         |
| updated_at       |       |  | owner_id (FK,IDX)|
+------------------+       |  | created_at       |
                           +--| updated_at       |
                              +------------------+

Legend:
PK  = Primary Key
FK  = Foreign Key
UQ  = Unique Constraint
IDX = Indexed
```

### Relationship Explanation:

- One User (1) can have Many Todos (\*)
- Each Todo must belong to exactly one User
- The arrow shows the foreign key relationship: `todos.owner_id` references `users.id`

---

## FastAPI Integration Points

### Pydantic Integration

These SQLAlchemy models work with Pydantic schemas:

```python
# SQLAlchemy model (database)
class User(Base):
    email: Mapped[str] = mapped_column(String(255))

# Pydantic schema (API)
class UserCreate(BaseModel):
    email: EmailStr
```

SQLAlchemy handles database, Pydantic handles validation.

### Async Support

FastAPI is async, so we use:

- `asyncpg` driver for PostgreSQL
- `AsyncSession` instead of Session
- `await` for all database operations

```python
async with AsyncSession() as session:
    result = await session.execute(select(User))
```

### Dependency Injection

These models are used in FastAPI dependencies:

```python
async def get_db() -> AsyncSession:
    async with AsyncSession() as session:
        yield session
```

Then injected into route functions:

```python
@app.get("/users/")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
```

---

## Summary

**User Model:**

- Stores user authentication and profile data
- Has fields for email, username, password (hashed), and status flags
- One user can have many todos (one-to-many relationship)
- Cascade delete ensures todos are removed when user is deleted

**Todo Model:**

- Stores task information with priority, status, and categorization
- Uses enums for type-safe priority and status values
- Belongs to exactly one user via foreign key
- Supports optional fields (description, category, due_date) for flexibility

**Key SQLAlchemy Concepts Used:**

- Declarative base and mapped columns
- Type annotations with Mapped
- Relationships (one-to-many)
- Foreign keys and referential integrity
- Indexes for query performance
- Enums for restricted value sets
- Cascade operations for data consistency
- Mixins for code reusability

This schema provides a solid foundation for a production-ready todo application with proper data modeling, relationships, and performance optimizations.
