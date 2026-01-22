# FastAPI Day 2: Request Handling & Data Input - Code Examples

Complete practical code examples for Day 2 of FastAPI learning path.

## 📁 File Structure

```
day-02-code/
├── README.md                       # This file
├── requirements.txt                # Python dependencies
├── 01_query_parameters.py          # Query parameters (all concepts)
├── 02_request_body.py              # Request body with Pydantic
├── 03_combining_parameters.py      # Combining parameter types
├── 04_headers.py                   # HTTP headers
├── 05_cookies.py                   # Cookies (complete guide)
├── 06_form_data.py                 # Form data handling
├── 07_file_uploads.py              # File uploads
├── 08_complete_examples.py         # Comprehensive examples
└── clients/                        # HTML test clients
    └── test_cookies.html           # Cookie testing interface
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Any Example

Each file is a complete FastAPI application. Run them individually:

```bash
# Query parameters
uvicorn 01_query_parameters:app --reload

# Request body
uvicorn 02_request_body:app --reload

# Cookies (with built-in HTML test client)
uvicorn 05_cookies:app --reload

# Complete examples
uvicorn 08_complete_examples:app --reload
```

### 3. Test the APIs

**Option 1: Interactive Docs (Recommended)**
- Open browser: `http://localhost:8000/docs`
- All endpoints are interactive
- Try out requests directly in the browser

**Option 2: HTML Test Clients**
- For cookies: Open `clients/test_cookies.html` in browser
- Built-in interfaces in some examples (visit root URL)

**Option 3: curl**
```bash
# Query parameters
curl "http://localhost:8000/items/basic?skip=5&limit=10"

# Request body
curl -X POST http://localhost:8000/products/basic \
  -H "Content-Type: application/json" \
  -d '{"name":"Laptop","price":999.99}'

# File upload
curl -X POST http://localhost:8000/upload/single \
  -F "file=@yourfile.txt"
```

## 📚 File Descriptions

### `01_query_parameters.py`
**Topics:**
- Basic query parameters with defaults
- Optional vs required parameters
- Validation with `Query()`
- Query parameter lists
- Advanced filtering and pagination
- Documentation examples

**Key Concepts:**
- Type conversion and validation
- Default values
- Constraints (min/max length, ranges)
- Multiple values for same parameter

**Example endpoints:**
- `GET /items/basic?skip=0&limit=10`
- `GET /products?category=electronics&min_price=100`
- `GET /items/validated?q=laptop&skip=10&limit=20`

---

### `02_request_body.py`
**Topics:**
- Why Pydantic? (comparison with manual validation)
- Basic Pydantic models
- Field validation with `Field()`
- Nested Pydantic models
- Model inheritance
- Model configuration
- Working with model data

**Key Concepts:**
- Automatic type validation
- Field constraints
- Nested models
- Model methods (model_dump, model_copy)
- Response models

**Example endpoints:**
- `POST /products/basic` - Basic product creation
- `POST /products/validated` - With validation
- `POST /products/detailed` - Nested models

---

### `03_combining_parameters.py`
**Topics:**
- How FastAPI decides parameter sources
- Path + Query + Body combinations
- Multiple body parameters
- Singular values in request body
- Complex endpoint patterns

**Key Concepts:**
- Parameter routing rules
- `Body()` for scalar values
- `embed=True` behavior
- Mental model for parameter types

**Example endpoints:**
- `PUT /items/{item_id}?q=search` with body
- `POST /items/assign` - Multiple body models
- `POST /items/calculate` - Multiple scalars in body

---

### `04_headers.py`
**Topics:**
- Reading request headers
- Header name conversion (snake_case ↔ kebab-case)
- Required vs optional headers
- Header validation
- Custom header names with alias
- Duplicate/list headers

**Key Concepts:**
- Automatic name conversion
- Authentication patterns
- API versioning via headers
- Content negotiation

**Example endpoints:**
- `GET /headers/basic` - Read User-Agent
- `GET /protected` - Required Authorization header
- `GET /api/resource` - API key authentication

---

### `05_cookies.py`
**Topics:**
- What cookies are and how they work
- Reading cookies from requests
- Setting cookies in responses
- Cookie attributes (HttpOnly, Secure, SameSite, etc.)
- Cookie scope (Domain and Path) - CRITICAL
- Local development vs production
- Real-world authentication patterns

**Key Concepts:**
- Cookie scope rules (most common bug!)
- Security flags
- Session management
- Login/logout flows

**Built-in HTML test client:** Visit `http://localhost:8000/`

**Example endpoints:**
- `POST /login` - Sets session cookie
- `GET /dashboard` - Requires session cookie
- `POST /logout` - Clears cookie

---

### `06_form_data.py`
**Topics:**
- What form data is (backend perspective)
- Basic form handling with `Form()`
- Form validation
- Optional form fields
- Form data vs JSON comparison
- When to use forms

