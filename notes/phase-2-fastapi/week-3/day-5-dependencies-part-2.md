# Day 5: Dependency Injection - Part 2

**Date**: Week 3, Day 5  
**Phase**: 2 - FastAPI Mastery  
**Topic**: Advanced Dependency Patterns and Production Techniques

---

## Table of Contents

1. [Recap: Dependencies Part 1](#recap-dependencies-part-1)
2. [Dependencies with Yield (Cleanup)](#dependencies-with-yield-cleanup)
3. [Dependency Caching](#dependency-caching)
4. [Global Dependencies](#global-dependencies)
5. [Router-Level Dependencies](#router-level-dependencies)
6. [Dependency Overriding for Testing](#dependency-overriding-for-testing)
7. [Security Dependencies](#security-dependencies)
8. [Database Session Dependencies](#database-session-dependencies)
9. [Advanced Dependency Patterns](#advanced-dependency-patterns)
10. [Complete Production Examples](#complete-production-examples)

---

## Recap: Dependencies Part 1

Before diving into advanced patterns, let's quickly recap what we learned in Part 1:

### What We Covered in Part 1

**Day 4 covered the fundamentals:**

1. **Understanding Dependency Injection**

   - What DI is and why it matters
   - How FastAPI's DI system works
   - Benefits: reusability, testability, maintainability

2. **Function Dependencies**

   - Simple dependencies
   - Dependencies with parameters
   - Reusable dependencies
   - Multiple dependencies

3. **Class-Based Dependencies**

   - Using classes as dependencies
   - `__init__` for parameter extraction
   - Type annotation shortcuts (`Depends()` with no argument)
   - Helper methods in classes

4. **Dependency Chains**

   - Dependencies depending on other dependencies
   - Multi-level chains
   - How FastAPI resolves chains automatically

5. **Common Patterns**
   - Pagination dependencies
   - Filtering dependencies
   - Sorting dependencies
   - Database connection basics

### Quick Reference from Part 1

```python
# Function dependency (Part 1)
def get_current_user(token: str = Header(...)):
    return validate_token(token)

# Class dependency (Part 1)
class PaginationParams:
    def __init__(self, skip: int = 0, limit: int = 10):
        self.skip = skip
        self.limit = limit

# Dependency chain (Part 1)
def get_token(auth: str = Header(...)):
    return extract_token(auth)

def get_user(token: str = Depends(get_token)):
    return fetch_user(token)

# Usage (Part 1)
@app.get("/items")
async def list_items(
    user = Depends(get_user),
    pagination: PaginationParams = Depends()
):
    return {"user": user, "pagination": pagination}
```

**What we're building on today:**

In Part 1, we learned the **what** and **how** of dependencies. Today in Part 2, we'll learn:

- **When** to use advanced patterns
- **How** to handle cleanup (yield)
- **How** to optimize with caching
- **How** to test with dependency overriding
- **How** to build production-ready patterns

---

## Dependencies with Yield (Cleanup)

One of the most powerful features of FastAPI dependencies is the ability to perform cleanup after a request completes. This is done using Python's `yield` statement.

### Understanding Yield in Dependencies

When you use `yield` in a dependency, the code flow splits:

1. **Code before `yield`** - Runs before the request handler (setup)
2. **`yield` statement** - Provides the value to the handler
3. **Code after `yield`** - Runs after the request handler (cleanup)

**Think of it like a sandwich:**

```python
def get_database():
    # Top bun: Setup
    db = create_connection()

    try:
        # Filling: The actual dependency value
        yield db
    finally:
        # Bottom bun: Cleanup (always runs!)
        db.close()
```

```mermaid
graph TB
    A[Request Arrives] --> B[Dependency: Setup Code<br/>db = create_connection]
    B --> C[Dependency: yield db]
    C --> D[Handler Receives db]
    D --> E[Handler Executes]
    E --> F[Handler Returns Response]
    F --> G[Dependency: Cleanup Code<br/>db.close]
    G --> H[Response Sent to Client]

    I[Exception in Handler?] -.-> J[Cleanup STILL Runs]
    J -.-> K[Error Response Sent]

    style B fill:#6B8DBE
    style C fill:#8A82A8
    style E fill:#7FAE8A
    style G fill:#6B8DBE
    style J fill:#C2A25F
```

**Key insight:** The cleanup code (after `yield`) **always runs**, even if:

- The handler raises an exception
- Validation fails
- Another dependency fails
- The request is cancelled

This guarantees proper resource cleanup!

### Basic Yield Example

Let's start with a simple example:

```python
from fastapi import FastAPI, Depends

app = FastAPI()

def get_database():
    """
    Database dependency with cleanup.

    Flow:
    1. Create database connection (before yield)
    2. Provide connection to handler (yield)
    3. Close connection (after yield)
    """
    # Setup
    print("Opening database connection")
    db = {"connection": "active"}

    try:
        # Provide to handler
        yield db
    finally:
        # Cleanup (always runs!)
        print("Closing database connection")
        db["connection"] = "closed"

@app.get("/items")
async def list_items(db = Depends(get_database)):
    """
    When this endpoint is called:

    1. "Opening database connection" is printed
    2. Handler receives db = {"connection": "active"}
    3. Handler executes and returns response
    4. "Closing database connection" is printed
    5. Response sent to client
    """
    print(f"Handler executing with db: {db}")
    return {"items": ["item1", "item2"], "db_status": db["connection"]}

"""
Request: GET /items

Console output:
Opening database connection
Handler executing with db: {'connection': 'active'}
Closing database connection

Response:
{
  "items": ["item1", "item2"],
  "db_status": "active"
}
"""
```

### Why Use try/finally?

The `try/finally` block ensures cleanup runs even if exceptions occur:

```python
def get_database():
    db = create_connection()

    try:
        yield db
    finally:
        # This ALWAYS runs, even if:
        # - Handler raises exception
        # - Another dependency fails
        # - Request is cancelled
        db.close()

# Without try/finally (BAD!)
def get_database_bad():
    db = create_connection()
    yield db
    db.close()  # Might not run if exception occurs!
```

**Demonstration:**

```python
from fastapi import HTTPException, Depends

def get_db():
    print("1. Creating database")
    db = {"connection": "active"}

    try:
        print("2. Yielding database")
        yield db
    finally:
        print("4. Cleaning up database")
        db["connection"] = "closed"

@app.get("/error-endpoint")
async def error_endpoint(db = Depends(get_db)):
    print("3. Handler raising error")
    raise HTTPException(500, "Something went wrong")

"""
Request: GET /error-endpoint

Console output:
1. Creating database
2. Yielding database
3. Handler raising error
4. Cleaning up database  ← Still runs!

Response: 500 Internal Server Error

The cleanup code ran even though handler raised an exception!
"""
```

### Database Connection with Yield

The most common use case - managing database connections:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Setup (done once at app startup)
SQLALCHEMY_DATABASE_URL = "postgresql://user:pass@localhost/dbname"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db() -> Session:
    """
    Dependency that provides database session with automatic cleanup.

    This is the standard pattern for SQLAlchemy in FastAPI.
    """
    # Create session
    db = SessionLocal()

    try:
        # Provide session to handler
        yield db
    finally:
        # Always close session (return to pool)
        db.close()

# Usage in endpoints
@app.get("/users")
async def list_users(db: Session = Depends(get_db)):
    """
    Database session is provided and automatically cleaned up.

    Flow:
    1. get_db() creates session
    2. Handler receives session
    3. Handler queries database
    4. Handler returns
    5. get_db() closes session (returned to pool)
    """
    users = db.query(User).all()
    return users

@app.post("/users")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Even if an error occurs, session is closed properly.
    """
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

"""
Benefits of this pattern:

1. Automatic Cleanup
   - Session always closed, even on error
   - No connection leaks

2. Reusable
   - Every endpoint uses same dependency
   - Consistent session management

3. Testable
   - Can override with test database
   - Isolation for tests

4. Safe
   - try/finally ensures cleanup
   - Connection pool not exhausted
"""
```

### File Handling with `yield` in Dependencies

FastAPI supports **generator-based dependencies** using `yield`. This pattern is ideal when you need to **set up a resource before the request** and **clean it up after the request finishes**, even if an error occurs.

This is commonly used for:

- Temporary files
- Database sessions
- Locks
- External connections

---

#### Core Idea

A dependency that uses `yield` has **two phases**:

1. **Before `yield`** → setup logic
2. **After `yield` (in `finally`)** → cleanup logic

FastAPI guarantees that the cleanup code runs **after the request is completed**, regardless of success or failure.

---

#### Example: Temporary File Management

```python
import tempfile
import os
from fastapi import Depends

def get_temp_file():
    """
    Dependency that creates a temporary file,
    provides it to the handler, and cleans it up afterward.
    """
    # Setup phase: create temporary file
    temp_fd, temp_path = tempfile.mkstemp()
    print(f"Created temp file: {temp_path}")

    try:
        # Value yielded here is injected into the handler
        yield temp_path
    finally:
        # Cleanup phase: always executed
        os.close(temp_fd)
        os.unlink(temp_path)
        print(f"Deleted temp file: {temp_path}")

@app.post("/process-file")
async def process_file(
    content: str,
    temp_file: str = Depends(get_temp_file)
):
    """
    Uses a temporary file provided by the dependency.

    The handler:
    - Receives the temp file path
    - Does not care about creation or cleanup
    """
    # Write content to temp file
    with open(temp_file, "w") as f:
        f.write(content)

    # Process the file
    result = process_file_content(temp_file)

    # No cleanup needed here
    return {"result": result}
```

---

#### How the `yield` Syntax Works

```python
def dependency():
    setup()
    try:
        yield value
    finally:
        cleanup()
```

- `yield value`

  - The yielded value is **injected into the handler parameter**

- `finally` block

  - Runs **after the response is sent**
  - Runs even if:

    - The handler raises an exception
    - Validation fails
    - The request is cancelled

This makes it safer than manual cleanup inside handlers.

---

#### Request Lifecycle (Step-by-Step)

1. FastAPI receives the request
2. `get_temp_file()` is called
3. Temporary file is created
4. `yield temp_path` → `temp_file` is injected into handler
5. Handler executes using the file
6. Response is returned
7. `finally` block runs → file is closed and deleted

---

#### Why This Pattern Is Important in Production

- **Separation of concerns**

  - Handler focuses on business logic
  - Dependency manages resources

- **Safety**

  - Cleanup always happens
  - Prevents file leaks and resource exhaustion

- **Consistency**

  - Same lifecycle behavior as database sessions and transactions

---

#### Common Production Use Cases

- Temporary file storage
- Database session management
- Opening and closing external connections
- Acquiring and releasing

#### Writing to the Temporary File (`with open(...)`)

```python
with open(temp_file, "w") as f:
    f.write(content)
```

This block writes the incoming request data to the temporary file provided by the dependency.

**What is happening here:**

- `open(temp_file, "w")`

  - Opens the temporary file path returned by the dependency
  - `"w"` means **write mode**

    - Creates the file if it does not exist
    - Truncates (clears) the file if it already exists

- `with` statement

  - Ensures the file is **automatically closed**
  - Prevents file descriptor leaks
  - Safer than manually calling `open()` and `close()`

- `f.write(content)`

  - Writes the request payload (`content`) into the temporary file
  - The data is now persisted on disk for further processing

**Why this is good practice:**

- Guarantees file closure even if an exception occurs
- Keeps file-handling logic explicit and readable
- Works cleanly with dependency-based lifecycle management

In production systems, this pattern is commonly used when:

- Processing large payloads
- Interfacing with libraries that require file paths
- Performing batch or offline-style operations on request data

This pattern is the foundation for how FastAPI manages **database sessions with `yield`**, making it a critical concept to understand.

### Context Manager Pattern

Context managers pair naturally with **`yield`-based dependencies** because both follow the same lifecycle idea: **setup → use → cleanup**.

```python
from contextlib import contextmanager

class DatabaseConnection:
    def __init__(self):
        self.connected = False

    def connect(self):
        print("Connecting to database")
        self.connected = True

    def disconnect(self):
        print("Disconnecting from database")
        self.connected = False

    def query(self, sql: str):
        if not self.connected:
            raise Exception("Not connected")
        return f"Executing: {sql}"

@contextmanager
def database_connection():
    """Context manager for database connection"""
    conn = DatabaseConnection()
    conn.connect()
    try:
        yield conn
    finally:
        conn.disconnect()

def get_db():
    """
    Dependency using context manager.

    Combines yield pattern with context manager.
    """
    with database_connection() as conn:
        yield conn

@app.get("/query")
async def execute_query(db: DatabaseConnection = Depends(get_db)):
    result = db.query("SELECT * FROM users")
    return {"result": result}

"""
This pattern is clean because:
- Context manager handles connection lifecycle
- Dependency provides it to handler
- Both cleanup mechanisms work together
"""
```

#### Why This Pattern Exists

In real applications, resources like database connections must:

- Be created before the request
- Be available during request handling
- Be **reliably cleaned up** afterward

FastAPI’s `yield` dependencies align perfectly with Python’s context manager protocol to achieve this.

---

#### Core Building Block: Context Manager

```python
from contextlib import contextmanager
```

- `@contextmanager` lets you create a context manager using a generator
- Code **before `yield`** runs on entry
- Code **after `yield`** runs on exit (even on errors)

---

#### Database Connection Abstraction

```python
class DatabaseConnection:
    def __init__(self):
        self.connected = False

    def connect(self):
        print("Connecting to database")
        self.connected = True

    def disconnect(self):
        print("Disconnecting from database")
        self.connected = False

    def query(self, sql: str):
        if not self.connected:
            raise Exception("Not connected")
        return f"Executing: {sql}"
```

- Encapsulates connection state
- Explicit `connect()` and `disconnect()` methods
- Prevents usage when not connected

---

#### Context Manager for Connection Lifecycle

```python
@contextmanager
def database_connection():
    """Context manager for database connection"""
    conn = DatabaseConnection()
    conn.connect()
    try:
        yield conn
    finally:
        conn.disconnect()
```

- Creates the connection
- Yields it for use
- Guarantees disconnection in `finally`

This is a **pure Python** construct, independent of FastAPI.

---

#### Using the Context Manager Inside a Dependency

```python
def get_db():
    """
    Dependency using a context manager.

    Setup happens before yield.
    Cleanup happens after request completes.
    """
    with database_connection() as conn:
        yield conn
```

- `with` enters the context manager
- `yield` exposes the resource to the path operation
- When the request ends:

  - FastAPI resumes execution
  - The `with` block exits
  - Cleanup runs automatically

---

#### Consuming the Dependency in a Path Operation

```python
@app.get("/query")
async def execute_query(db: DatabaseConnection = Depends(get_db)):
    result = db.query("SELECT * FROM users")
    return {"result": result}
```

- The handler receives a **ready-to-use** database connection
- No setup or teardown logic appears in the handler
- Business logic stays clean and focused

---

#### Why This Pattern Is Clean and Safe

- Connection lifecycle is centralized
- Cleanup is guaranteed even on errors
- Dependencies remain composable and testable
- Handlers stay thin and declarative

This pattern is ideal for:

- Database sessions
- Transactions
- External service clients
- Any resource requiring strict lifecycle control

### Multiple Resources with Yield

A single dependency can manage **multiple resources** by acquiring them together and releasing them in one place. This is useful when an operation depends on several services that must share the same request lifecycle.

---

#### What This Pattern Solves

Some endpoints need more than one resource at the same time, for example:

- A database connection
- A cache client
- A logger or tracer

Managing these individually in the handler leads to:

- Repeated setup code
- Forgotten cleanup
- Harder-to-test handlers

`yield`-based dependencies centralize this logic.

---

#### Acquiring Multiple Resources

```python
def get_resources():
    """
    Acquire multiple resources and clean them all up.
    """
    # Acquire resources
    db = connect_to_database()
    cache = connect_to_redis()
    logger = setup_logger()

    print("All resources acquired")
```

- All resources are created **once per request**
- They are acquired in a defined order
- Failures here prevent the handler from running

---

#### Exposing Resources to the Handler

```python
    try:
        # Provide all resources
        yield {
            "db": db,
            "cache": cache,
            "logger": logger
        }
```

- `yield` passes a structured object (dictionary) to the handler
- Grouping related resources keeps the handler signature simple
- Any structure can be used (dict, dataclass, custom object)

---

#### Guaranteed Cleanup Phase

```python
    finally:
        # Clean up all resources (in reverse order)
        print("Cleaning up resources")
        logger.close()
        cache.disconnect()
        db.close()
        print("All resources cleaned up")
```

- Always runs after the request finishes
- Runs even if an exception occurs in the handler
- Cleanup is typically done in **reverse acquisition order**

---

#### Consuming Multiple Resources in the Handler

```python
@app.get("/complex-operation")
async def complex_operation(resources = Depends(get_resources)):
```

- The handler depends on **one dependency**
- Internally, it gains access to multiple services
- No setup or teardown logic leaks into business code

```python
    db = resources["db"]
    cache = resources["cache"]
    logger = resources["logger"]
```

---

#### Why This Works Well in Production

- One place controls resource lifecycle
- Prevents leaks and inconsistent state
- Keeps handlers focused on business logic
- Easy to swap implementations (e.g., mock cache or DB in tests)

This pattern is especially effective for **complex request flows** where multiple infrastructure components must work together safely within a single request.

```python
def get_resources():
    """
    Acquire multiple resources and clean them all up.
    """
    # Acquire resources
    db = connect_to_database()
    cache = connect_to_redis()
    logger = setup_logger()

    print("All resources acquired")

    try:
        # Provide all resources
        yield {
            "db": db,
            "cache": cache,
            "logger": logger
        }
    finally:
        # Clean up all resources (in reverse order)
        print("Cleaning up resources")
        logger.close()
        cache.disconnect()
        db.close()
        print("All resources cleaned up")

@app.get("/complex-operation")
async def complex_operation(resources = Depends(get_resources)):
    """
    Use multiple resources, all cleaned up automatically.
    """
    db = resources["db"]
    cache = resources["cache"]
    logger = resources["logger"]

    logger.info("Starting operation")

    # Check cache first
    cached = cache.get("key")
    if cached:
        return {"data": cached, "source": "cache"}

    # Query database
    data = db.query("SELECT * FROM items")

    # Store in cache
    cache.set("key", data)

    logger.info("Operation complete")

    return {"data": data, "source": "database"}
```

### Transaction Management

Using `yield`-based dependencies is the **recommended way** to manage database transactions in FastAPI. It ensures that all database operations within a request either succeed together or fail together.

---

#### Core Idea

- The dependency **owns the transaction lifecycle**
- The handler only performs business logic
- Commit or rollback is decided automatically based on success or failure

---

```python
from sqlalchemy.orm import Session

def get_db_transaction():
    """
    Dependency that provides database session in a transaction.

    Automatically commits on success or rolls back on error.
    """
    db = SessionLocal()

    try:
        # Start transaction (implicit in SQLAlchemy)
        yield db

        # If we reach here, handler succeeded
        db.commit()
        print("Transaction committed")

    except Exception as e:
        # Handler raised exception
        db.rollback()
        print(f"Transaction rolled back: {e}")
        raise

    finally:
        # Always close session
        db.close()

@app.post("/transfer-funds")
async def transfer_funds(
    from_account: int,
    to_account: int,
    amount: float,
    db: Session = Depends(get_db_transaction)
):
    """
    Transfer funds between accounts.

    If any operation fails, entire transaction is rolled back.
    If all succeed, transaction is committed.
    """
    # Deduct from source account
    source = db.query(Account).filter_by(id=from_account).first()
    if source.balance < amount:
        raise HTTPException(400, "Insufficient funds")
    source.balance -= amount

    # Add to destination account
    dest = db.query(Account).filter_by(id=to_account).first()
    dest.balance += amount

    # Create transaction record
    transaction = Transaction(
        from_account=from_account,
        to_account=to_account,
        amount=amount
    )
    db.add(transaction)

    # If we return successfully, transaction commits!
    # If any line above raises exception, transaction rolls back!
    return {"message": "Transfer successful"}

"""
This pattern ensures:
- All-or-nothing execution
- Automatic rollback on error
- No partial updates
- Clean session management
"""
```

---

#### Transaction Dependency

```python
from sqlalchemy.orm import Session

def get_db_transaction():
    """
    Dependency that provides a database session wrapped in a transaction.

    - Commits if the request succeeds
    - Rolls back if an exception occurs
    - Always closes the session
    """
    db = SessionLocal()

    try:
        # Transaction starts implicitly
        yield db

        # Executed only if handler completes successfully
        db.commit()
        print("Transaction committed")

    except Exception as e:
        # Executed if handler raises an exception
        db.rollback()
        print(f"Transaction rolled back: {e}")
        raise

    finally:
        # Always release the session
        db.close()
```

---

#### Using the Transaction in a Handler

```python
@app.post("/transfer-funds")
async def transfer_funds(
    from_account: int,
    to_account: int,
    amount: float,
    db: Session = Depends(get_db_transaction)
):
```

- The handler receives a **ready-to-use session**
- It does not know or care about commit/rollback
- Any exception automatically triggers rollback

---

#### Atomic Business Logic

```python
    source = db.query(Account).filter_by(id=from_account).first()
    if source.balance < amount:
        raise HTTPException(400, "Insufficient funds")
    source.balance -= amount

    dest = db.query(Account).filter_by(id=to_account).first()
    dest.balance += amount

    transaction = Transaction(
        from_account=from_account,
        to_account=to_account,
        amount=amount
    )
    db.add(transaction)

    return {"message": "Transfer successful"}
```

- All operations run in **one transaction**
- Any failure stops execution and rolls everything back
- No partial updates are possible

---

#### Why This Pattern Is Production-Grade

- Guarantees **atomicity** (all-or-nothing)
- Prevents inconsistent database state
- Centralizes transaction handling
- Keeps handlers clean and testable

This approach should be the default for **any endpoint that modifies data** in production systems.

### Timing and Logging

`yield`-based dependencies are a clean way to measure request execution time and perform logging **around** a request without polluting handler logic.

---

#### Core Idea

- Code **before `yield`** runs _before_ the handler
- Code **after `yield`** runs _after_ the handler finishes
- The handler remains unaware of timing or logging concerns

This makes timing a perfect **side-effect-only dependency**.

---

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name: str):
    """Context manager for timing operations"""
    start = time.time()
    print(f"[{name}] Starting...")
    yield
    elapsed = time.time() - start
    print(f"[{name}] Completed in {elapsed:.2f}s")

def log_request_time():
    """
    Dependency that logs request processing time.

    Nothing to yield to handler - just timing!
    """
    start = time.time()

    # Yield nothing (handler doesn't need anything)
    yield

    # After handler completes
    elapsed = time.time() - start
    print(f"Request processed in {elapsed:.3f}s")

@app.get("/slow-operation")
async def slow_operation(_=Depends(log_request_time)):
    """
    Request timing logged automatically.

    Note: _ = Depends(...) pattern for side-effect-only dependencies
    """
    # Simulate slow operation
    time.sleep(2)
    return {"status": "completed"}

"""
Request: GET /slow-operation

Console output:
Request processed in 2.003s

The dependency measured request time without the handler
needing to know about it!
"""
```

---

#### Timing Dependency

```python
def log_request_time():
    """
    Dependency that logs total request processing time.

    Does not provide any value to the handler.
    """
    start = time.time()

    # Run handler
    yield

    # Runs after handler completes
    elapsed = time.time() - start
    print(f"Request processed in {elapsed:.3f}s")
```

- No return value is needed
- The dependency exists only for its side effect (logging)

---

#### Using the Dependency in a Path Operation

```python
@app.get("/slow-operation")
async def slow_operation(_ = Depends(log_request_time)):
```

- `_ = Depends(...)` signals **intentional ignore**
- Dependency still executes fully
- Handler parameters stay clean

---

#### Handler Logic

```python
    time.sleep(2)
    return {"status": "completed"}
```

- The handler does its job
- Timing is handled externally

---

#### Execution Flow

1. FastAPI starts request
2. `log_request_time()` runs and records start time
3. Handler executes
4. Control returns to dependency
5. Elapsed time is logged
6. Response is sent

---

#### Why This Pattern Is Useful

- Centralized request logging
- Zero coupling between logging and business logic
- Easy to enable or remove per endpoint
- Ideal for metrics, tracing, and observability

This pattern scales naturally to structured logging, distributed tracing, and performance monitoring systems.

### Cleanup Guarantees

Understanding when cleanup runs:

```python
def track_lifecycle():
    """
    Track exact lifecycle of dependency.
    """
    print("1. Setup: Before yield")

    try:
        print("2. Yielding value")
        yield {"status": "active"}
    finally:
        print("4. Cleanup: After handler")

@app.get("/success")
async def success_endpoint(_=Depends(track_lifecycle)):
    print("3. Handler executing successfully")
    return {"result": "ok"}

@app.get("/error")
async def error_endpoint(_=Depends(track_lifecycle)):
    print("3. Handler raising error")
    raise HTTPException(500, "Intentional error")

"""
Success case:
1. Setup: Before yield
2. Yielding value
3. Handler executing successfully
4. Cleanup: After handler

Error case:
1. Setup: Before yield
2. Yielding value
3. Handler raising error
4. Cleanup: After handler  ← Still runs!

Cleanup ALWAYS runs, regardless of success or failure!
"""
```

### When to Use Yield

**Use yield dependencies when you need to:**

| Scenario               | Example                          |
| ---------------------- | -------------------------------- |
| Close connections      | Database, Redis, file handles    |
| Release resources      | Locks, semaphores, memory        |
| Cleanup temporary data | Temp files, cache entries        |
| Measure timing         | Request duration, profiling      |
| Log operations         | Start/end logging                |
| Manage transactions    | Commit/rollback                  |
| Context management     | Any resource with setup/teardown |

**Don't use yield when:**

- Simple value extraction (query params, headers)
- Stateless transformations
- No cleanup needed
- Just validation

---

## Dependency Caching

FastAPI automatically caches dependency results within a single request. This is a powerful optimization feature.

### Understanding Dependency Caching

**The problem without caching:**

```python
def get_current_user(token: str = Header(...)):
    # This is an expensive operation
    print("Fetching user from database...")
    return database.get_user_by_token(token)

@app.get("/profile")
async def get_profile(user = Depends(get_current_user)):
    return user

@app.get("/settings")
async def get_settings(user = Depends(get_current_user)):
    # Same user fetched again!
    return user.settings
```

**Without caching:** Each endpoint would query the database separately, even in the same request!

**FastAPI's solution:** Cache dependency results per request.

```mermaid
graph TB
    A[Request Arrives] --> B{get_current_user called?}
    B -->|No| C[Call get_current_user]
    C --> D[Cache Result]
    D --> E[Return Result]

    B -->|Yes| F[Return Cached Result]
    F --> E

    E --> G[Continue Processing]
    G --> H{Need user again?}
    H -->|Yes| B
    H -->|No| I[Complete Request]

    style C fill:#C2A25F
    style D fill:#6B8DBE
    style F fill:#7FAE8A
```

### How Dependency Caching Works

FastAPI automatically **caches dependency results within a single request**. This ensures efficiency and consistency when the same dependency is used multiple times.

---

```python
def expensive_operation(x: int = Query(...)):
    """
    Expensive operation - should only run once per request.
    """
    print(f"Running expensive operation with x={x}")
    time.sleep(1)  # Simulate expensive operation
    return x * 2

@app.get("/cached")
async def cached_example(
    result1 = Depends(expensive_operation),
    result2 = Depends(expensive_operation),
    result3 = Depends(expensive_operation)
):
    """
    expensive_operation is called 3 times, but only executes once!

    All three dependencies get the same cached result.
    """
    return {
        "result1": result1,
        "result2": result2,
        "result3": result3
    }

"""
Request: GET /cached?x=5

Console output:
Running expensive operation with x=5  ← Only printed ONCE!

Response:
{
  "result1": 10,
  "result2": 10,
  "result3": 10
}

All three results are the same because the dependency
was only executed once and the result was cached.
"""
```

#### What FastAPI Uses to Cache Dependencies

FastAPI decides whether to reuse a dependency result based on:

1. **Dependency function identity**
   The same dependency function is reused if it appears multiple times.

2. **Resolved parameters**
   The same input values produce the same cached result.

3. **Request scope**
   The cache exists only for the lifetime of one request and is cleared afterward.

---

#### Example: Cached Dependency Execution

```python
def expensive_operation(x: int = Query(...)):
    """
    Simulates an expensive computation.
    """
    print(f"Running expensive operation with x={x}")
    time.sleep(1)
    return x * 2
```

This dependency is intentionally slow and should not run more than necessary.

---

#### Using the Same Dependency Multiple Times

```python
@app.get("/cached")
async def cached_example(
    result1 = Depends(expensive_operation),
    result2 = Depends(expensive_operation),
    result3 = Depends(expensive_operation),
):
    """
    The dependency appears three times but executes only once.
    """
    return {
        "result1": result1,
        "result2": result2,
        "result3": result3,
    }
```

---

#### What Happens at Runtime

Request:

```
GET /cached?x=5
```

Execution:

- `expensive_operation(x=5)` is called once
- Result is cached
- Cached value is reused for `result1`, `result2`, and `result3`

Console output:

```
Running expensive operation with x=5
```

Response:

```json
{
  "result1": 10,
  "result2": 10,
  "result3": 10
}
```

---

#### Key Takeaways

- Dependencies run **at most once per request**
- Cached results are reused across parameters and branches
- Expensive work is automatically deduplicated
- Caching is request-scoped and never leaks across requests

This behavior is critical for performance, database sessions, and consistency in complex dependency graphs.

### Caching in Dependency Chains

FastAPI’s dependency caching applies **across the entire dependency graph**, not just within a single parameter. This means caching works **through chains and branches** automatically.

---

#### Core Idea

If the **same dependency function** is required multiple times during a request—directly or indirectly—FastAPI:

- Executes it **once**
- Caches the result
- Reuses the cached value everywhere else in the chain

---

#### Example Dependency Chain

```python
def get_database():
    print("Opening database connection")
    return {"connection": "active"}

def get_user(user_id: int, db = Depends(get_database)):
    print(f"Fetching user {user_id}")
    return db.get("user", user_id)

def get_user_permissions(user = Depends(get_user)):
    print(f"Fetching permissions for {user}")
    return ["read", "write"]
```

Here:

- `get_user` depends on `get_database`
- `get_user_permissions` depends on `get_user`
- This forms a dependency chain

---

#### Reusing the Same Dependencies in the Handler

```python
@app.get("/check-access")
async def check_access(
    db1 = Depends(get_database),
    db2 = Depends(get_database),
    user1 = Depends(get_user),
    user2 = Depends(get_user),
    perms = Depends(get_user_permissions),
):
    """
    Each dependency is declared multiple times,
    but executed only once per request.
    """
    return {
        "databases_same": db1 is db2,
        "users_same": user1 is user2,
        "permissions": perms,
    }
```

---

#### What Happens at Runtime

Request:

```
GET /check-access?user_id=1
```

Execution order:

1. `get_database()` runs once
2. `get_user()` runs once and reuses the cached database
3. `get_user_permissions()` runs once and reuses the cached user

Console output:

```
Opening database connection
Fetching user 1
Fetching permissions for {...}
```

Response:

```json
{
  "databases_same": true,
  "users_same": true,
  "permissions": ["read", "write"]
}
```

---

#### Why This Matters

- Prevents duplicate database connections
- Avoids repeated queries for the same data
- Guarantees consistency across the request
- Enables safe and efficient dependency graphs

This is why FastAPI dependency chains scale cleanly even in complex, production-grade systems.

```python
def get_database():
    print("Opening database connection")
    return {"connection": "active"}

def get_user(user_id: int, db = Depends(get_database)):
    print(f"Fetching user {user_id}")
    return db.get("user", user_id)

def get_user_permissions(user = Depends(get_user)):
    print(f"Fetching permissions for {user}")
    return ["read", "write"]

@app.get("/check-access")
async def check_access(
    db1 = Depends(get_database),        # Database connection 1
    db2 = Depends(get_database),        # Same connection! (cached)
    user1 = Depends(get_user),          # User fetch 1
    user2 = Depends(get_user),          # Same user! (cached)
    perms = Depends(get_user_permissions)  # Uses cached user
):
    """
    Even though we depend on get_database and get_user multiple times,
    each is only called once per request!
    """
    return {
        "databases_same": db1 is db2,  # True!
        "users_same": user1 is user2,  # True!
        "permissions": perms
    }

"""
Request: GET /check-access?user_id=1

Console output:
Opening database connection      ← Only ONCE
Fetching user 1                  ← Only ONCE
Fetching permissions for {...}   ← Only ONCE

Response:
{
  "databases_same": true,
  "users_same": true,
  "permissions": ["read", "write"]
}
"""
```

### Caching with Different Parameters

Caching is parameter-sensitive:

```python
def get_item(item_id: int):
    print(f"Fetching item {item_id}")
    return {"id": item_id, "name": f"Item {item_id}"}

@app.get("/items/{item_id}/details")
async def item_details(
    item_id: int,
    item1 = Depends(get_item),  # Called with item_id from path
    item2 = Depends(get_item)   # Same item_id = cached!
):
    return {"item1": item1, "item2": item2}

@app.get("/compare")
async def compare_items(
    id1: int = Query(...),
    id2: int = Query(...),
    item1 = Depends(lambda: get_item(id1)),  # Different parameter
    item2 = Depends(lambda: get_item(id2))   # Different parameter
):
    """
    Different parameters = different cache entries.

    Both dependencies execute because parameters differ.
    """
    return {"item1": item1, "item2": item2}

"""
Request: GET /items/123/details

Console:
Fetching item 123  ← Only once

Request: GET /compare?id1=1&id2=2

Console:
Fetching item 1    ← id1
Fetching item 2    ← id2 (different parameter, so not cached)
"""
```

### Disabling Caching with use_cache=False

Sometimes you want to disable caching:

```python
from fastapi import Depends

def get_timestamp():
    """Get current timestamp"""
    return time.time()

@app.get("/with-cache")
async def with_cache(
    time1 = Depends(get_timestamp),
    time2 = Depends(get_timestamp)
):
    """
    Both timestamps are the same (cached).
    """
    return {"time1": time1, "time2": time2, "same": time1 == time2}

@app.get("/without-cache")
async def without_cache(
    time1 = Depends(get_timestamp, use_cache=False),
    time2 = Depends(get_timestamp, use_cache=False)
):
    """
    Each call gets fresh timestamp (not cached).
    """
    return {"time1": time1, "time2": time2, "same": time1 == time2}

"""
Request: GET /with-cache
Response: {"time1": 1234567890.123, "time2": 1234567890.123, "same": true}

Request: GET /without-cache
Response: {"time1": 1234567890.123, "time2": 1234567890.125, "same": false}
"""
```

### Caching Best Practices

**When to rely on caching:**

- Database connections (expensive to create)
- User authentication (expensive database/API call)
- Configuration loading (rarely changes)
- Expensive computations within a request

**When to disable caching:**

- Random number generation
- Timestamps
- Request-specific IDs
- Operations that should run every time

**Example: Auth + Database pattern:**

```python
def get_db():
    """Database connection - should be cached"""
    db = create_connection()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Header(...),
    db = Depends(get_db)  # Reuses cached connection!
):
    """User authentication - should be cached"""
    return db.query(User).filter_by(token=token).first()

def get_user_posts(
    user = Depends(get_current_user),  # Reuses cached user!
    db = Depends(get_db)               # Reuses cached connection!
):
    """User's posts - reuses both cached dependencies"""
    return db.query(Post).filter_by(user_id=user.id).all()

@app.get("/dashboard")
async def dashboard(
    user = Depends(get_current_user),
    posts = Depends(get_user_posts)
):
    """
    This endpoint:
    - Opens database connection ONCE
    - Fetches current user ONCE
    - Fetches posts ONCE

    Even though multiple dependencies need them!
    """
    return {"user": user, "posts": posts}
```

---

## Global Dependencies

Global dependencies run for **every request** to your application, regardless of the endpoint.

### Understanding Global Dependencies

Global dependencies are useful for:

- Logging every request
- Authentication for entire API
- Rate limiting all endpoints
- Request ID generation
- Performance monitoring

```python
from fastapi import FastAPI, Depends, Request

def log_request(request: Request):
    """
    Global dependency - runs for EVERY request.
    """
    print(f"Request: {request.method} {request.url}")
    # No return value needed - side effect only

app = FastAPI(
    dependencies=[Depends(log_request)]  # ← Global dependency
)

@app.get("/items")
async def list_items():
    return {"items": []}

@app.get("/users")
async def list_users():
    return {"users": []}

"""
Every request to any endpoint logs automatically:

GET /items  → "Request: GET http://localhost:8000/items"
GET /users  → "Request: GET http://localhost:8000/users"

No need to add dependency to each endpoint!
"""
```

### Multiple Global Dependencies

```python
def log_request(request: Request):
    print(f"[LOG] {request.method} {request.url}")

def check_api_key(x_api_key: str = Header(...)):
    if x_api_key != "secret-key":
        raise HTTPException(401, "Invalid API key")

def add_request_id(request: Request):
    request.state.request_id = str(uuid.uuid4())
    print(f"[REQUEST-ID] {request.state.request_id}")

app = FastAPI(
    dependencies=[
        Depends(log_request),
        Depends(check_api_key),
        Depends(add_request_id)
    ]
)

"""
Every request must:
1. Be logged
2. Have valid API key
3. Get request ID

All automatically - no per-endpoint code needed!
"""
```

### Global Dependencies with Yield

```python
import time

def track_request_time():
    """
    Global dependency that times every request.
    """
    start = time.time()

    yield

    elapsed = time.time() - start
    print(f"Request completed in {elapsed:.3f}s")

app = FastAPI(
    dependencies=[Depends(track_request_time)]
)

@app.get("/fast")
async def fast_endpoint():
    return {"status": "ok"}

@app.get("/slow")
async def slow_endpoint():
    time.sleep(2)
    return {"status": "ok"}

"""
GET /fast  → "Request completed in 0.001s"
GET /slow  → "Request completed in 2.003s"

Every request timed automatically!
"""
```

### When to Use Global Dependencies

**Good use cases:**

- Authentication for private APIs
- Rate limiting
- Request logging
- Monitoring/metrics
- CORS (though middleware is better)
- Request ID injection

**Bad use cases:**

- Database connections (use per-endpoint)
- User-specific data (use per-endpoint)
- Endpoint-specific validation
- Heavy computations (only needed by some endpoints)

**Example: Authenticated API:**

```python
def verify_api_key(x_api_key: str = Header(...)):
    """
    Verify API key for all requests.
    """
    if x_api_key not in valid_api_keys:
        raise HTTPException(401, "Invalid API key")
    return x_api_key

# All endpoints require authentication
app = FastAPI(
    title="Private API",
    dependencies=[Depends(verify_api_key)]
)

@app.get("/data")
async def get_data():
    # No need to check auth - global dependency does it
    return {"data": "secret"}

@app.post("/data")
async def create_data(item: dict):
    # Auth checked automatically
    return {"created": item}

"""
Every endpoint requires valid API key.
No need to add dependency to each endpoint.
"""
```

---

## Router-Level Dependencies

Router dependencies apply to all endpoints within a specific router (a group of related endpoints).

### Understanding APIRouter Dependencies

FastAPI uses `APIRouter` to organize endpoints into logical groups. Dependencies can be applied to the entire router:

```python
from fastapi import APIRouter, Depends

# Create router with dependencies
admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin)]  # ← Router dependency
)

def verify_admin(user = Depends(get_current_user)):
    """
    Verify user is admin.

    This runs for ALL endpoints in admin_router.
    """
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user

# All these endpoints automatically check admin access
@admin_router.get("/users")
async def list_all_users():
    return {"users": get_all_users()}

@admin_router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    delete_user_by_id(user_id)
    return {"deleted": user_id}

@admin_router.post("/settings")
async def update_settings(settings: dict):
    save_settings(settings)
    return {"updated": settings}

# Include router in app
app.include_router(admin_router)

"""
Every endpoint under /admin/:
- Requires authentication (via get_current_user)
- Requires admin role (via verify_admin)

No need to add dependency to each endpoint!
"""
```

### Multiple Routers with Different Dependencies

```python
from fastapi import FastAPI, APIRouter, Depends

app = FastAPI()

# Public routes - no authentication
public_router = APIRouter(prefix="/public", tags=["public"])

@public_router.get("/info")
async def public_info():
    return {"info": "This is public"}

# User routes - requires authentication
user_router = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[Depends(get_current_user)]
)

@user_router.get("/profile")
async def user_profile(user = Depends(get_current_user)):
    return {"user": user}

@user_router.get("/posts")
async def user_posts(user = Depends(get_current_user)):
    return {"posts": get_user_posts(user.id)}

# Admin routes - requires admin role
admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin)]
)

@admin_router.get("/users")
async def list_all_users():
    return {"users": get_all_users()}

# Include all routers
app.include_router(public_router)
app.include_router(user_router)
app.include_router(admin_router)

"""
Organization:
- /public/*  - No auth required
- /user/*    - Auth required
- /admin/*   - Admin role required

Clean separation of concerns!
"""
```

### Combining Router and Endpoint Dependencies

```python
def rate_limit_user():
    """Rate limit check - router level"""
    # Check rate limit for authenticated users
    pass

def validate_post_ownership(post_id: int, user = Depends(get_current_user)):
    """Validate user owns post - endpoint level"""
    post = get_post(post_id)
    if post.user_id != user.id:
        raise HTTPException(403, "Not your post")
    return post

posts_router = APIRouter(
    prefix="/posts",
    dependencies=[
        Depends(get_current_user),  # All endpoints require auth
        Depends(rate_limit_user)    # All endpoints rate limited
    ]
)

@posts_router.get("/")
async def list_my_posts(user = Depends(get_current_user)):
    """
    Dependencies:
    - Router: auth + rate limit
    - Endpoint: none extra
    """
    return get_user_posts(user.id)

@posts_router.put("/{post_id}")
async def update_post(
    post_id: int,
    content: str,
    post = Depends(validate_post_ownership)  # Endpoint-specific
):
    """
    Dependencies:
    - Router: auth + rate limit
    - Endpoint: ownership validation

    Total: 3 dependency checks!
    """
    update_post_content(post_id, content)
    return {"updated": post_id}

"""
Layered dependencies:

1. Router dependencies (all endpoints)
   - Authentication
   - Rate limiting

2. Endpoint dependencies (specific endpoint)
   - Ownership validation

This gives fine-grained control!
"""
```

### Nested Routers

```python
# Main API router
api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(verify_api_key)]  # All v1 endpoints
)

# Users sub-router
users_router = APIRouter(
    prefix="/users",
    dependencies=[Depends(get_current_user)]  # All user endpoints
)

# Admin user sub-router
admin_users_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(verify_admin)]  # Admin user endpoints
)

