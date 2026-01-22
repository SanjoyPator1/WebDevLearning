# Day 4: Dependency Injection - Code Examples

Practical code examples for FastAPI Dependency Injection concepts from your Day 4 notes.

## Setup

```bash
pip install -r requirements.txt
```

## Files Overview

### 01_basic_dependencies.py
**Topics**: Basic DI concepts, function dependencies, reusable dependencies

**Key Examples**:
- Simple function dependencies
- Dependencies with parameters (pagination)
- Reusable dependencies across endpoints
- Multiple dependencies in one endpoint
- Different return types

**Run**:
```bash
uvicorn 01_basic_dependencies:app --reload
```

**Test Endpoints**:
```bash
# Basic dependency
curl http://localhost:8000/greet

# Pagination
curl "http://localhost:8000/items?skip=10&limit=20"

# Multiple dependencies (requires headers and cookie)
curl -H "X-Token: secret-token" -H "X-Key: secret-key" \
     -b "session_id=abc123" http://localhost:8000/secure-resource
```

---

### 02_class_dependencies.py
**Topics**: Class-based dependencies, type annotation shortcut, inheritance

**Key Examples**:
- Basic class dependency with helper methods
- Shortcut vs explicit `Depends()` syntax
- Class dependencies with processing logic
- Per-request state management
- Class inheritance for progressive complexity

**Run**:
```bash
uvicorn 02_class_dependencies:app --reload
```

**Test Endpoints**:
```bash
# Class dependency
curl "http://localhost:8000/items-class?q=phone&skip=10&limit=20"

# Search with processing
curl "http://localhost:8000/search?q=FastAPI&category=books&sort=date"

# Inherited dependencies
curl "http://localhost:8000/simple-list?skip=5&limit=10"
curl "http://localhost:8000/filtered-search-list?q=test&category=books&skip=5&limit=10"
```

---

### 03_dependency_chains.py
**Topics**: Dependency chains, authentication, permission checking, result caching

**Key Examples**:
- Linear dependency chains (token → verify → user)
- Complex auth chains with roles
- Dependency factories for permissions
- Multiple branches with shared dependencies
- Result caching demonstration

**Run**:
```bash
uvicorn 03_dependency_chains:app --reload
```

**Test Endpoints**:
```bash
# Basic authentication chain
curl -H "Authorization: Bearer secret123" http://localhost:8000/me

# Permission-based access
curl -H "Authorization: Bearer token123" http://localhost:8000/profile
curl -H "Authorization: Bearer token123" http://localhost:8000/admin/users

# Branching with caching (watch console for single DB connection)
curl http://localhost:8000/user-products

# Caching demonstration
curl http://localhost:8000/cached-example
```

---

### 04_path_operation_dependencies.py
**Topics**: Dependencies in path operation decorators, side effects

**Key Examples**:
- Path operation dependencies (validation only)
- Multiple pre-checks before handler execution
- Combining parameter and path dependencies
- Feature flag pattern
- Shared dependencies across endpoints

**Run**:
```bash
uvicorn 04_path_operation_dependencies:app --reload
```

**Test Endpoints**:
```bash
# Path operation dependencies
curl -H "X-Token: secret-token" -H "X-Key: secret-key" http://localhost:8000/items

# Multiple checks
curl -H "version: 1.0" http://localhost:8000/resource

# Feature flags
curl http://localhost:8000/new-endpoint      # Enabled
curl http://localhost:8000/beta-endpoint     # Disabled (403)
```

---

### 05_practical_patterns.py
**Topics**: Real-world patterns for production use

**Key Examples**:
- Database session management with cleanup
- Authentication and authorization
- Request context gathering
- Pagination helpers
- Combined patterns (auth + pagination + DB)
- Optional authentication

**Run**:
```bash
uvicorn 05_practical_patterns:app --reload
```

**Test Endpoints**:
```bash
# Database with cleanup (check console)
curl http://localhost:8000/users/1

# Authentication
curl -H "Authorization: Bearer user_token_123" http://localhost:8000/auth/me

# Role-based access
curl -H "Authorization: Bearer admin_token_456" http://localhost:8000/admin/dashboard

# Request context
curl -H "Accept-Language: fr,en" http://localhost:8000/context-demo

# Pagination
curl "http://localhost:8000/paginated-items?page=2&page_size=5"

# Combined pattern
curl -H "Authorization: Bearer user_token_123" \
     "http://localhost:8000/my-orders?page=1&page_size=10"

# Optional auth
curl http://localhost:8000/public-items  # Anonymous
curl -H "Authorization: Bearer user_token_123" http://localhost:8000/public-items  # Authenticated
```