**Key Concepts:**
- Form encoding types
- Boolean conversion
- Multiple form fields
- Real-world form examples

**Built-in HTML test client:** Visit `http://localhost:8000/`

**Example endpoints:**
- `POST /login` - Login form
- `POST /users/register` - Registration with validation
- `POST /contact/advanced` - Contact form

---

### `07_file_uploads.py`
**Topics:**
- How file uploads work (backend view)
- Single file upload
- `File` vs `UploadFile` comparison
- Multiple file uploads
- File + metadata (form fields)
- File type validation
- File size validation
- Saving files to disk

**Key Concepts:**
- Always use `UploadFile` (not bytes)
- File validation (type, size)
- Security considerations
- Streaming large files

**Built-in HTML test client:** Visit `http://localhost:8000/`

**Example endpoints:**
- `POST /upload/single` - Single file
- `POST /upload/multiple` - Multiple files
- `POST /upload/with-metadata` - File + form data

---

### `08_complete_examples.py`
**Topics:**
- E-commerce Product API (complete)
- User Profile API (complete)
- All Day 2 concepts combined

**Key Concepts:**
- Production-like patterns
- All parameter types together
- Authentication flows
- Image uploads
- CRUD operations

**Example endpoints:**
- `GET /products?category=electronics&min_price=100`
- `POST /products` with API key header
- `POST /auth/login` with cookies
- `POST /profile/avatar` with file upload

---

## 🎯 Learning Path

### Beginner (Start Here)
1. `01_query_parameters.py` - Understand URL parameters
2. `02_request_body.py` - Learn Pydantic models
3. `03_combining_parameters.py` - See how they work together

### Intermediate
4. `04_headers.py` - HTTP headers for metadata
5. `06_form_data.py` - Traditional form handling
6. `07_file_uploads.py` - File handling

### Advanced
7. `05_cookies.py` - Authentication with cookies (read carefully!)
8. `08_complete_examples.py` - Real-world patterns

## 🐛 Common Pitfalls

### Cookies
- ⚠️ **Path mismatch** - Cookie exists but isn't sent
  - Fix: Always use `path="/"` unless you have a strong reason
- ⚠️ **Secure flag in dev** - Cookie not sent over HTTP
  - Fix: Use `secure=False` in development
- ⚠️ **Frontend not sending cookies** - Missing credentials
  - Fix: Use `credentials: 'include'` in fetch

### File Uploads
- ⚠️ **Using `bytes` instead of `UploadFile`** - Memory issues
  - Fix: Always use `UploadFile`
- ⚠️ **Missing python-multipart** - Forms/uploads fail
  - Fix: `pip install python-multipart`
- ⚠️ **Trusting client filenames** - Security risk
  - Fix: Generate server-side filenames (UUID)

### Parameters
- ⚠️ **Forgetting `Form()` or `Body()`** - Becomes query param
  - Fix: Explicitly wrap with `Form()` or `Body()`
- ⚠️ **Path param not in route** - Treated as query param
  - Fix: Include in route: `/items/{item_id}`

## 💡 Tips

### Testing
1. Use `/docs` for interactive testing
2. Use DevTools Network tab to see actual requests
3. Use DevTools Application tab to see cookies
4. Check request/response headers

### Development
1. Read file comments - they explain "why", not just "what"
2. Run one file at a time
3. Experiment with validation - break things to learn
4. Compare with your notes

### Production
1. Never trust client input - validate everything
2. Use HTTPS in production (Secure cookies)
3. Set upload limits at reverse proxy
4. Generate server-side filenames
5. Scan uploads for malware

## 🔧 Debugging

### Cookies Not Working?
```python
# Check these in order:
1. Is path="/"? (most common issue)
2. Is domain correct?
3. Is secure=False in dev?
4. Is SameSite compatible?
5. Is frontend sending credentials?
6. Check DevTools → Application → Cookies
```

### Validation Errors?
- Check FastAPI docs response - it tells you exactly what's wrong
- Look at "loc" field - shows which parameter failed
- Look at "msg" field - shows why it failed

### File Upload Failing?
```bash
# Did you install python-multipart?
pip install python-multipart

# Are you using UploadFile?
file: UploadFile = File(...)  # ✓ Correct
file: bytes = File(...)        # ✗ Wrong
```

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [HTTP Cookies (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
- [Multipart Form Data](https://developer.mozilla.org/en-US/docs/Web/API/FormData)

## 🤝 Contributing

Found an issue or have a suggestion? These examples are meant to be learning tools. Feel free to modify and experiment!

## 📝 License

These examples are for educational purposes.

---

**Happy Learning! 🚀**

Remember: The best way to learn is to run the code, break it, fix it, and understand why it works.