@admin_users_router.delete("/{user_id}")
async def delete_any_user(user_id: int):
    """
    Dependencies chain:
    1. verify_api_key (from api_router)
    2. get_current_user (from users_router)
    3. verify_admin (from admin_users_router)

    All three must pass!
    """
    delete_user(user_id)
    return {"deleted": user_id}

# Include routers hierarchically
users_router.include_router(admin_users_router)
api_router.include_router(users_router)
app.include_router(api_router)

"""
Final URL: /api/v1/users/admin/{user_id}

Dependencies applied:
1. API key validation
2. User authentication
3. Admin authorization

Clean hierarchical organization!
"""
```

---

## Dependency Overriding for Testing

FastAPI allows you to **replace real dependencies with test-specific ones**. This makes testing safe, fast, and fully isolated from production systems.

---

### Why Dependency Overriding Is Needed

#### The Problem

Production dependencies are often tied to real resources:

```python
def get_db():
    """Production database connection"""
    return create_production_db_connection()

@app.get("/users")
async def list_users(db = Depends(get_db)):
    return db.query("SELECT * FROM users")

```

Issues during testing:

- Tests would connect to the **production database**
- Tests become **slow and unsafe**
- Hard to simulate edge cases and failures

---

### The Core Idea

FastAPI lets you **override a dependency at runtime**:

```python
app.dependency_overrides[get_db] = lambda: test_database

