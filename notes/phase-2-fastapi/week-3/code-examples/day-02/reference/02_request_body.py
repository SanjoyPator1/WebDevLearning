"""
Request Body with Pydantic - Complete Guide
===========================================

Topics covered:
1. Why Pydantic? (comparison with manual validation)
2. Basic Pydantic models
3. Field validation with Field()
4. Nested Pydantic models
5. Model inheritance
6. Model configuration
7. Working with model data

Run: uvicorn 02_request_body:app --reload
Test: http://localhost:8000/docs
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime

app = FastAPI(
    title="Request Body with Pydantic Guide",
    description="Complete guide to handling request bodies using Pydantic models",
    version="1.0.0"
)

# =============================================================================
# 1. WHY PYDANTIC? (Comparison)
# =============================================================================

@app.post("/items/manual")
async def create_item_manual(data: dict):
    """
    Manual validation - tedious and error-prone!
    
    Without Pydantic, you need to manually:
    - Check if fields exist
    - Validate types
    - Validate constraints
    - Handle errors
    - Convert types
    
    This is 50+ lines of boring, bug-prone code.
    """
    # Manual validation - avoid this!
    errors = []
    
    if "name" not in data:
        errors.append("name is required")
    elif not isinstance(data["name"], str):
        errors.append("name must be a string")
    elif len(data["name"]) < 1:
        errors.append("name cannot be empty")
    
    if "price" not in data:
        errors.append("price is required")
    elif not isinstance(data["price"], (int, float)):
        errors.append("price must be a number")
    elif data["price"] <= 0:
        errors.append("price must be positive")
    
    if errors:
        return {"errors": errors}
    
    return {"message": "Item created", "data": data}


# With Pydantic - automatic validation!
class Item(BaseModel):
    """
    Pydantic model for automatic validation.
    
    Everything is validated automatically:
    - Field presence
    - Type checking
    - Type conversion
    - Constraint validation
    """
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    description: str | None = None
    tax: float | None = None


@app.post("/items/pydantic")
async def create_item_pydantic(item: Item):
    """
    With Pydantic: automatic validation, no manual checks needed!
    
    The 'item' parameter is guaranteed to be valid.
    FastAPI validates everything before calling this function.
    
    Request body example:
    {
        "name": "Laptop",
        "description": "Gaming laptop",
        "price": 999.99,
        "tax": 79.99
    }
    """
    return {
        "message": "Item created successfully",
        "item": item
    }


# =============================================================================
# 2. BASIC PYDANTIC MODELS
# =============================================================================

class Product(BaseModel):
    """
    Basic Pydantic model with common field types.
    
    Field types:
    - str: String
    - int: Integer
    - float: Float/Decimal
    - bool: Boolean
    - str | None: Optional string (Python 3.10+)
    - Optional[str]: Optional string (older syntax)
    """
    name: str
    description: str | None = None  # Optional field with default None
    price: float
    tax: float | None = None
    is_available: bool = True  # Optional field with default True
    stock: int = 0  # Optional field with default 0


@app.post("/products/basic")
async def create_product(product: Product):
    """
    Basic product creation using Pydantic model.
    
    What FastAPI does:
    1. Validates JSON structure matches Product model
    2. Validates each field's type
    3. Converts types if needed (e.g., "123" → 123)
    4. Creates a Product instance
    5. Passes it to your function
    
    Request body example:
    {
        "name": "Laptop",
        "price": 999.99
    }
    """
    # Access model fields directly
    product_dict = product.model_dump()
    
    # Calculate price with tax if provided
    if product.tax:
        price_with_tax = product.price + product.tax
        product_dict["price_with_tax"] = price_with_tax
    
    return {
        "message": "Product created",
        "product": product_dict
    }


# =============================================================================
# 3. FIELD VALIDATION WITH Field()
# =============================================================================

class ValidatedProduct(BaseModel):
    """
    Pydantic model with comprehensive field validation.
    
    Field() parameters:
    - default / ...: Default value or required
    - min_length, max_length: String/list length
    - gt, ge, lt, le: Numeric comparisons
    - regex: Pattern matching
    - description: Documentation
    - example: Example value
    """
    name: str = Field(
        ...,  # Required (no default)
        min_length=1,  # At least 1 character
        max_length=100,  # At most 100 characters
        description="Product name",
        example="Gaming Laptop"
    )
    
    description: str | None = Field(
        None,  # Optional with default None
        max_length=500,
        description="Product description"
    )
    
    price: float = Field(
        ...,  # Required
        gt=0,  # Greater than 0 (must be positive)
        le=1000000,  # Less than or equal to 1 million
        description="Product price in USD",
        example=999.99
    )
    
    quantity: int = Field(
        default=1,  # Default value
        ge=1,  # Greater than or equal to 1
        le=10000,  # Less than or equal to 10000
        description="Available quantity"
    )
    
    sku: str = Field(
        ...,
        min_length=5,
        max_length=20,
        regex="^[A-Z0-9-]+$",  # Uppercase alphanumeric with hyphens
        description="Stock Keeping Unit",
        example="LAPTOP-001"
    )
    
    tags: List[str] = Field(
        default_factory=list,  # Empty list if not provided
        max_length=5,  # Max 5 tags
        description="Product tags"
    )


@app.post("/products/validated")
async def create_validated_product(product: ValidatedProduct):
    """
    Product creation with comprehensive validation.
    
    All validation happens automatically before this function is called.
    
    Valid request:
    {
        "name": "Gaming Laptop",
        "price": 999.99,
        "sku": "LAPTOP-001"
    }
    
    Invalid requests return 422 Unprocessable Entity with details:
    - name too short → error message
    - price negative → error message
    - quantity = 0 → error message
    - sku with lowercase → error message
    - More than 5 tags → error message
    """
    return {
        "message": "Product created successfully",
        "product": product
    }


# =============================================================================
# 4. NESTED PYDANTIC MODELS
# =============================================================================

class Image(BaseModel):
    """Model for product images"""
    url: str = Field(..., description="Image URL")
    alt_text: str = Field(..., description="Image alt text")
    is_primary: bool = Field(False, description="Is this the primary image?")


class Tag(BaseModel):
    """Model for product tags"""
    name: str = Field(..., min_length=1, max_length=20)
    color: str = Field(
        ...,
        regex="^#[0-9A-Fa-f]{6}$",  # Hex color code
        description="Tag color in hex format",
        example="#FF5733"
    )


class DetailedProduct(BaseModel):
    """Product with nested models for complex data structures"""
    name: str = Field(..., min_length=1)
    description: str | None = None
    price: float = Field(..., gt=0)
    
    # Nested single object
    primary_image: Image | None = None
    
    # Nested list of objects
    images: List[Image] = Field(default_factory=list)
    tags: List[Tag] = Field(default_factory=list)
    
    # Nested dictionary
    metadata: dict | None = None


@app.post("/products/detailed")
async def create_detailed_product(product: DetailedProduct):
    """
    Create product with nested models.
    
    Nested models allow complex data structures with validation
    at every level.
    
    Request body example:
    {
        "name": "Gaming Laptop",
        "price": 999.99,
        "primary_image": {
            "url": "http://example.com/laptop.jpg",
            "alt_text": "Gaming laptop front view",
            "is_primary": true
        },
        "images": [
            {
                "url": "http://example.com/laptop-side.jpg",
                "alt_text": "Side view",
                "is_primary": false
            }
        ],
        "tags": [
            {"name": "gaming", "color": "#FF0000"},
            {"name": "portable", "color": "#00FF00"}
        ],
        "metadata": {
            "brand": "TechCorp",
            "warranty_years": 2
        }
    }
    
    FastAPI validates:
    - Product structure
    - Each image structure
    - Each tag structure
    - All field constraints at every level
    """
    return {
        "message": "Product created",
        "product": product,
        "stats": {
            "image_count": len(product.images),
            "tag_count": len(product.tags),
            "has_primary_image": product.primary_image is not None
        }
    }


# =============================================================================
# 5. MODEL INHERITANCE
# =============================================================================

class ItemBase(BaseModel):
    """Base model with common fields"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    price: float = Field(..., gt=0)
    tax: float | None = None


