# Week 3: FastAPI Deep Dive - Basics

**Duration**: 7 days  
**Phase**: 2 - FastAPI Deep Dive  
**Focus**: Building REST APIs with FastAPI

---

## Daily Breakdown

### Day 1: Introduction to FastAPI
- **File**: `day-1-fastapi-intro.md`
- **Topics**: What is FastAPI, installation, first app, path operations
- **Exercises**: `exercises/02-fastapi/01-basics/` (Ex 1-2)

### Day 2: Request Handling
- **File**: `day-2-request-handling.md`
- **Topics**: Query parameters, request body, Pydantic models

### Day 3: Data Validation
- **File**: `day-3-data-validation.md`
- **Topics**: Field validation, custom validators, error handling
- **Exercises**: `exercises/02-fastapi/01-basics/` (Ex 3-6)

### Day 4: Advanced Parameters
- **File**: `day-4-advanced-parameters.md`
- **Topics**: Headers, cookies, form data, file uploads

### Day 5: Response Handling
- **File**: `day-5-response-handling.md`
- **Topics**: Response models, status codes, custom responses
- **Exercises**: `exercises/02-fastapi/01-basics/` (Ex 7-10)

### Day 6: Dependencies Basics
- **File**: `day-6-dependencies.md`
- **Topics**: Dependency injection, function/class dependencies

### Day 7: Mini Project
- **File**: `day-7-mini-project.md`
- **Topics**: Build complete Blog API
- **Exercises**: `exercises/02-fastapi/01-basics/` (Ex 11-12)

---

## Prerequisites

Before starting Week 3, ensure you've completed:
- ✅ Week 1: Decorators, Context Managers, Generators
- ✅ Week 2: Async/Await, Type Hints, Pydantic

---

## Installation

```bash
# Create/activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install FastAPI and Uvicorn
pip install fastapi
pip install "uvicorn[standard]"

# Or install everything
pip install "fastapi[all]"
```

---

## How to Use This Week's Materials

### 1. Read Daily Notes

```bash
cat day-1-fastapi-intro.md
# or open in your editor
code day-1-fastapi-intro.md
```

### 2. Create Your First API

```python
# main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

### 3. Run the Server

```bash
uvicorn main:app --reload
```

### 4. Test Your API

- Browser: http://127.0.0.1:8000
- Interactive Docs: http://127.0.0.1:8000/docs
- Alternative Docs: http://127.0.0.1:8000/redoc

### 5. Complete Exercises

```bash
cd exercises/02-fastapi/01-basics/
# Read EXERCISES.md
# Work on exercise_1.py
uvicorn exercise_1:app --reload
```

---

## Week 3 Goals

By the end of this week, you should be able to:
- [ ] Create FastAPI applications
- [ ] Define path operations (GET, POST, PUT, DELETE)
- [ ] Handle path and query parameters
- [ ] Use Pydantic models for validation
- [ ] Implement error handling
- [ ] Work with request/response models
- [ ] Use dependency injection
- [ ] Build a complete CRUD API

---

## Key Concepts

### FastAPI Basics
- **Path Operations**: HTTP methods (GET, POST, PUT, DELETE)
- **Path Parameters**: Variables in URL (`/items/{item_id}`)
- **Query Parameters**: Key-value pairs (`?skip=0&limit=10`)
- **Request Body**: JSON data with Pydantic models
- **Automatic Docs**: Swagger UI and ReDoc

### Pydantic Models
- **Data Validation**: Automatic type checking
- **Field Constraints**: min, max, regex patterns
- **Custom Validators**: Complex validation logic
- **Response Models**: Control API output

### Dependencies
- **Reusable Logic**: Share code across endpoints
- **Dependency Injection**: Automatic parameter resolution
- **Authentication**: Token verification
- **Database Connections**: Resource management

---

## Project Structure

```
week-3-fastapi/
├── main.py              # Main FastAPI application
├── models.py            # Pydantic models
├── dependencies.py      # Dependency functions
├── routers/             # API routers (later)
│   ├── items.py
│   └── users.py
└── requirements.txt
```

---

## Common Patterns

### Basic CRUD

```python
# In-memory storage
items = {}