```

From that point on:

- Every `Depends(get_db)` uses the test version
- No production code needs to change
- Overrides apply only while they are set

---

### Basic Dependency Override Example

```python
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

app = FastAPI()

# Production dependency
def get_user():
    return {"id": 1, "name": "Production User"}

@app.get("/user")
async def read_user(user = Depends(get_user)):
    return user

```

---

### Testing Without Overrides

```python
client = TestClient(app)

def test_user_production():
    response = client.get("/user")
    assert response.json()["name"] == "Production User"

```

This test uses the real dependency.

---

### Testing With Dependency Override

```python
def test_user_override():
    # Test-specific dependency
    def get_test_user():
        return {"id": 999, "name": "Test User"}

    # Override production dependency
    app.dependency_overrides[get_user] = get_test_user

    response = client.get("/user")
    assert response.json()["name"] == "Test User"

    # Always clean up after the test
    app.dependency_overrides.clear()

```

---

### How Overrides Work

- Overrides are matched by **function identity**
- Any `Depends(get_user)` is replaced globally
- The handler code remains unchanged
- Overrides last until explicitly cleared

---

### Best Practices for Testing

- Override **external systems** (DB, cache, APIs)
- Keep test dependencies **simple and deterministic**
- Always **clear overrides** after each test
- Prefer overrides over mocking inside handlers

Dependency overriding is what makes FastAPI tests clean, reliable, and production-safe without sacrificing design quality.

### Overriding Database Dependencies

The most common use case:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Production setup
PROD_DATABASE_URL = "postgresql://user:pass@prod-server/db"
prod_engine = create_engine(PROD_DATABASE_URL)
ProdSessionLocal = sessionmaker(bind=prod_engine)

def get_db():
    """Production database dependency"""
    db = ProdSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Test setup
TEST_DATABASE_URL = "postgresql://user:pass@localhost/test_db"
test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=test_engine)

def get_test_db():
    """Test database dependency"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Application
@app.get("/users")
async def list_users(db = Depends(get_db)):
    return db.query(User).all()

# Tests
def test_list_users():
    # Override with test database
    app.dependency_overrides[get_db] = get_test_db

    # Create test data
    db = next(get_test_db())
    test_user = User(name="Test User")
    db.add(test_user)
    db.commit()

    # Test endpoint
    client = TestClient(app)
    response = client.get("/users")

    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Test User"

    # Cleanup
    app.dependency_overrides.clear()

"""
Benefits:
- Tests use isolated test database
- Production database untouched
- Full integration testing
- Easy setup and teardown
"""
```

