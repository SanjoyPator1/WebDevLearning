# FastAPI Dependencies, Sessions & Connection Pooling - Deep Dive

## 📚 Table of Contents

1. [Your Question Explained](#your-question-explained)
2. [Dependency Caching (Single Request)](#dependency-caching-single-request)
3. [Session Management Per Request](#session-management-per-request)
4. [Connection Pooling (Multiple Users)](#connection-pooling-multiple-users)
5. [Complete Real-World Scenarios](#complete-real-world-scenarios)
6. [Performance Analysis](#performance-analysis)

---

## ❓ Your Question Explained

### Your Concern (Very Valid!)

```python
@router.get("/me")
async def get_profile(current_user: CurrentUser):
    # You think:
    # 1. CurrentUser depends on get_current_user
    # 2. get_current_user depends on get_user_service
    # 3. get_user_service depends on get_db
    #
    # So get_db() is called 3 times? ❌ NO!
    return current_user
```

**Your concern:** "Doesn't this call the database multiple times?"

**Answer:** **NO!** FastAPI is smart - it **caches dependencies** within a single request.

---

## 🔄 Dependency Caching (Single Request)

### How FastAPI Handles Dependencies

**Key Concept:** FastAPI calls each dependency **only ONCE per request**, even if multiple dependencies need it.

### Example: Protected Endpoint

```python
@router.post("/todos")
async def create_todo(
    todo_in: TodoCreate,
    current_user: CurrentUser,          # Needs: get_db → get_user_service → get_current_user
    todo_service: TodoServiceDep,       # Needs: get_db → get_todo_service
    user_service: UserServiceDep        # Needs: get_db → get_user_service
):
    # Do something
    pass
```

### What You Might Think Happens (WRONG ❌)

```
Request arrives
    ↓
Resolve current_user:
    get_db() called #1 → Creates Session A
    get_user_service(Session A)
    get_current_user(...)
    ↓
Resolve todo_service:
    get_db() called #2 → Creates Session B  ❌ WRONG!
    get_todo_service(Session B)
    ↓
Resolve user_service:
    get_db() called #3 → Creates Session C  ❌ WRONG!
    get_user_service(Session C)
    ↓
3 database sessions created! ❌
```

### What Actually Happens (CORRECT ✅)

```
Request arrives
    ↓
FastAPI dependency resolver starts
    ↓
Step 1: Analyze all dependencies
    current_user needs: get_db, get_user_service, get_current_user
    todo_service needs: get_db, get_todo_service
    user_service needs: get_db, get_user_service
    ↓
Step 2: Build dependency graph
    get_db (needed by all) ←┐
        ├→ get_user_service  │
        │   ├→ get_current_user (for current_user)
        │   └→ (reused for user_service)  ← REUSED!
        └→ get_todo_service
    ↓
Step 3: Execute dependencies in order (ONLY ONCE EACH)
    ├─ get_db() → Session A (called once) ✅
    ├─ get_user_service(Session A) → UserService instance (called once) ✅
    ├─ get_todo_service(Session A) → TodoService instance (called once) ✅
    └─ get_current_user(...) → User object (called once) ✅
    ↓
Step 4: Inject into endpoint
    current_user = User(...)
    todo_service = TodoService(Session A)  ← Same session
    user_service = UserService(Session A)  ← Same session
    ↓
Step 5: Execute endpoint code
    All services use SAME session A ✅
    ↓
Step 6: Cleanup (after response)
    Close Session A
```

### Visual Diagram

```
Single Request: POST /todos
┌────────────────────────────────────────────────────────────┐
│  FastAPI Dependency Cache (Lives for this request only)    │
├────────────────────────────────────────────────────────────┤
│  get_db:           Session A (created ONCE)                │
│  get_user_service: UserService(Session A) (created ONCE)   │
│  get_todo_service: TodoService(Session A) (created ONCE)   │
│  get_current_user: User object (created ONCE)              │
└────────────────────────────────────────────────────────────┘
         │         │         │         │
         └─────────┴─────────┴─────────┴────────┐
                                                │
                    All endpoints get these ────┘
                    (NO duplication!)

After response sent → Cache cleared → Session closed
```

---

## 💾 Session Management Per Request

### What is a Database Session?

**Database Session = A "workspace" for database operations**

```python
async with AsyncSessionLocal() as session:
    # Session starts here
    # All operations within this block use the same transaction

    user = await session.execute(select(User).where(User.id == 1))
    todo = await session.execute(select(Todo).where(Todo.id == 1))

    await session.commit()  # Save all changes together
    # Session ends here (automatically closed)
```

### Session Lifecycle in FastAPI

**File: `app/db/session.py`**

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session  # ← FastAPI gets session here
            # Endpoint executes with this session
            # All dependencies use this session
        finally:
            await session.close()  # ← Automatic cleanup
```

**Visual Timeline:**

```
Request arrives
    ↓
get_db() called
    ↓
Session created from pool (see Connection Pooling below)
    ↓
yield session ← FastAPI takes this
    │
    │ (Endpoint + all dependencies execute)
    │ (All using SAME session)
    │
Endpoint returns response
    ↓
get_db() continues after yield
    ↓
session.close() ← Return connection to pool
    ↓
Response sent to client
```

### One Session Per Request Rule

```
Request 1 (User A): GET /users/me
    ├─ Creates Session 1
    ├─ All dependencies use Session 1
    ├─ Response sent
    └─ Session 1 closed

Request 2 (User B): GET /todos
    ├─ Creates Session 2 (NEW session)
    ├─ All dependencies use Session 2
    ├─ Response sent
    └─ Session 2 closed

Request 3 (User A again): POST /todos
    ├─ Creates Session 3 (NEW session, even same user)
    ├─ All dependencies use Session 3
    ├─ Response sent
    └─ Session 3 closed
```

**Key Point:** Each request gets its **own isolated session**, but within that request, **all dependencies share the same session**.

---

## 🏊 Connection Pooling (Multiple Users)

### The Real Magic: Connection Pool

**Question:** If each request creates a session, don't we create too many database connections?

**Answer:** No! Sessions **reuse connections** from a **pool**.

### Connection Pool Configuration

**File: `app/db/session.py`**

```python
engine = create_async_engine(
    settings.database_url_asyncpg,
    echo=settings.DEBUG,
    pool_pre_ping=True,    # Test connection before use
    pool_size=5,           # Keep 5 connections ready
    max_overflow=10,       # Allow 10 more if needed (max 15 total)
)
```

**What this means:**

```
Connection Pool (Lives for entire application lifetime)
┌─────────────────────────────────────────────────────┐
│  Pool Size = 5 (always maintained)                  │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │Conn 1│ │Conn 2│ │Conn 3│ │Conn 4│ │Conn 5│       │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘       │
│                                                     │
│  Max Overflow = 10 (created on demand)              │
│  ┌──────┐ ┌──────┐ ┌──────┐                         │
│  │Conn 6│ │Conn 7│ │Conn 8│ ... (up to Conn 15)     │
│  └──────┘ └──────┘ └──────┘                         │
└─────────────────────────────────────────────────────┘
         ↑                    ↑
    Persistent          Created/destroyed
    (always alive)      as needed
```

### How Sessions Use Connections

**Important:** Session ≠ Connection

```
Session (short-lived, per request)
    ↓
Borrows connection from pool
    ↓
Uses connection
    ↓
Returns connection to pool
    ↓
Session destroyed, connection still alive in pool
```

### Real-World Scenario: 3 Users Making Requests

```
Time: 0ms
Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          idle    idle    idle    idle    idle

─────────────────────────────────────────────────────────

Time: 10ms - User A: GET /users/me
Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          IN USE  idle    idle    idle    idle
                   ↑
              Session 1 uses Conn1

─────────────────────────────────────────────────────────

Time: 15ms - User B: GET /todos
Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          IN USE  IN USE  idle    idle    idle
                   ↑       ↑
              Session 1  Session 2 uses Conn2
              (User A)   (User B)

─────────────────────────────────────────────────────────

Time: 20ms - User C: POST /todos
Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          IN USE  IN USE  IN USE  idle    idle
                   ↑       ↑       ↑
              Session 1  Session 2  Session 3 uses Conn3
              (User A)   (User B)   (User C)

─────────────────────────────────────────────────────────

Time: 25ms - User A's request finishes
Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          idle    IN USE  IN USE  idle    idle
                   ↑       ↑       ↑
              Returned   Still   Still
              to pool    in use  in use

─────────────────────────────────────────────────────────

Time: 30ms - User D: GET /users (reuses Conn1!)
Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          IN USE  IN USE  IN USE  idle    idle
                   ↑       ↑       ↑
              Session 4  Session 2  Session 3
              (User D)   (User B)   (User C)
              REUSED!

─────────────────────────────────────────────────────────

Time: 50ms - All requests finished
Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          idle    idle    idle    idle    idle
                   ↑       ↑       ↑       ↑       ↑
              All connections back in pool, ready for reuse
```

### What Happens With 20 Concurrent Users?

```
Users 1-5:   Use Conn1-5 (from pool)
Users 6-15:  Use Conn6-15 (from overflow)
Users 16-20: WAIT for a connection to become available

Pool Status:
┌────────────────────────────────────┐
│ Pool (5):     All IN USE           │
│ Overflow (10): All IN USE          │
│ Queue (5):    Waiting...           │
└────────────────────────────────────┘

As requests complete:
User 1 finishes → Conn1 available → User 16 takes it
User 2 finishes → Conn2 available → User 17 takes it
... and so on
```

### Connection Pool Settings Explained

```python
pool_size=5           # Always maintain 5 connections
                      # Created when app starts
                      # Never destroyed (until app shutdown)
                      # Best for: steady baseline load

max_overflow=10       # Allow up to 10 additional connections
                      # Created on demand when pool exhausted
                      # Destroyed when idle for too long
                      # Best for: handling traffic spikes

# Total possible connections: 5 + 10 = 15
```

**Recommendations:**

```python
# Small app (1-10 concurrent users)
pool_size=2
max_overflow=3
# Total: 5 connections

# Medium app (10-100 concurrent users)
pool_size=5
max_overflow=10
# Total: 15 connections (your current setup)

# Large app (100-1000 concurrent users)
pool_size=20
max_overflow=30
# Total: 50 connections

# Also consider PostgreSQL max_connections setting!
# Default is 100, so don't exceed that
```

---

## 🌐 Complete Real-World Scenarios

### Scenario 1: Single User, Single Request

```
User A: GET /users/me
Token: Bearer abc123

FastAPI receives request
    ↓
Resolve dependencies:
    ├─ oauth2_scheme: Extract "abc123"
    ├─ get_db: Borrow Conn1 from pool → Session A
    ├─ get_user_service(Session A): UserService instance
    └─ get_current_user(token, service):
        ├─ Decode token → {"sub": "1"}
        ├─ Query DB using Session A: SELECT * FROM users WHERE id=1
        └─ Return User(id=1, ...)
    ↓
Execute endpoint:
    return User(id=1, ...)
    ↓
Cleanup:
    Session A closed → Conn1 returned to pool
    ↓
Response: 200 OK

Database Activity:
    1 query: SELECT * FROM users WHERE id=1

Connection Pool:
    Conn1: borrowed → used → returned (still alive)

Total DB Connections Used: 1
Session Count: 1
```

### Scenario 2: Single User, Multiple Dependencies

```
User A: POST /todos
Token: Bearer abc123
Body: {"title": "Buy milk"}

FastAPI receives request
    ↓
Resolve dependencies:
    ├─ get_db: Borrow Conn1 → Session A (CREATED ONCE)
    │
    ├─ get_user_service(Session A): UserService instance
    │   (REUSES Session A)
    │
    ├─ get_todo_service(Session A): TodoService instance
    │   (REUSES Session A)
    │
    └─ get_current_user(token, user_service):
        ├─ Decode token
        ├─ Query using Session A: SELECT * FROM users WHERE id=1
        └─ Return User(id=1)
    ↓
Execute endpoint:
    ├─ user_service.get_user(1) using Session A
    │   Query: SELECT * FROM users WHERE id=1 (might hit cache)
    │
    └─ todo_service.create(todo_in, user.id) using Session A
        Query: INSERT INTO todos (title, owner_id) VALUES (...)
    ↓
Cleanup:
    Session A closed → Conn1 returned to pool
    ↓
Response: 201 Created

Database Activity:
    1. SELECT * FROM users WHERE id=1 (auth)
    2. SELECT * FROM users WHERE id=1 (endpoint - may be cached)
    3. INSERT INTO todos (...)

Connection Pool:
    Conn1: borrowed → used for all queries → returned

Total DB Connections Used: 1 (SAME connection for all)
Session Count: 1 (SHARED by all dependencies)
```

### Scenario 3: Multiple Users, Concurrent Requests

```
Time: 0ms - System idle
Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          idle    idle    idle    idle    idle

═══════════════════════════════════════════════════════════

Time: 10ms
User A: GET /users/me (Token: abc123)

Dependency Resolution:
    get_db → Borrow Conn1 → Session A1
    get_current_user → Query with Session A1

Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          IN USE  idle    idle    idle    idle
                    ↑
                Session A1 (User A)

Database: SELECT * FROM users WHERE id=1

═══════════════════════════════════════════════════════════

Time: 15ms (User A still processing)
User B: GET /todos (Token: def456)

Dependency Resolution:
    get_db → Borrow Conn2 → Session B1 (NEW SESSION)
    get_current_user → Query with Session B1
    get_todo_service → Uses same Session B1

Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          IN USE  IN USE  idle    idle    idle
                    ↑       ↑
                Session A1 Session B1
                (User A)   (User B)

Database:
    Conn1: SELECT * FROM users WHERE id=1 (User A)
    Conn2: SELECT * FROM users WHERE id=2 (User B auth)
           SELECT * FROM todos WHERE owner_id=2 (User B data)

═══════════════════════════════════════════════════════════

Time: 20ms (Both still processing)
User C: POST /todos (Token: ghi789)

Dependency Resolution:
    get_db → Borrow Conn3 → Session C1 (NEW SESSION)
    get_current_user → Query with Session C1
    get_todo_service → Uses same Session C1

Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          IN USE  IN USE  IN USE  idle    idle
                    ↑       ↑       ↑
                Session A1 Session B1 Session C1
                (User A)   (User B)   (User C)

Database:
    Conn1: Still in use
    Conn2: Still in use
    Conn3: SELECT * FROM users WHERE id=3 (User C auth)
           INSERT INTO todos (...) (User C create)

═══════════════════════════════════════════════════════════

Time: 25ms - User A finishes

Session A1 closed → Conn1 returned to pool

Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          idle    IN USE  IN USE  idle    idle
                    ↑       ↑       ↑
                Available Session B1 Session C1
                for reuse (User B)   (User C)

═══════════════════════════════════════════════════════════

Time: 30ms - User D makes request
User D: GET /users/me (Token: jkl012)

Dependency Resolution:
    get_db → Borrow Conn1 (REUSED from pool!) → Session D1

Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          IN USE  IN USE  IN USE  idle    idle
                    ↑       ↑       ↑
                Session D1 Session B1 Session C1
                (User D)   (User B)   (User C)
                REUSED!

Database:
    Conn1: SELECT * FROM users WHERE id=4 (User D)
           (Same physical connection, new session)

═══════════════════════════════════════════════════════════

Time: 50ms - All users finish

All sessions closed → All connections returned

Connection Pool: [Conn1] [Conn2] [Conn3] [Conn4] [Conn5]
Status:          idle    idle    idle    idle    idle
                    ↑       ↑       ↑       ↑       ↑
                All alive and ready for next requests

Summary:
    4 HTTP requests
    4 database sessions (one per request)
    3 database connections used (Conn1 reused)
    0 database connections created/destroyed
    All 5 pool connections still alive
```

---

## 📊 Performance Analysis

### Dependency Caching Impact

**Without Caching (Hypothetical - FastAPI doesn't do this):**

```
Request with 3 dependencies needing DB:
    get_db() called 3 times
    3 sessions created
    3 connections borrowed from pool
    3 sets of queries

    Time: ~30ms per query × 3 = 90ms
    Overhead: High
```

**With Caching (FastAPI's actual behavior):**

```
Request with 3 dependencies needing DB:
    get_db() called 1 time (cached for other 2)
    1 session created
    1 connection borrowed from pool
    Queries run in same transaction

    Time: ~30ms total
    Overhead: Minimal

    Performance gain: 3x faster!
```

### Connection Pool Impact

**Without Pool (Every request creates new connection):**

```
Request:
    Connect to PostgreSQL (50-100ms)
    Execute query (10ms)
    Close connection (20ms)

    Total: 80-130ms per request

100 requests:
    Total time: 8,000-13,000ms (8-13 seconds)
    Database load: Very high (100 connects/disconnects)
```

**With Pool (Reuse connections):**

```
Request:
    Borrow from pool (1ms)
    Execute query (10ms)
    Return to pool (1ms)

    Total: 12ms per request

100 requests:
    Total time: 1,200ms (1.2 seconds) with concurrency
    Database load: Low (5-15 persistent connections)

    Performance gain: 10x faster!
```

### Real Numbers Example

**Scenario:** 100 concurrent users hitting `/users/me`

```
With FastAPI dependency caching + connection pooling:

Connections needed: 15 (5 pool + 10 overflow)
Each request:
    ├─ Borrow connection: 1ms
    ├─ get_db called: 1 time (not 3!)
    ├─ Query execution: 10ms
    └─ Return connection: 1ms
    Total: ~12ms

First 15 users: Immediate (0ms wait)
Users 16-100: Wait for available connection (~50ms average)

Total processing time: ~150ms for all 100 requests
Database connections: 15 active (not 100!)
```

**Without these optimizations:**

```
Each request:
    ├─ Create connection: 50ms
    ├─ get_db called: 3 times
    ├─ Query execution: 10ms × 3 = 30ms
    └─ Close connection: 20ms
    Total: ~100ms

All sequential: 10,000ms (10 seconds)
Database connections: 100 simultaneous (if PostgreSQL allows)
```

---

## 🎯 Key Takeaways

### 1. Dependency Caching (Per Request)

✅ **Each dependency called ONCE per request**
✅ **Shared across all endpoint parameters**
✅ **Cache cleared after response**

```python
# Even with 10 dependencies all needing get_db:
# get_db() is called only 1 time!
@router.post("/complex")
async def complex_endpoint(
    dep1: Dep1,  # needs get_db
    dep2: Dep2,  # needs get_db
    dep3: Dep3,  # needs get_db
    # ... 7 more dependencies all needing get_db
):
    # get_db() called once, result shared by all 10
    pass
```

### 2. One Session Per Request

✅ **Each HTTP request gets one database session**
✅ **Session shared by all dependencies in that request**
✅ **Session automatically closed after response**
✅ **Provides transaction isolation**

### 3. Connection Pooling

✅ **Connections persist across requests**
✅ **Borrowed from pool, not created**
✅ **Reused for different sessions**
✅ **Configurable size (pool_size + max_overflow)**

### 4. No Redundant Database Calls

```
Single Request Flow:
    ├─ get_db() → 1 session created
    ├─ Multiple dependencies → ALL use same session
    └─ Multiple services → ALL use same session

Result: 1 database session, 1 connection, minimal overhead
```

### 5. Scaling

```
1 user:       1 connection from pool (5 available)
10 users:     10 connections (5 pool + 5 overflow)
20 users:     15 connections (5 pool + 10 overflow)
21st user:    Waits for available connection

Configure based on your load!
```

---

## 🚨 Common Misconceptions

### ❌ WRONG: "Each dependency creates new DB connection"

```python
@router.get("/me")
async def get_me(
    user: CurrentUser,        # Creates connection? NO!
    service: UserServiceDep   # Creates another? NO!
):
    # Only 1 connection borrowed from pool
    # Shared by both dependencies
    pass
```

### ❌ WRONG: "get_db() called multiple times = multiple sessions"

```python
# FastAPI calls get_db() ONCE per request
# Result cached and shared
# Even if 100 dependencies need it!
```

### ❌ WRONG: "Connection pool creates new connections for each request"

```python
# Pool REUSES existing connections
# New connections only created if pool exhausted
# Most requests use existing connections from pool
```

### ✅ CORRECT Understanding:

```
Per Request:
    1 session (shared by all dependencies via caching)
    1 connection (borrowed from pool, not created)

Across Requests:
    N sessions (one per request)
    5-15 connections (from pool, reused)
```

---

## 🎓 Summary

**Your original question was excellent!** It showed you're thinking about performance.

**The answer:**

1. **Dependencies are cached** - Called once per request
2. **Sessions are per-request** - One session per HTTP request
3. **Connections are pooled** - Reused across many sessions
4. **Result:** Minimal database overhead, excellent performance

**Visual Summary:**

```
Request Level:
    1 Request → 1 Session → 1 Connection from pool
    All dependencies share this session

Application Level:
    N Requests → N Sessions → 5-15 Pooled Connections (reused)
    Connections persist and are recycled

Database Level:
    Sees 5-15 long-lived connections (not thousands)
    Much more efficient than creating/destroying
```

You're not making redundant database calls - FastAPI handles this brilliantly! 🎉