---

### 06_advanced_patterns.py
**Topics**: Advanced patterns for complex applications

**Key Examples**:
- Yielding dependencies with setup/teardown
- Request timing and logging
- Nested/sub-dependencies
- Conditional dependencies
- Layered architecture (service → repository → database)
- Query filtering with validation

**Run**:
```bash
uvicorn 06_advanced_patterns:app --reload
```

**Test Endpoints**:
```bash
# Database with cleanup (watch console)
curl http://localhost:8000/db-query

# Timed endpoint (watch console for duration)
curl http://localhost:8000/timed-endpoint

# Nested dependencies
curl http://localhost:8000/external-call

# Caching (watch console - runs once)
curl http://localhost:8000/multi-service

# Ownership checking
curl "http://localhost:8000/items/1?user_id=100"  # Success
curl "http://localhost:8000/items/1?user_id=200"  # Forbidden

# Layered architecture
curl http://localhost:8000/users/1/profile

# Query filtering with validation
curl "http://localhost:8000/products?status=active&min_price=10&max_price=100"
curl "http://localhost:8000/products?status=invalid"  # Validation error
```

---

### 07_testing_dependencies.py
**Topics**: Testing with dependency overrides

**Key Examples**:
- Mocking database dependencies
- Mocking external APIs
- Testing with different user roles
- Using pytest fixtures
- Parametrized tests

**Run App**:
```bash
uvicorn 07_testing_dependencies:app --reload
```

**Run Tests**:
```bash
# Install pytest first
pip install pytest

# Run all tests
pytest 07_testing_dependencies.py -v

# Run specific test
pytest 07_testing_dependencies.py::test_user_endpoint_with_mock_db -v
```

---

## Learning Path

Recommended order for studying:

1. **01_basic_dependencies.py** - Understand core DI concepts
2. **02_class_dependencies.py** - Learn class-based patterns
3. **03_dependency_chains.py** - Master chains and auth flows
4. **04_path_operation_dependencies.py** - Understand path-level dependencies
5. **05_practical_patterns.py** - See production patterns
6. **06_advanced_patterns.py** - Explore advanced techniques
7. **07_testing_dependencies.py** - Learn testing strategies

## Key Concepts to Understand

1. **Dependency Injection Basics**
   - Functions receive dependencies, don't create them
   - FastAPI calls dependencies automatically
   - `Depends()` tells FastAPI what to inject

2. **Function vs Class Dependencies**
   - Functions: simple, direct
   - Classes: grouping, helper methods, state

3. **Dependency Chains**
   - Dependencies can depend on other dependencies
   - FastAPI resolves bottom-up
   - Results cached per request

4. **Path Operation Dependencies**
   - Side-effect only (validation, logging)
   - Don't inject values into handler
   - Run before handler execution

5. **Yielding Dependencies**
   - Code before `yield`: setup
   - Code after `yield`: cleanup
   - Cleanup always runs (even on errors)

6. **Testing**
   - `app.dependency_overrides` for testing
   - Replace real services with mocks
   - Use fixtures for clean test setup

## Common Patterns

### Authentication Chain
```python
get_token → verify_token → get_current_user
```

### Permission Checking
```python
get_current_user → check_permission → handler
```

### Database Session
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Pagination
```python
class Pagination:
    def __init__(self, page: int, page_size: int):
        self.skip = (page - 1) * page_size
        self.limit = page_size
```

## Tips

1. Keep dependencies single-responsibility
2. Use class dependencies when you need helper methods
3. Fail early with HTTPException in dependencies
4. Use path operation dependencies for cross-cutting concerns
5. Always clean up resources in yielding dependencies
6. Override dependencies in tests, never mock FastAPI itself
7. Dependencies are cached per request - don't worry about performance

## Additional Resources

- FastAPI Docs: https://fastapi.tiangolo.com/tutorial/dependencies/
- Your Day 4 Notes: Reference alongside these examples
- Type hints: Dependencies work best with proper type annotations