class ItemCreate(ItemBase):
    """
    For creating items - inherits from ItemBase.
    
    Used for POST requests where we don't have ID yet.
    Can add creation-specific fields.
    """
    tags: List[str] = Field(default_factory=list)
    initial_stock: int = Field(default=0, ge=0)


class ItemUpdate(BaseModel):
    """
    For updating items - all fields optional.
    
    Used for PATCH requests where client can update
    only specific fields.
    """
    name: str | None = None
    description: str | None = None
    price: float | None = Field(None, gt=0)
    tax: float | None = None
    tags: List[str] | None = None


class ItemInDB(ItemBase):
    """
    For database representation - includes system fields.
    
    Used for responses and internal operations.
    Includes fields that only exist after database insert.
    """
    id: int
    created_at: str
    updated_at: str
    stock: int


# In-memory "database"
items_db = {}
next_id = 1


@app.post("/items/create", response_model=ItemInDB)
async def create_item_with_inheritance(item: ItemCreate):
    """
    Create item using inheritance pattern.
    
    Different models for different purposes:
    - ItemCreate: Input (no id, no timestamps)
    - ItemInDB: Output (includes id, timestamps)
    
    This is a common pattern in real applications:
    - Input models: What client sends
    - Output models: What API returns
    - DB models: What's stored in database
    
    Request body:
    {
        "name": "Laptop",
        "price": 999.99,
        "tags": ["electronics", "computers"],
        "initial_stock": 50
    }
    """
    global next_id
    
    # Simulate database insert
    item_in_db = ItemInDB(
        **item.model_dump(exclude={"initial_stock"}),  # Spread ItemCreate fields
        id=next_id,
        stock=item.initial_stock,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    
    items_db[next_id] = item_in_db
    next_id += 1
    
    return item_in_db


@app.patch("/items/{item_id}", response_model=ItemInDB)
async def update_item(item_id: int, item_update: ItemUpdate):
    """
    Update item using partial update model.
    
    ItemUpdate has all optional fields, so client can update
    only what they want to change.
    
    Request body (update only price and name):
    {
        "name": "Updated Laptop",
        "price": 1099.99
    }
    """
    if item_id not in items_db:
        return {"error": "Item not found"}
    
    existing_item = items_db[item_id]
    
    # Update only provided fields
    update_data = item_update.model_dump(exclude_unset=True)
    
    # Create updated item
    updated_item = existing_item.model_copy(update=update_data)
    updated_item.updated_at = datetime.now().isoformat()
    
    items_db[item_id] = updated_item
    
    return updated_item


# =============================================================================
# 6. MODEL CONFIGURATION
# =============================================================================

class ConfiguredItem(BaseModel):
    """
    Model with custom configuration using ConfigDict.
    
    Configuration options:
    - extra: How to handle extra fields ('forbid', 'allow', 'ignore')
    - validate_assignment: Validate when fields are modified
    - use_enum_values: Use enum values instead of enum instances
    - from_attributes: Populate from ORM objects (SQLAlchemy, etc.)
    """
    model_config = ConfigDict(
        # Ignore unknown fields instead of raising error
        extra='ignore',
        
        # Validate when fields are assigned (not just on creation)
        validate_assignment=True,
        
        # Allow population from ORM objects
        from_attributes=True,
        
        # Generate JSON schema with examples
        json_schema_extra={
            "examples": [
                {
                    "name": "Example Product",
                    "price": 29.99
                }
            ]
        }
    )
    
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)