### Overriding Authentication

```python
def get_current_user(token: str = Header(...)):
    """Production auth - validates real tokens"""
    user = validate_token_with_auth_service(token)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user

@app.get("/profile")
async def get_profile(user = Depends(get_current_user)):
    return {"user": user}

# Tests
def test_profile_authenticated():
    """Test with mock authentication"""

    # Override auth dependency
    def mock_current_user():
        return {"id": 1, "name": "Test User", "role": "user"}

    app.dependency_overrides[get_current_user] = mock_current_user

    # Test without needing real token
    client = TestClient(app)
    response = client.get("/profile")

    assert response.status_code == 200
    assert response.json()["user"]["name"] == "Test User"

    app.dependency_overrides.clear()

def test_profile_admin():
    """Test with admin user"""

    def mock_admin_user():
        return {"id": 2, "name": "Admin User", "role": "admin"}

    app.dependency_overrides[get_current_user] = mock_admin_user

    client = TestClient(app)
    response = client.get("/profile")

    assert response.json()["user"]["role"] == "admin"

    app.dependency_overrides.clear()

"""
No need for:
- Real authentication service
- Valid tokens
- User database

Just override with test data!
"""
```

### Overriding External Services

```python
# Production dependency
def get_payment_gateway():
    """Real payment gateway"""
    return StripeGateway(api_key=os.getenv("STRIPE_KEY"))

@app.post("/checkout")
async def checkout(
    amount: float,
    gateway = Depends(get_payment_gateway)
):
    charge = gateway.charge(amount)
    return {"charge_id": charge.id}

# Test
def test_checkout():
    """Test without charging real money!"""

    class MockPaymentGateway:
        def charge(self, amount):
            return type('obj', (object,), {'id': 'mock_charge_123'})

    # Override with mock
    app.dependency_overrides[get_payment_gateway] = lambda: MockPaymentGateway()

    client = TestClient(app)
    response = client.post("/checkout", json={"amount": 100.0})

    assert response.json()["charge_id"] == "mock_charge_123"
    # No real charge made!

    app.dependency_overrides.clear()
```

