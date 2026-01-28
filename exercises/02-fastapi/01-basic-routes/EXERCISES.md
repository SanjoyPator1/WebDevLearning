# FastAPI Basics - Exercises

**Topic**: FastAPI Fundamentals (Week 3)  
**Difficulty**: Beginner to Intermediate  
**Total Exercises**: 12

---

## Exercise 1: Hello FastAPI

**Difficulty**: Easy  
**File**: `exercise_1.py`

Create a basic FastAPI application with multiple endpoints.

**Requirements**:
- Root endpoint `/` returning welcome message
- `/health` endpoint returning health status
- `/info` endpoint returning API information (name, version)
- Use proper async functions

**Expected**:
```python
# GET /
{"message": "Welcome to my API"}

# GET /health
{"status": "healthy", "timestamp": "2024-01-01T00:00:00"}

# GET /info
{"name": "My API", "version": "1.0.0"}
```

---

## Exercise 2: Path Parameters

**Difficulty**: Easy  
**File**: `exercise_2.py`

Create endpoints using path parameters.

**Requirements**:
- `/users/{user_id}` - Get user by ID
- `/posts/{post_id}` - Get post by ID  
- `/users/{user_id}/posts/{post_id}` - Get user's specific post
- Type hints for all parameters

**Test**:
```
GET /users/5 → {"user_id": 5, "name": "User 5"}
GET /posts/10 → {"post_id": 10, "title": "Post 10"}
GET /users/5/posts/10 → {"user_id": 5, "post_id": 10}
```

---

## Exercise 3: Query Parameters

**Difficulty**: Easy  
**File**: `exercise_3.py`

Implement search and filtering with query parameters.

**Requirements**:
- `/search?q=query` - Search endpoint
- `/items?skip=0&limit=10` - Pagination
- `/products?category=electronics&min_price=100&max_price=1000` - Filtering
- Handle optional parameters

**Test**:
```
GET /search?q=python
GET /items?skip=5&limit=20
GET /products?category=books&min_price=10
```

---

## Exercise 4: CRUD Operations

**Difficulty**: Medium  
**File**: `exercise_4.py`

Build a complete CRUD API for managing items.

**Requirements**:
- In-memory storage (list or dict)
- POST /items - Create item
- GET /items - List all items
- GET /items/{id} - Get single item
- PUT /items/{id} - Update item
- DELETE /items/{id} - Delete item
- Return appropriate responses

---

## Exercise 5: Request Body with Pydantic

**Difficulty**: Medium  
**File**: `exercise_5.py`

Create models and handle request bodies.

**Requirements**:
- Create `Product` model with name, price, description
- POST /products - Accept Product model
- Validate price > 0
- Optional description field
- Return created product with generated ID

**Product Model**:
```python
class Product(BaseModel):
    name: str
    price: float
    description: str | None = None
```

---

## Exercise 6: Data Validation

**Difficulty**: Medium  
**File**: `exercise_6.py`

Implement comprehensive validation.

**Requirements**:
- User registration endpoint
- Validate email format
- Validate password (min 8 chars, special char, number)
- Validate age (18-120)
- Return proper error messages

**User Model**:
```python
class User(BaseModel):
    username: str  # 3-20 chars, alphanumeric
    email: str     # valid email
    password: str  # strong password
    age: int       # 18-120
```

---

## Exercise 7: Response Models

**Difficulty**: Medium  
**File**: `exercise_7.py`

Use response models to control output.

**Requirements**:
- UserIn model with password
- UserOut model without password
- POST /register - Accept UserIn, return UserOut
- Exclude sensitive data from response

**Models**:
```python
class UserIn(BaseModel):
    username: str
    email: str
    password: str

class UserOut(BaseModel):
    username: str
    email: str
    id: int
```

---

## Exercise 8: Error Handling

**Difficulty**: Medium  
**File**: `exercise_8.py`

Implement proper error handling.

**Requirements**:
- GET /items/{id} - Return 404 if not found
- POST /items - Return 400 for invalid data
- Custom error messages
- Use HTTPException

**Example Errors**:
```python
# 404
{"detail": "Item with id 5 not found"}

# 400
{"detail": "Price must be greater than 0"}
```

---

## Exercise 9: File Upload

**Difficulty**: Medium  
**File**: `exercise_9.py`

Handle file uploads.

**Requirements**:
- POST /upload - Single file upload
- POST /upload-multiple - Multiple file upload
- Return file info (name, size, content type)
- Save files to disk (optional)

---

## Exercise 10: Headers and Cookies

**Difficulty**: Medium  
**File**: `exercise_10.py`

Work with headers and cookies.

**Requirements**:
- GET /protected - Require Authorization header
- POST /login - Set session cookie
- GET /profile - Read session cookie
- Return user info if authenticated

---

## Exercise 11: Dependencies

**Difficulty**: Medium-Hard  
**File**: `exercise_11.py`

Implement dependency injection.

**Requirements**:
- Create pagination dependency (skip, limit)
- Create authentication dependency (token verification)
- Use dependencies in multiple endpoints
- GET /items - Use pagination dependency
- GET /admin/users - Use auth dependency

---

## Exercise 12: Mini Project - Task Manager API

**Difficulty**: Hard  
**File**: `exercise_12.py`

Build a complete task management API.

**Requirements**:

**Models**:
- Task: id, title, description, completed, created_at
- User: id, username, email

**Endpoints**:
```
POST   /tasks                  - Create task
GET    /tasks                  - List tasks (with filters)
GET    /tasks/{id}             - Get task
PUT    /tasks/{id}             - Update task
DELETE /tasks/{id}             - Delete task
PATCH  /tasks/{id}/complete    - Mark as complete
GET    /tasks/stats            - Get statistics
```

**Features**:
- Query parameters for filtering (completed, search)
- Pagination (skip, limit)
- Input validation
- Error handling (404, 400)
- Response models
- Auto-generated ID
- Created timestamp

**Bonus**:
- Simple authentication
- User-specific tasks
- Due dates
- Priority levels

---

## Testing Your Solutions

### Using uvicorn

```bash
# Run your FastAPI app
uvicorn exercise_1:app --reload

# Test in browser
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

### Using curl

```bash
# GET
curl http://127.0.0.1:8000/items

# POST
curl -X POST http://127.0.0.1:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Item","price":10.5}'

# PUT
curl -X PUT http://127.0.0.1:8000/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated"}'

# DELETE
curl -X DELETE http://127.0.0.1:8000/items/1
```

### Using Python requests

```python
import requests

# GET
r = requests.get("http://127.0.0.1:8000/items")
print(r.json())

# POST
r = requests.post(
    "http://127.0.0.1:8000/items",
    json={"name": "Item", "price": 10.5}
)
print(r.json())
```

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)

---

## Tips

1. Always test in `/docs` - it's interactive!
2. Use type hints - they enable validation
3. Start uvicorn with `--reload` for auto-restart
4. Check the automatic docs at `/docs`
5. Use Pydantic models for request/response
6. Handle errors with HTTPException
7. Test edge cases (invalid IDs, missing data)

---

Good luck! 🚀