@app.post("/items")
async def create_item(item: Item):
    item_id = len(items) + 1
    items[item_id] = item
    return {"id": item_id, **item.model_dump()}

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    items[item_id] = item
    return item

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    del items[item_id]
    return {"message": "Item deleted"}
```

### Pagination

```python
@app.get("/items")
async def list_items(skip: int = 0, limit: int = 10):
    return items_list[skip : skip + limit]
```

### Search

```python
@app.get("/search")
async def search_items(q: str | None = None):
    if not q:
        return items_list
    return [item for item in items_list if q.lower() in item["name"].lower()]
```

---

## Testing Your APIs

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
  -d '{"name":"Updated Item","price":15.0}'

# DELETE
curl -X DELETE http://127.0.0.1:8000/items/1
```

### Using Python requests

```python
import requests

BASE_URL = "http://127.0.0.1:8000"

# GET
response = requests.get(f"{BASE_URL}/items")
print(response.json())

# POST
response = requests.post(
    f"{BASE_URL}/items",
    json={"name": "New Item", "price": 10.5}
)
print(response.json())

# PUT
response = requests.put(
    f"{BASE_URL}/items/1",
    json={"name": "Updated", "price": 20.0}
)
print(response.json())

# DELETE
response = requests.delete(f"{BASE_URL}/items/1")
print(response.json())
```

### Using Interactive Docs

1. Start your server: `uvicorn main:app --reload`
2. Go to: http://127.0.0.1:8000/docs
3. Try out all endpoints interactively!

---

## Common Pitfalls

### 1. Wrong Path Order

```python
# WRONG - specific route after generic
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    pass

@app.get("/users/me")  # Will never match!
async def get_current_user():
    pass

# CORRECT - specific routes first
@app.get("/users/me")
async def get_current_user():
    pass

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    pass
```

### 2. Missing Type Hints

```python
# BAD - no type hints, no validation
@app.get("/items/{item_id}")
async def get_item(item_id):
    return {"item_id": item_id}

# GOOD - type hints enable validation
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"item_id": item_id}
```

### 3. Not Using Pydantic Models

```python
# BAD - manual validation needed
@app.post("/items")
async def create_item(name: str, price: float):
    if price < 0:
        raise HTTPException(400, "Price must be positive")
    return {"name": name, "price": price}

# GOOD - automatic validation
class Item(BaseModel):
    name: str
    price: float = Field(gt=0)

@app.post("/items")
async def create_item(item: Item):
    return item
```

### 4. Not Handling Errors

```python
# BAD - no error handling
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return items[item_id]  # KeyError if not exists!

# GOOD - proper error handling
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]
```

---

## Troubleshooting

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`  
**Solution**: `pip install fastapi uvicorn`

**Problem**: Port already in use  
**Solution**: Use different port: `uvicorn main:app --port 8001`

**Problem**: Changes not reflecting  
**Solution**: Use `--reload` flag: `uvicorn main:app --reload`

**Problem**: Validation not working  
**Solution**: Add type hints to parameters

**Problem**: Can't access from other devices  
**Solution**: Use `--host 0.0.0.0`: `uvicorn main:app --host 0.0.0.0`

---

## Next Week Preview

**Week 4**: Advanced FastAPI - Routers, middleware, background tasks, WebSockets

---

## Resources

### Official Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Uvicorn Documentation](https://www.uvicorn.org/)

### Tutorials
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [Full Stack FastAPI Template](https://github.com/tiangolo/full-stack-fastapi-template)

### Tools
- [Postman](https://www.postman.com/) - API testing
- [HTTPie](https://httpie.io/) - Modern curl alternative
- [Swagger Editor](https://editor.swagger.io/) - OpenAPI editor

---

**Happy coding!** Remember: FastAPI's automatic documentation at `/docs` is your best friend. Use it to test your APIs! 🚀