---

### Pytest Fixtures for Dependency Overrides

When testing FastAPI applications, **pytest fixtures** are the cleanest way to manage dependency overrides. They ensure isolation, reusability, and proper cleanup between tests.

#### Why Use Fixtures for Overrides?

Fixtures help you:

- Apply dependency overrides **only for specific tests**
- Avoid leaking overrides between tests
- Share mock setup logic across many test cases
- Keep test code declarative and readable

Each fixture controls **one concern** (client, database, user, etc.).

---

#### Client Fixture with Cleanup

```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    """Test client with clean dependency overrides"""
    client = TestClient(app)
    yield client
    # Cleanup after each test
    app.dependency_overrides.clear()
```

**What this does:**

- Creates a `TestClient` for each test
- Yields it to the test function
- Clears all dependency overrides after the test finishes

This guarantees **test isolation**—no test affects another.

---

#### Mock Database Dependency

```python
@pytest.fixture
def mock_db():
    """Mock database session"""
    def get_mock_db():
        return MockDatabase()

    app.dependency_overrides[get_db] = get_mock_db
    yield get_mock_db()
```

**Key points:**

- Overrides the production `get_db` dependency
- Replaces it with an in-memory or fake database
- Automatically applies to all endpoints using `Depends(get_db)`

This avoids touching real databases during tests.

---

#### Mock Authenticated User

```python
@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    def get_mock_user():
        return {"id": 1, "name": "Test User"}

    app.dependency_overrides[get_current_user] = get_mock_user
    yield get_mock_user()
```

**Why this matters:**

- Bypasses authentication logic
- Lets you test protected routes easily
- Keeps authorization logic out of test setup

---

#### Using Fixtures in Tests

```python
def test_with_mocks(client, mock_db, mock_user):
    """Test with all mocks in place"""
    response = client.get("/protected-resource")
    assert response.status_code == 200
    # Both database and auth are mocked!
```