@app.post("/items/configured")
async def create_configured_item(item: ConfiguredItem):
    """
    Create item with custom configuration.
    
    With extra='ignore', this request works even with unknown fields:
    {
        "name": "Laptop",
        "price": 999.99,
        "unknown_field": "This will be ignored, not an error"
    }
    
    Without extra='ignore', unknown fields would cause validation error.
    """
    return {
        "message": "Item created",
        "item": item
    }


# =============================================================================
# 7. WORKING WITH MODEL DATA
# =============================================================================

class DataWorkingItem(BaseModel):
    """Model to demonstrate data manipulation methods"""
    name: str
    description: str | None = None
    price: float
    tags: List[str] = Field(default_factory=list)
    metadata: dict | None = None


@app.post("/items/data-methods")
async def demonstrate_data_methods(item: DataWorkingItem):
    """
    Demonstrates various ways to work with Pydantic model data.
    
    Request body:
    {
        "name": "Laptop",
        "description": "Gaming laptop",
        "price": 999.99,
        "tags": ["gaming", "portable"],
        "metadata": {"brand": "TechCorp"}
    }
    """
    # 1. Access fields directly
    name = item.name
    price = item.price
    
    # 2. Convert to dictionary
    item_dict = item.model_dump()
    # Returns: {"name": "...", "price": ..., "description": ..., ...}
    
    # 3. Convert to dictionary excluding None values
    item_dict_no_none = item.model_dump(exclude_none=True)
    # Only includes fields that are not None
    
    # 4. Convert to dictionary excluding certain fields
    item_dict_partial = item.model_dump(exclude={"description", "metadata"})
    # Excludes specified fields
    
    # 5. Convert to dictionary including only certain fields
    item_dict_selected = item.model_dump(include={"name", "price"})
    # Only includes specified fields
    
    # 6. Convert to JSON string
    item_json = item.model_dump_json()
    # Returns JSON string
    
    # 7. Convert to JSON string with indentation
    item_json_pretty = item.model_dump_json(indent=2)
    
    # 8. Copy model with updates
    updated_item = item.model_copy(update={"price": 1099.99})
    
    return {
        "direct_access": {
            "name": name,
            "price": price
        },
        "as_dict": item_dict,
        "no_none": item_dict_no_none,
        "partial": item_dict_partial,
        "selected": item_dict_selected,
        "as_json": item_json,
        "updated_copy": updated_item
    }


