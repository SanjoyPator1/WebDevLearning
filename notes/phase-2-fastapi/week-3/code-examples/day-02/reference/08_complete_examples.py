"""
Complete Practical Examples - Day 2
====================================

This file contains two comprehensive examples that combine ALL concepts
from Day 2:
1. E-commerce Product API
2. User Profile API

These are production-like examples showing how everything works together:
- Query parameters (filtering, pagination, sorting)
- Request bodies (Pydantic models)
- Path parameters (resource identification)
- Headers (authentication)
- Cookies (session management)
- Form data (traditional forms)
- File uploads (images, documents)

Run: uvicorn 08_complete_examples:app --reload
Test: http://localhost:8000/docs
"""

from fastapi import FastAPI, Query, File, UploadFile, Form, Header, Cookie, Response, HTTPException, Body
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
import secrets
import shutil
from pathlib import Path

app = FastAPI(
    title="Complete Day 2 Examples",
    description="Production-like examples combining all Day 2 concepts",
    version="1.0.0"
)

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Mock databases
products_db = {}
users_db = {}
sessions = {}
next_product_id = 1

# =============================================================================
# EXAMPLE 1: E-COMMERCE PRODUCT API
# =============================================================================
"""
This example demonstrates a realistic e-commerce product API with:
- Product listing with comprehensive filtering
- Product creation with authentication
- Image uploads
- Full CRUD operations
"""

# --- Pydantic Models ---