**What happens here:**

- `client` ensures a clean request environment
- `mock_db` overrides database access
- `mock_user` overrides authentication
- The endpoint runs exactly as if everything were real

---

#### Why This Pattern Works Well

- Fixtures compose naturally (add/remove mocks easily)
- Overrides are scoped to a single test
- Cleanup is automatic and reliable
- Tests stay focused on behavior, not setup

This is the **recommended pattern** for testing FastAPI applications that rely heavily on dependency injection.

---

```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    """Test client with clean dependency overrides"""
    client = TestClient(app)
    yield client
    # Cleanup after each test
    app.dependency_overrides.clear()

@pytest.fixture
def mock_db():
    """Mock database session"""
    def get_mock_db():
        return MockDatabase()

    app.dependency_overrides[get_db] = get_mock_db
    yield get_mock_db()

@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    def get_mock_user():
        return {"id": 1, "name": "Test User"}

    app.dependency_overrides[get_current_user] = get_mock_user
    yield get_mock_user()

# Tests use fixtures
def test_with_mocks(client, mock_db, mock_user):
    """Test with all mocks in place"""
    response = client.get("/protected-resource")
    assert response.status_code == 200
    # Both database and auth are mocked!

"""
Clean, reusable test fixtures.
Each test starts with clean state.
"""
```

---

## Security Dependencies

Security dependencies are specialized dependencies used for **authentication and authorization**. They work like normal dependencies but are explicitly marked as security-related, which allows FastAPI to:

- Integrate them into OpenAPI / Swagger documentation
- Clearly describe authentication requirements
- Support standard security schemes (API keys, OAuth2, JWT, etc.)

---

### Basic API Key Authentication

This example demonstrates **API key–based authentication** using a request header.

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

# Define security scheme
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify API key from header.

    Security() works like Depends(), but:
    - Marks this dependency as a security requirement
    - Exposes it properly in OpenAPI docs
    """
    valid_keys = ["secret-key-1", "secret-key-2"]

    if api_key not in valid_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return api_key

@app.get("/protected")
async def protected_route(api_key: str = Security(verify_api_key)):
    """
    Protected endpoint.

    Requires a valid API key in the X-API-Key header.
    """
    return {"message": "Access granted", "key": api_key}
```

---

### How This Works

#### Security Scheme Definition

```python
api_key_header = APIKeyHeader(name="X-API-Key")
```

- Declares where the API key comes from
- FastAPI automatically:

  - Extracts the header value
  - Validates its presence
  - Documents it in Swagger UI

---

#### `Security()` vs `Depends()`

```python
api_key: str = Security(api_key_header)
```

Key differences from `Depends()`:

- Marks the dependency as **security-related**
- Appears under the “Authorize” section in Swagger
- Is required for proper OpenAPI security definitions

Functionally, it behaves like `Depends()`.

---

#### Verification Logic

```python
def verify_api_key(api_key: str = Security(api_key_header)):
```

This dependency:

- Extracts the API key from the request header
- Validates it against allowed values
- Raises `HTTPException` if invalid
- Returns the API key if valid

If an exception is raised:

- The request stops immediately
- The handler is never executed

---

### Request Flow

**Valid request:**

```
GET /protected
X-API-Key: secret-key-1
```

Response:

```json
{
  "message": "Access granted",
  "key": "secret-key-1"
}
```

**Invalid request:**

```
GET /protected
X-API-Key: wrong-key
```

Response:

```json
{
  "detail": "Invalid API key"
}
```

---

### When to Use Security Dependencies

Use `Security()` when:

- Implementing authentication or authorization
- You want proper Swagger/OpenAPI documentation
- You are using standard security mechanisms:

  - API keys
  - OAuth2
  - JWT
  - Bearer tokens

For non-security concerns (logging, DB access, validation), prefer `Depends()`.

---

This pattern scales cleanly to more advanced authentication systems while keeping endpoints declarative and secure.

### OAuth2 Password Bearer

OAuth2 Password Bearer is a **standard authentication flow** where the client sends a **JWT access token** in the `Authorization` header using the `Bearer` scheme.

FastAPI provides first-class support for this pattern and automatically documents it in OpenAPI.

---

```python
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Extract and validate JWT token.

    oauth2_scheme extracts token from Authorization: Bearer <token>
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(401, "Invalid token")
    except JWTError:
        raise HTTPException(401, "Invalid token")

    # Get user from database
    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(401, "User not found")

    return user

@app.get("/users/me")
async def read_users_me(current_user = Depends(get_current_user)):
    """
    Get current user profile.

    Requires valid JWT token.
    """
    return current_user

"""
Request:
GET /users/me
Headers: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response: 200 OK
{"username": "alice", "email": "alice@example.com"}
"""
```

---

#### OAuth2 Scheme Definition

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
```

- Declares an OAuth2 **Password flow**
- Tells FastAPI:

  - Tokens are obtained from the `/token` endpoint
  - Requests must include `Authorization: Bearer <token>`

- Swagger UI automatically shows an **Authorize** button

---

#### Token Extraction and Validation Dependency

```python
def get_current_user(token: str = Depends(oauth2_scheme)):
```

- `oauth2_scheme`:

  - Extracts the token from the `Authorization` header
  - Validates header format (`Bearer <token>`)

- The dependency is responsible for:

  - Decoding the JWT
  - Validating token contents
  - Loading the authenticated user

If any step fails, an `HTTPException` is raised and the request stops.

---

#### JWT Decoding Logic

```python
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

- Verifies token signature and integrity
- Extracts claims from the payload
- Common practice:

  - Store the username or user ID in the `sub` claim

Validation checks:

- Token is well-formed
- Signature is valid
- Required claims exist

---

#### User Resolution

```python
user = get_user_by_username(username)
```

- Converts a valid token into an actual user
- Prevents access with:

  - Tokens for deleted users
  - Tokens referencing invalid identities

This step ensures **authorization is tied to real application state**, not just cryptography.

---

#### Protected Endpoint Usage

```python
async def read_users_me(current_user = Depends(get_current_user)):
```

- Endpoint is protected by the dependency
- Handler receives a fully authenticated user
- No authentication logic inside the handler

If authentication fails:

- Handler is never executed
- Client receives `401 Unauthorized`

---

#### Request Flow Summary

1. Client sends request with `Authorization: Bearer <token>`
2. `oauth2_scheme` extracts the token
3. JWT is decoded and validated
4. User is loaded from the database
5. Handler executes with authenticated user

---

#### When to Use OAuth2PasswordBearer

Use this pattern when:

- Implementing JWT-based authentication
- Supporting login-based access tokens
- Building APIs consumed by web or mobile clients
- You want standards-compliant, well-documented security

This is the **recommended foundation** for production-grade authentication in FastAPI.

---

### Role-Based Access Control (RBAC)

Role-Based Access Control restricts access to endpoints based on the **role assigned to the authenticated user**. In FastAPI, RBAC is cleanly implemented using **dependency factories**.

---

```python
from enum import Enum

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

def require_role(*allowed_roles: Role):
    """
    Dependency factory for role-based access.

    Returns a dependency that checks if user has required role.
    """
    def role_checker(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                403,
                f"Requires one of: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker

# Use in endpoints
@app.get("/users")
async def list_users(user = Depends(require_role(Role.ADMIN))):
    """Only admins can list all users"""
    return get_all_users()

@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    user = Depends(require_role(Role.ADMIN, Role.MODERATOR))
):
    """Admins and moderators can delete posts"""
    delete_post_by_id(post_id)
    return {"deleted": post_id}

@app.get("/profile")
async def get_profile(user = Depends(require_role(Role.USER, Role.ADMIN, Role.MODERATOR))):
    """Any authenticated user can see profile"""
    return user

"""
Flexible role checking:
- require_role(Role.ADMIN) - Only admins
- require_role(Role.ADMIN, Role.MODERATOR) - Admins or moderators
- require_role(Role.USER, Role.ADMIN, Role.MODERATOR) - Any authenticated user
"""
```

---

#### Role Definition

```python
from enum import Enum

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
```

- Roles are modeled as an `Enum` for:

  - Type safety
  - Clear allowed values
  - Better documentation

- Storing roles as strings keeps them compatible with databases and JWT claims

---

#### Dependency Factory for Role Checks

```python
def require_role(*allowed_roles: Role):
```

- This is a **dependency factory**
- It does **not** run validation itself
- Instead, it **creates and returns a dependency** configured with allowed roles

This enables:

- Reusable authorization logic
- Declarative security at the endpoint level
- Different role requirements per route

---

#### Role Validation Dependency

```python
def role_checker(current_user = Depends(get_current_user)):
```

- Depends on `get_current_user`, so:

  - Authentication happens first
  - Role checks only run for authenticated users

- Authorization logic:

  - User role must be in `allowed_roles`
  - Otherwise, request fails with `403 Forbidden`

The handler only runs if both authentication **and** authorization succeed.

---

#### Endpoint Usage Examples

```python
@app.get("/users")
async def list_users(user = Depends(require_role(Role.ADMIN))):
```

- Only users with the `ADMIN` role can access

```python
@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    user = Depends(require_role(Role.ADMIN, Role.MODERATOR))
):
```

- Allows multiple roles
- Any matching role is sufficient

```python
@app.get("/profile")
async def get_profile(
    user = Depends(require_role(Role.USER, Role.ADMIN, Role.MODERATOR))
):
```

- Any authenticated role is allowed
- Still enforces authentication via `get_current_user`

---

#### Why This Pattern Works Well

- **Separation of concerns**

  - Authentication: `get_current_user`
  - Authorization: `require_role`

- **Highly reusable**

  - Same factory, different rules

- **Explicit and readable**

  - Security rules are visible in the endpoint signature

- **Production-friendly**

  - Easy to extend (permissions, scopes, feature flags)

This pattern scales cleanly as applications grow and is the recommended way to implement RBAC in FastAPI.

### Permission-Based Authorization

```python
from typing import Set

class Permission(str, Enum):
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    DELETE_USERS = "delete:users"
    READ_POSTS = "read:posts"
    WRITE_POSTS = "write:posts"

def get_user_permissions(user = Depends(get_current_user)) -> Set[Permission]:
    """
    Get user's permissions from database/cache.
    """
    # In real app, query from database
    role_permissions = {
        "admin": {
            Permission.READ_USERS, Permission.WRITE_USERS, Permission.DELETE_USERS,
            Permission.READ_POSTS, Permission.WRITE_POSTS
        },
        "moderator": {
            Permission.READ_USERS, Permission.READ_POSTS, Permission.WRITE_POSTS
        },
        "user": {
            Permission.READ_POSTS
        }
    }

    return role_permissions.get(user.role, set())

def require_permission(permission: Permission):
    """
    Dependency factory for permission checking.
    """
    def permission_checker(permissions: Set[Permission] = Depends(get_user_permissions)):
        if permission not in permissions:
            raise HTTPException(403, f"Missing permission: {permission}")
        return True

    return permission_checker

@app.get("/users")
async def list_users(_= Depends(require_permission(Permission.READ_USERS))):
    """Requires read:users permission"""
    return get_all_users()

@app.post("/users")
async def create_user(
    user: UserCreate,
    _= Depends(require_permission(Permission.WRITE_USERS))
):
    """Requires write:users permission"""
    return create_new_user(user)

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    _= Depends(require_permission(Permission.DELETE_USERS))
):
    """Requires delete:users permission"""
    delete_user_by_id(user_id)
    return {"deleted": user_id}

"""
Fine-grained access control:
- Users can read posts
- Moderators can read/write posts and read users
- Admins can do everything