# =============================================================================
# 8. REAL-WORLD USER MODEL
# =============================================================================

class UserCreate(BaseModel):
    """User registration model"""
    username: str = Field(..., min_length=3, max_length=20, regex="^[a-zA-Z0-9_]+$")
    email: EmailStr  # Requires: pip install pydantic[email]
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    age: int = Field(..., ge=18, le=120)


class UserResponse(BaseModel):
    """User response model (excludes password)"""
    id: int
    username: str
    email: str
    full_name: str
    age: int
    created_at: str


users_db = {}
user_next_id = 1


@app.post("/users/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    """
    User registration with proper input/output models.
    
    Security pattern:
    - UserCreate: Accepts password
    - UserResponse: Never includes password
    
    Request body:
    {
        "username": "alice",
        "email": "alice@example.com",
        "password": "securepassword123",
        "full_name": "Alice Smith",
        "age": 25
    }
    
    Response (password excluded):
    {
        "id": 1,
        "username": "alice",
        "email": "alice@example.com",
        "full_name": "Alice Smith",
        "age": 25,
        "created_at": "2025-01-16T10:30:00"
    }
    """
    global user_next_id
    
    # In real app: hash password, check if username exists, etc.
    
    user_response = UserResponse(
        id=user_next_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        age=user.age,
        created_at=datetime.now().isoformat()
    )
    
    users_db[user_next_id] = user_response
    user_next_id += 1
    
    return user_response


# =============================================================================
# TESTING NOTES
# =============================================================================
"""
Testing Request Bodies:

1. Using FastAPI Docs (Recommended):
   - Go to http://localhost:8000/docs
   - Click on any endpoint
   - Click "Try it out"
   - Fill in the JSON body
   - Click "Execute"
   - See validation errors in real-time

2. Using curl:
   curl -X POST http://localhost:8000/products/basic \
     -H "Content-Type: application/json" \
     -d '{"name": "Laptop", "price": 999.99}'

3. Using httpie:
   http POST localhost:8000/products/basic \
     name="Laptop" price:=999.99

4. Using Python requests:
   import requests
   response = requests.post(
       "http://localhost:8000/products/basic",
       json={"name": "Laptop", "price": 999.99}
   )

Common Validation Errors:
- Missing required field → 422 with field name
- Wrong type → 422 with expected type
- Constraint violation → 422 with constraint details
- Invalid nested structure → 422 with path to error

Pydantic Features Used:
- BaseModel: Base class for all models
- Field(): Advanced field validation
- model_dump(): Convert to dictionary
- model_dump_json(): Convert to JSON string
- model_copy(): Create a copy with updates
- ConfigDict: Model configuration
- Nested models: Complex data structures
- Inheritance: Reuse common fields
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