class Product(BaseModel):
    """Product model for request body"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    price: float = Field(..., gt=0)
    category: str
    stock: int = Field(..., ge=0)
    tags: List[str] = Field(default_factory=list)


class ProductInDB(BaseModel):
    """Product model with database fields"""
    id: int
    name: str
    description: str
    price: float
    category: str
    stock: int
    tags: List[str]
    created_at: str
    updated_at: str
    image_url: Optional[str] = None


# --- Product Endpoints ---

@app.get("/products", response_model=List[ProductInDB])
async def list_products(
    # Filtering
    category: str | None = Query(None, description="Filter by category"),
    min_price: float = Query(0, ge=0, description="Minimum price"),
    max_price: float = Query(10000, ge=0, description="Maximum price"),
    in_stock: bool = Query(True, description="Only show in-stock items"),
    search: str | None = Query(None, min_length=2, description="Search query"),
    tags: List[str] | None = Query(None, description="Filter by tags"),
    
    # Pagination
    skip: int = Query(0, ge=0, description="Skip N items"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    
    # Sorting
    sort_by: str = Query("name", regex="^(name|price|stock|created_at)$"),
    sort_order: str = Query("asc", regex="^(asc|desc)$")
):
    """
    List products with comprehensive filtering.
    
    Combines:
    - Query parameters (filters, pagination, sorting)
    - Response model (ProductInDB)
    
    Example:
    GET /products?category=electronics&min_price=100&max_price=1000
    &search=laptop&tags=gaming&tags=portable&skip=0&limit=20&sort_by=price&sort_order=desc
    """
    # Get all products
    all_products = list(products_db.values())
    
    # Apply filters
    filtered = all_products
    
    if category:
        filtered = [p for p in filtered if p["category"] == category]
    
    if search:
        filtered = [p for p in filtered
                   if search.lower() in p["name"].lower()
                   or search.lower() in p["description"].lower()]
    
    filtered = [p for p in filtered
               if min_price <= p["price"] <= max_price]
    
    if in_stock:
        filtered = [p for p in filtered if p["stock"] > 0]
    
    if tags:
        filtered = [p for p in filtered
                   if any(tag in p["tags"] for tag in tags)]
    
    # Sort
    reverse = (sort_order == "desc")
    filtered.sort(key=lambda x: x[sort_by], reverse=reverse)
    
    # Paginate
    total = len(filtered)
    products = filtered[skip:skip + limit]
    
    return products


@app.post("/products", response_model=ProductInDB)
async def create_product(
    product: Product,
    x_api_key: str = Header(..., description="API key for authentication")
):
    """
    Create a new product.
    
    Combines:
    - Request body (Pydantic model)
    - Header authentication (X-API-Key)
    - Response model
    
    Example:
    POST /products
    Headers: X-API-Key: secret-api-key-12345
    Body: {
        "name": "Gaming Laptop",
        "description": "High-performance laptop",
        "price": 1299.99,
        "category": "electronics",
        "stock": 50,
        "tags": ["gaming", "laptop", "portable"]
    }
    """
    global next_product_id
    
    # Validate API key (simplified)
    if x_api_key != "secret-api-key-12345":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Create product with database fields
    product_dict = product.model_dump()
    product_dict.update({
        "id": next_product_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "image_url": None
    })
    
    products_db[next_product_id] = product_dict
    next_product_id += 1
    
    return product_dict


@app.get("/products/{product_id}", response_model=ProductInDB)
async def get_product(
    product_id: int
):
    """
    Get a single product by ID.
    
    Combines:
    - Path parameter (product_id)
    - Response model
    """
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return products_db[product_id]


@app.post("/products/{product_id}/image")
async def upload_product_image(
    product_id: int,
    image: UploadFile = File(...),
    alt_text: str = Form(..., description="Image alt text"),
    is_primary: bool = Form(False, description="Set as primary image")
):
    """
    Upload product image with metadata.
    
    Combines:
    - Path parameter (product_id)
    - File upload (UploadFile)
    - Form data (metadata)
    
    Example:
    POST /products/1/image
    Form data:
    - image: [file]
    - alt_text: "Gaming laptop front view"
    - is_primary: true
    """
    # Check if product exists
    if product_id not in products_db:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Validate image type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if image.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only images allowed")
    
    # Read and validate size
    contents = await image.read()
    max_size = 5 * 1024 * 1024  # 5MB
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="Image too large (max 5MB)")
    
    # Save image
    import uuid
    extension = image.filename.split(".")[-1] if "." in image.filename else "jpg"
    unique_filename = f"product_{product_id}_{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    with file_path.open("wb") as buffer:
        buffer.write(contents)
    
    # Update product
    if is_primary:
        products_db[product_id]["image_url"] = f"/uploads/{unique_filename}"
    
    return {
        "message": "Image uploaded successfully",
        "product_id": product_id,
        "image": {
            "filename": unique_filename,
            "url": f"/uploads/{unique_filename}",
            "alt_text": alt_text,
            "is_primary": is_primary,
            "size": len(contents)
        }
    }


# =============================================================================
# EXAMPLE 2: USER PROFILE API
# =============================================================================
"""
This example demonstrates a user profile management system with:
- Authentication using cookies
- Profile creation and updates
- Avatar uploads
- Session management
"""

# --- Pydantic Models ---

class UserCreate(BaseModel):
    """User registration model"""
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str


class UserProfile(BaseModel):
    """User profile (no sensitive data)"""
    id: int
    username: str
    email: str
    full_name: str
    bio: str | None = None
    avatar_url: str | None = None
    created_at: str


# --- Authentication Endpoints ---

@app.post("/auth/register", response_model=UserProfile)
async def register(
    user: UserCreate
):
    """
    User registration.
    
    Combines:
    - Request body (Pydantic model)
    - Response model (excludes password)
    
    Example:
    POST /auth/register
    Body: {
        "username": "alice",
        "email": "alice@example.com",
        "password": "securepass123",
        "full_name": "Alice Smith"
    }
    """
    # Check if username exists
    for existing_user in users_db.values():
        if existing_user["username"] == user.username:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create user (in real app: hash password)
    user_id = len(users_db) + 1
    user_dict = {
        "id": user_id,
        "username": user.username,
        "email": user.email,
        "password": user.password,  # In real app: hash this!
        "full_name": user.full_name,
        "bio": None,
        "avatar_url": None,
        "created_at": datetime.now().isoformat()
    }
    
    users_db[user_id] = user_dict
    
    # Return profile (exclude password)
    return {
        "id": user_dict["id"],
        "username": user_dict["username"],
        "email": user_dict["email"],
        "full_name": user_dict["full_name"],
        "bio": user_dict["bio"],
        "avatar_url": user_dict["avatar_url"],
        "created_at": user_dict["created_at"]
    }


@app.post("/auth/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    """
    User login with session cookie.
    
    Combines:
    - Form data (traditional login form)
    - Cookie setting (session management)
    
    Example:
    POST /auth/login
    Form data:
    - username: alice
    - password: securepass123
    """
    # Find user
    user = None
    for u in users_db.values():
        if u["username"] == username:
            user = u
            break
    
    # Validate credentials
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "user_id": user["id"],
        "username": user["username"],
        "created_at": datetime.now().isoformat()
    }
    
    # Set cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,  # True in production
        samesite="lax",
        path="/",
        max_age=3600  # 1 hour
    )
    
    return {
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "username": user["username"]
        }
    }


@app.post("/auth/logout")
async def logout(
    response: Response,
    session_id: str = Cookie(...)
):
    """
    Logout and clear session.
    
    Combines:
    - Cookie reading (authentication)
    - Cookie deletion (logout)
    """
    # Delete session
    if session_id in sessions:
        del sessions[session_id]
    
    # Clear cookie
    response.set_cookie(
        key="session_id",
        value="",
        max_age=0,
        path="/"
    )
    
    return {"message": "Logged out successfully"}


# --- Profile Endpoints ---

@app.get("/profile", response_model=UserProfile)
async def get_profile(
    session_id: str = Cookie(...)
):
    """
    Get current user profile.
    
    Combines:
    - Cookie authentication (session_id)
    - Response model
    
    Example:
    GET /profile
    Cookie: session_id=abc123...
    """
    # Validate session
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = sessions[session_id]
    user = users_db[session["user_id"]]
    
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"],
        "bio": user["bio"],
        "avatar_url": user["avatar_url"],
        "created_at": user["created_at"]
    }


@app.post("/profile/update", response_model=UserProfile)
async def update_profile(
    full_name: str = Form(...),
    bio: str | None = Form(None),
    session_id: str = Cookie(...)
):
    """
    Update user profile.
    
    Combines:
    - Form data (profile updates)
    - Cookie authentication
    - Response model
    
    Example:
    POST /profile/update
    Cookie: session_id=abc123...
    Form data:
    - full_name: Alice Johnson
    - bio: Software engineer passionate about Python
    """
    # Validate session
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = sessions[session_id]
    user = users_db[session["user_id"]]
    
    # Update profile
    user["full_name"] = full_name
    user["bio"] = bio
    
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"],
        "bio": user["bio"],
        "avatar_url": user["avatar_url"],
        "created_at": user["created_at"]
    }


@app.post("/profile/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    session_id: str = Cookie(...)
):
    """
    Upload user avatar.
    
    Combines:
    - File upload
    - Cookie authentication
    - Image validation
    
    Example:
    POST /profile/avatar
    Cookie: session_id=abc123...
    Form data:
    - avatar: [image file]
    """
    # Validate session
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = sessions[session_id]
    user = users_db[session["user_id"]]
    
    # Validate image type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if avatar.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only images allowed")
    
    # Read and validate size
    contents = await avatar.read()
    max_size = 2 * 1024 * 1024  # 2MB for avatars
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="Avatar too large (max 2MB)")
    
    # Save avatar
    import uuid
    extension = avatar.filename.split(".")[-1] if "." in avatar.filename else "jpg"
    unique_filename = f"avatar_{user['id']}_{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    with file_path.open("wb") as buffer:
        buffer.write(contents)
    
    # Update user
    user["avatar_url"] = f"/uploads/{unique_filename}"
    
    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": user["avatar_url"]
    }


# =============================================================================
# SEED DATA
# =============================================================================

@app.post("/seed-data")
async def seed_data():
    """
    Seed the database with sample data for testing.
    
    Call this endpoint to populate products_db with sample products.
    """
    global next_product_id, products_db
    
    sample_products = [
        {
            "name": "Gaming Laptop",
            "description": "High-performance laptop with RTX 4080",
            "price": 1299.99,
            "category": "electronics",
            "stock": 15,
            "tags": ["gaming", "laptop", "portable"]
        },
        {
            "name": "Wireless Mouse",
            "description": "Ergonomic wireless mouse",
            "price": 29.99,
            "category": "accessories",
            "stock": 50,
            "tags": ["wireless", "mouse", "ergonomic"]
        },
        {
            "name": "Mechanical Keyboard",
            "description": "RGB mechanical keyboard with Cherry MX switches",
            "price": 149.99,
            "category": "accessories",
            "stock": 30,
            "tags": ["mechanical", "keyboard", "rgb"]
        }
    ]
    
    products_db.clear()
    next_product_id = 1
    
    for product_data in sample_products:
        product_dict = product_data.copy()
        product_dict.update({
            "id": next_product_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "image_url": None
        })
        products_db[next_product_id] = product_dict
        next_product_id += 1
    
    return {
        "message": "Sample data created",
        "products_count": len(products_db)
    }


# =============================================================================
# TESTING NOTES
# =============================================================================
"""
Testing the Complete Examples:

1. E-commerce Product API Flow:
   a. Seed data: POST /seed-data
   b. List products: GET /products?category=electronics
   c. Create product: POST /products (with X-API-Key header)
   d. Upload image: POST /products/1/image (with file)
   
2. User Profile API Flow:
   a. Register: POST /auth/register
   b. Login: POST /auth/login (sets cookie)
   c. Get profile: GET /profile (uses cookie)
   d. Update profile: POST /profile/update (uses cookie)
   e. Upload avatar: POST /profile/avatar (uses cookie)
   f. Logout: POST /auth/logout

Using FastAPI Docs (/docs):
- All endpoints are interactive
- Cookies are handled automatically
- File uploads work in the UI
- Response models are validated

Using curl:
# Product API
curl -X POST http://localhost:8000/seed-data

curl "http://localhost:8000/products?category=electronics&min_price=100"

curl -X POST http://localhost:8000/products \
  -H "X-API-Key: secret-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","description":"Test product","price":99.99,"category":"test","stock":10,"tags":[]}'

# User Profile API
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"securepass123","full_name":"Alice Smith"}'

curl -c cookies.txt -X POST http://localhost:8000/auth/login \
  -d "username=alice&password=securepass123"

curl -b cookies.txt http://localhost:8000/profile

These examples demonstrate ALL Day 2 concepts in realistic scenarios.
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