Easy to modify permissions without changing code!
"""
```

Permission-based authorization provides **fine-grained access control** by checking what a user is allowed to do, rather than only who they are. This is more flexible than role-only checks and is commonly used in production systems.

---

#### Permission Definition

```python
from typing import Set
from enum import Enum

class Permission(str, Enum):
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    DELETE_USERS = "delete:users"
    READ_POSTS = "read:posts"
    WRITE_POSTS = "write:posts"
```

- Permissions are defined as an `Enum` to:

  - Avoid magic strings
  - Ensure consistency across the codebase
  - Improve readability and maintainability

- Permissions follow a `resource:action` convention, which scales well.

---

#### Resolving User Permissions

```python
def get_user_permissions(user = Depends(get_current_user)) -> Set[Permission]:
```

- This dependency:

  - Runs **after authentication**
  - Converts a user’s role into a concrete set of permissions

- In real applications, permissions usually come from:

  - Database tables
  - Cached role-permission mappings
  - JWT claims (for read-heavy systems)

The function returns a `Set` for efficient membership checks.

---

#### Permission Check Dependency Factory

```python
def require_permission(permission: Permission):
```

- This is a **dependency factory**
- It generates a dependency configured for **one specific permission**
- The inner dependency:

  - Depends on `get_user_permissions`
  - Fails fast with `403 Forbidden` if permission is missing

This keeps authorization logic reusable and declarative.

---

#### Using Permissions in Endpoints

```python
@app.get("/users")
async def list_users(_ = Depends(require_permission(Permission.READ_USERS))):
```

- Side-effect-only dependency
- The handler does not need permission data, only validation

```python
@app.post("/users")
async def create_user(
    user: UserCreate,
    _ = Depends(require_permission(Permission.WRITE_USERS))
):
```

- Different permission, same factory
- No duplication of authorization logic

```python
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    _ = Depends(require_permission(Permission.DELETE_USERS))
):
```

- Clear, self-documenting access rules at the endpoint level

---

#### Why Permission-Based Authorization Scales Well

- **More granular than roles**

  - Roles group permissions
  - Permissions define actual capabilities

- **Easier to evolve**

  - Add or remove permissions without changing endpoint code

- **Production-friendly**

  - Works well with RBAC, ABAC, feature flags, and audit systems

- **Explicit security rules**

  - Authorization requirements are visible in function signatures

This pattern is commonly used in large systems where roles alone are not expressive enough.

---

## Database Session Dependencies

- Manages how database connections are **created, used, and cleaned up** per request.
- Prevents connection leaks and unsafe shared state.
- Uses FastAPI’s dependency system to handle session lifecycle automatically.

This pattern is essential for building reliable, concurrent backend services.

---

### Basic SQLAlchemy Pattern

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Database setup
DATABASE_URL = "postgresql://user:pass@localhost/dbname"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """
    Provide database session with automatic cleanup.

    Standard pattern for FastAPI + SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Use in endpoints
@app.get("/users")
async def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@app.post("/users")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
```

#### Database and Session Setup

```python
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

- `engine`

  - Manages the connection pool to the database.
  - Shared across the application.
  - `pool_pre_ping=True` checks connection health before use.

- `SessionLocal`

  - A **session factory**, not a session itself.
  - Creates a new database session when called.
  - `autocommit=False` enforces explicit transaction control.
  - `autoflush=False` avoids automatic writes before queries.

---

#### Database Session Dependency

```python
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- Creates **one database session per request**.
- `yield` hands the session to the endpoint.
- Code after `yield` runs after the request completes.
- `db.close()` guarantees cleanup even if an error occurs.

---

#### Using the Session in Endpoints

```python
async def list_users(db: Session = Depends(get_db)):
```

- `Depends(get_db)` injects a database session.
- The session is scoped only to the current request.

---

#### Read Operation

```python
users = db.query(User).all()
```

- Executes a database query using the injected session.
- No manual connection handling required.

---

#### Write Operation

```python
db_user = User(**user.dict())
db.add(db_user)
db.commit()
db.refresh(db_user)
```

- `User(**user.dict())`

  - Converts request data into an ORM model.

- `db.add(db_user)`

  - Marks the object for insertion.

- `db.commit()`

  - Persists changes to the database.

- `db.refresh(db_user)`

  - Reloads database-generated fields (e.g. primary key).

---

#### Why This Pattern Is Used

- One session per request
- Automatic cleanup
- Safe for concurrent requests
- Official FastAPI + SQLAlchemy recommendation

---

### Transaction Management

#### Purpose

- Ensures a group of database operations execute as **one atomic unit**.
- Automatically **commits on success** and **rolls back on failure**.
- Prevents partial writes that can corrupt data.

This pattern is critical for operations like payments, transfers, and multi-step updates.

---

#### Transaction-Aware Database Dependency

```python
def get_db_transaction():
    """
    Database session with automatic transaction management.

    Commits on success, rolls back on error.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

- Creates a new session per request.
- `yield db`

  - Provides the session to the endpoint.
  - Endpoint logic runs at this point.

- `db.commit()`

  - Executes only if no exception occurred.

- `db.rollback()`

  - Reverts all changes if any error is raised.

- `db.close()`

  - Always releases the connection.

---

#### Using the Transaction Dependency

```python
async def transfer_funds(
    from_id: int,
    to_id: int,
    amount: float,
    db: Session = Depends(get_db_transaction)
):
```

- The entire endpoint runs inside a single transaction.
- No need to manually call `commit()` or `rollback()`.

---

#### Transactional Business Logic

```python
source = db.query(Account).get(from_id)
source.balance -= amount
```

- Fetches the source account.
- Updates the balance in memory.
- No database write yet.

```python
dest = db.query(Account).get(to_id)
dest.balance += amount
```

- Fetches the destination account.
- Applies the second update.

---

#### Failure Behavior

- If **any line raises an exception**:

  - `db.commit()` is skipped.
  - `db.rollback()` is triggered.
  - Both balance changes are undone.

This guarantees **all-or-nothing** behavior.

---

#### Why This Pattern Is Important

- Maintains data consistency
- Prevents partial updates
- Centralizes transaction control
- Keeps endpoint code clean and focused

```python
def get_db_transaction():
    """
    Database session with automatic transaction management.

    Commits on success, rolls back on error.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Commit if no exception
    except Exception:
        db.rollback()  # Rollback on error
        raise
    finally:
        db.close()

@app.post("/transfer")
async def transfer_funds(
    from_id: int,
    to_id: int,
    amount: float,
    db: Session = Depends(get_db_transaction)
):
    """
    Transfer funds with automatic rollback on error.
    """
    # Deduct from source
    source = db.query(Account).get(from_id)
    source.balance -= amount

    # Add to destination
    dest = db.query(Account).get(to_id)
    dest.balance += amount

    # If any operation fails, entire transaction rolls back!
    return {"transferred": amount}
```

---

### Repository Pattern

#### Purpose

- Separates **database access logic** from API and business logic.
- Encapsulates queries and persistence inside dedicated classes.
- Makes code easier to maintain, test, and evolve.

This pattern is commonly used in medium to large codebases.

```python
class UserRepository:
    """Repository for user database operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def create(self, user_data: dict):
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: int, user_data: dict):
        user = self.get_by_id(user_id)
        for key, value in user_data.items():
            setattr(user, key, value)
        self.db.commit()
        return user

def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    """Provide user repository"""
    return UserRepository(db)

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo)
):
    """Use repository instead of raw database session"""
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user

@app.post("/users")
async def create_user(
    user: UserCreate,
    repo: UserRepository = Depends(get_user_repo)
):
    """Repository handles all database logic"""
    return repo.create(user.dict())

"""
Benefits of repository pattern:
- Business logic separated from database logic
- Reusable database operations
- Easier to test (mock repository)
- Consistent database access patterns
"""
```

---

#### Repository Class

```python
class UserRepository:
    """Repository for user database operations"""
```

- Represents a **single aggregate or entity** (`User`).
- Contains all database-related logic for that entity.

---

#### Initializing the Repository

```python
def __init__(self, db: Session):
    self.db = db
```

- Receives a database session via dependency injection.
- Does not create or manage the session lifecycle.

---

#### Read Operations

```python
def get_by_id(self, user_id: int):
    return self.db.query(User).filter(User.id == user_id).first()
```

- Fetches a single user by primary key.
- Returns `None` if no record exists.

```python
def get_by_email(self, email: str):
    return self.db.query(User).filter(User.email == email).first()
```

- Encapsulates query logic behind a clear method name.
- Prevents query duplication across endpoints.

---

#### Create Operation

```python
def create(self, user_data: dict):
    user = User(**user_data)
    self.db.add(user)
    self.db.commit()
    self.db.refresh(user)
    return user
```

- Converts raw input data into an ORM model.
- Handles persistence and transaction commit.
- Returns the fully populated entity.

---

#### Update Operation

```python
def update(self, user_id: int, user_data: dict):
    user = self.get_by_id(user_id)
    for key, value in user_data.items():
        setattr(user, key, value)
    self.db.commit()
    return user
```

- Retrieves the existing entity.
- Applies partial updates dynamically.
- Commits changes in a single transaction.

---

#### Repository Dependency

```python
def get_user_repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)
```

- Creates a repository per request.
- Injects the database session automatically.
- Keeps endpoints free from database setup logic.

---

#### Using the Repository in Endpoints

```python
async def get_user(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo)
):
```

- Endpoints depend on the repository, not the database.
- Improves readability and separation of concerns.

---

#### Endpoint Example: Read

```python
user = repo.get_by_id(user_id)
if not user:
    raise HTTPException(404, "User not found")
return user
```

- Business rules live in the endpoint.
- Data access remains inside the repository.

---

#### Endpoint Example: Create

```python
return repo.create(user.dict())
```

- Endpoint delegates all persistence logic.
- Keeps request handling concise.

---

#### Why Use the Repository Pattern

- Clear separation between API and data layers
- Reusable and centralized database logic
- Easier unit testing with mocked repositories
- Consistent access patterns across the application

---

## Advanced Dependency Patterns

- Builds on FastAPI’s dependency system to handle **dynamic behavior**.
- Allows selecting implementations at runtime.
- Useful when infrastructure or logic varies per request.

These patterns help keep endpoints clean while supporting complex scenarios.

---

### Conditional Dependencies

- Choose between multiple implementations based on request data.
- Commonly driven by query parameters, headers, or environment flags.
- Avoids branching logic inside endpoint functions.

---

```python
def get_db_or_cache(use_cache: bool = Query(False)):
    """
    Return either database or cache based on query parameter.
    """
    if use_cache:
        return RedisCache()
    else:
        return get_database()

@app.get("/items")
async def list_items(
    storage = Depends(get_db_or_cache)
):
    """
    GET /items?use_cache=true  → Uses cache
    GET /items?use_cache=false → Uses database
    """
    return storage.get_items()
```

#### Conditional Dependency Function

```python
def get_db_or_cache(use_cache: bool = Query(False)):
```

- Accepts request input directly inside the dependency.
- `use_cache` is read from the query string.

```python
if use_cache:
    return RedisCache()
else:
    return get_database()
```

- Returns different objects based on runtime conditions.
- The endpoint does not need to know which implementation is used.

---

#### Using the Conditional Dependency

```python
async def list_items(
    storage = Depends(get_db_or_cache)
):
```

- `storage` can be backed by cache or database.
- The endpoint depends on an **interface-like contract**, not a concrete source.

---

#### Request Behavior

```text
GET /items?use_cache=true   → Uses Redis cache
GET /items?use_cache=false  → Uses database
```

- Behavior changes without modifying endpoint code.
- Dependency logic remains centralized.

---

#### Why This Pattern Is Useful

- Reduces conditional logic in endpoints
- Improves flexibility and extensibility
- Supports caching, feature flags, and fallbacks
- Keeps API handlers simple and declarative

### Dependency Composition

- Combines multiple related dependencies into a **single higher-level dependency**.
- Reduces the number of parameters in endpoint functions.
- Groups infrastructure concerns (DB, cache, logging) together.

This pattern is useful when multiple endpoints require the same set of services.

---

```python
class ServiceContainer:
    """Container holding multiple services"""

    def __init__(
        self,
        db: Session = Depends(get_db),
        cache = Depends(get_cache),
        logger = Depends(get_logger)
    ):
        self.db = db
        self.cache = cache
        self.logger = logger

@app.get("/complex-operation")
async def complex_op(services: ServiceContainer = Depends()):
    """
    Single dependency provides all services!
    """
    services.logger.info("Starting operation")

    # Check cache
    cached = services.cache.get("key")
    if cached:
        return cached

    # Query database
    data = services.db.query(Item).all()
    services.cache.set("key", data)

    return data
```

#### Composed Dependency Container

```python
class ServiceContainer:
    """Container holding multiple services"""
```

- Acts as a lightweight service holder.
- Does not contain business logic, only dependencies.

---

#### Injecting Dependencies into the Container

```python
def __init__(
    self,
    db: Session = Depends(get_db),
    cache = Depends(get_cache),
    logger = Depends(get_logger)
):
```

- Each parameter is a FastAPI dependency.
- FastAPI resolves these before creating the container.
- All services are initialized **once per request**.

```python
self.db = db
self.cache = cache
self.logger = logger
```

- Exposes resolved dependencies as attributes.
- Makes access explicit and structured.

---

#### Using the Composed Dependency in an Endpoint

```python
@app.get("/complex-operation")
async def complex_op(services: ServiceContainer = Depends()):
```

- Only one dependency is declared in the endpoint.
- Internally provides access to database, cache, and logger.

---

#### Complete Endpoint Flow

```python
services.logger.info("Starting operation")
```

- Logging handled through injected logger.

```python
cached = services.cache.get("key")
if cached:
    return cached
```

- Cache is checked first.
- Allows early return without hitting the database.

```python
data = services.db.query(Item).all()
services.cache.set("key", data)
```

- Database query runs only on cache miss.
- Result is stored back in cache.

```python
return data
```

- Returns the final response to the client.

---

#### Why Use Dependency Composition

- Cleaner endpoint signatures
- Logical grouping of related services
- Easier refactoring as dependencies grow
- Consistent service access across endpoints

### Factory Pattern

#### Purpose

- Creates dependencies **dynamically** based on configuration.
- Encapsulates object creation logic in one place.
- Avoids hard-coding concrete implementations inside endpoints.

This pattern is useful when multiple endpoints use the same interface with different implementations.

---

```python
def create_service_factory(service_type: str):
    """
    Factory that creates different dependencies based on parameter.
    """
    def get_service():
        if service_type == "email":
            return EmailService()
        elif service_type == "sms":
            return SMSService()
        else:
            raise ValueError(f"Unknown service: {service_type}")

    return get_service

# Use factory
email_service = Depends(create_service_factory("email"))
sms_service = Depends(create_service_factory("sms"))

@app.post("/notify/email")
async def notify_email(message: str, service = Depends(email_service)):
    service.send(message)

@app.post("/notify/sms")
async def notify_sms(message: str, service = Depends(sms_service)):
    service.send(message)
```

#### Dependency Factory Function

```python
def create_service_factory(service_type: str):
    """
    Factory that creates different dependencies based on parameter.
    """
```

- Accepts a configuration value (`service_type`).
- Returns a dependency function instead of a concrete object.

---

#### Inner Dependency

```python
def get_service():
    if service_type == "email":
        return EmailService()
    elif service_type == "sms":
        return SMSService()
    else:
        raise ValueError(f"Unknown service: {service_type}")
```

- Runs at request time.
- Chooses the correct implementation.
- Raises an error for unsupported service types.

---

#### Returning the Dependency

```python
return get_service
```

- FastAPI treats the returned function as a dependency.
- Allows reuse with different configurations.

---

#### Creating Concrete Dependencies

```python
email_service = Depends(create_service_factory("email"))
sms_service = Depends(create_service_factory("sms"))
```

- Each dependency is preconfigured.
- Endpoints do not need to know how services are created.

---

#### Complete Usage Example

```python
@app.post("/notify/email")
async def notify_email(
    message: str,
    service = Depends(email_service)
):
    service.send(message)
```

- Injects an `EmailService` instance.
- Endpoint logic remains implementation-agnostic.

```python
@app.post("/notify/sms")
async def notify_sms(
    message: str,
    service = Depends(sms_service)
):
    service.send(message)
```

- Injects an `SMSService` instance.
- Same interface, different behavior.

---

#### Why Use the Factory Pattern

- Centralizes creation logic
- Supports multiple implementations cleanly
- Improves extensibility without changing endpoints
- Works well with configuration-driven systems

---

## Complete Production Examples

### Example 1: Production-Ready API with All Patterns

```python
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging

# Setup
app = FastAPI(title="Production API")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Logging
def get_logger():
    return logging.getLogger(__name__)

# Database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get authenticated user from token"""
    user = verify_token(token, db)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    return user

# Authorization
def require_admin(user = Depends(get_current_user)):
    """Ensure user is admin"""
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user

# Repository
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(User).all()

    def get_by_id(self, user_id: int):
        return self.db.query(User).get(user_id)

def get_user_repo(db: Session = Depends(get_db)):
    return UserRepository(db)

# Service
class UserService:
    def __init__(
        self,
        repo: UserRepository = Depends(get_user_repo),
        logger = Depends(get_logger)
    ):
        self.repo = repo
        self.logger = logger

    def list_users(self):
        self.logger.info("Listing all users")
        return self.repo.get_all()

    def get_user(self, user_id: int):
        self.logger.info(f"Getting user {user_id}")
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(404, "User not found")
        return user

# Endpoints
@app.get("/users")
async def list_users(
    service: UserService = Depends(),
    _= Depends(require_admin)
):
    """
    List all users.

    Dependencies:
    - Authentication (via get_current_user)
    - Authorization (via require_admin)
    - Database session (via get_db)
    - Repository (via get_user_repo)
    - Service (via UserService)
    - Logger (via get_logger)

    All handled automatically!
    """
    return service.list_users()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(),
    current_user = Depends(get_current_user)
):
    """
    Get user by ID.

    Requires authentication but not admin.
    """
    return service.get_user(user_id)
```

---

## Key Takeaways

1. **Yield for Cleanup** - Always use try/finally with yield
2. **Caching is Automatic** - Trust FastAPI's caching per request
3. **Global for All** - Use sparingly, mainly for auth/logging
4. **Router for Groups** - Organize by feature with router dependencies
5. **Override for Tests** - Essential for isolated testing
6. **Security Dependencies** - Use Security() for auth in docs
7. **Database Patterns** - Session per request, repository pattern
8. **Layer Dependencies** - Global → Router → Endpoint

---

## Practice Exercises

1. **Create authentication system** with JWT and refresh tokens
2. **Build repository pattern** for user and post entities
3. **Write tests** using dependency overrides
4. **Implement RBAC** with role and permission checks
5. **Create service layer** with dependency composition

---

**Congratulations!** You've mastered advanced dependency injection in FastAPI. Tomorrow we'll explore Response Handling and Models!
