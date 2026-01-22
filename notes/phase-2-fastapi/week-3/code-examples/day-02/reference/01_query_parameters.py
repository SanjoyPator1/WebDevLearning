"""
Query Parameters - Complete Guide
==================================

Topics covered:
1. Basic query parameters with defaults
2. Optional vs required parameters
3. Multiple parameters with different types
4. Validation with Query()
5. Query parameter lists
6. Advanced filtering and pagination
7. Documentation examples

Run: uvicorn 01_query_parameters:app --reload
Test: http://localhost:8000/docs
"""

from fastapi import FastAPI, Query
from typing import List, Optional

app = FastAPI(
    title="Query Parameters Guide",
    description="Complete guide to handling query parameters in FastAPI",
    version="1.0.0"
)

# =============================================================================
# 1. BASIC QUERY PARAMETERS
# =============================================================================

@app.get("/items/basic")
async def basic_query_params(skip: int = 0, limit: int = 10):
    """
    Basic query parameters with default values.
    
    How it works:
    - FastAPI sees function parameters without special decorators
    - These aren't path parameters (not in URL path)
    - Therefore, treated as query parameters
    - Type hints provide automatic validation and conversion
    
    URL examples:
    - /items/basic → skip=0, limit=10 (uses defaults)
    - /items/basic?skip=5 → skip=5, limit=10
    - /items/basic?limit=20 → skip=0, limit=20
    - /items/basic?skip=10&limit=50 → skip=10, limit=50
    """
    return {
        "skip": skip,
        "limit": limit,
        "message": f"Showing items {skip} to {skip + limit}"
    }


@app.get("/products")
async def get_products(
    category: str,
    min_price: float = 0,
    max_price: float = 1000,
    in_stock: bool = True,
    sort_by: str = "name"
):
    """
    Multiple query parameters with different types.
    
    Type conversion happens automatically:
    - category → str (no conversion needed)
    - min_price → float (converted from string)
    - max_price → float (converted from string)
    - in_stock → bool (converted from string)
    - sort_by → str (no conversion needed)
    
    Boolean conversion:
    - "true", "True", "1", "yes", "on" → True
    - "false", "False", "0", "no", "off" → False
    
    URL example:
    /products?category=electronics&min_price=100&max_price=500&in_stock=true&sort_by=price
    """
    # Simulate filtering logic
    products = [
        {
            "id": 1,
            "name": "Laptop",
            "category": category,
            "price": 800,
            "in_stock": True
        }
    ]
    
    return {
        "category": category,
        "price_range": {"min": min_price, "max": max_price},
        "in_stock_only": in_stock,
        "sort_by": sort_by,
        "products": products,
        "count": len(products)
    }


# =============================================================================
# 2. OPTIONAL VS REQUIRED PARAMETERS
# =============================================================================

@app.get("/search/optional")
async def search_optional(q: Optional[str] = None):
    """
    Optional query parameter using Optional[str].
    
    Optional[str] means:
    - The parameter can be a string OR None
    - If not provided, defaults to None
    
    URL examples:
    - /search/optional → q=None (no query provided)
    - /search/optional?q=laptop → q="laptop"
    - /search/optional?q= → q="" (empty string)
    """
    if q:
        # Simulate database search
        results = [
            {"id": 1, "name": f"Product matching {q}"},
            {"id": 2, "name": f"Another {q} product"}
        ]
        return {
            "query": q,
            "results": results,
            "count": len(results)
        }
    
    return {
        "message": "No query provided",
        "hint": "Try /search/optional?q=laptop"
    }


# Python 3.10+ syntax (simpler than Optional)
@app.get("/search/modern")
async def search_modern(q: str | None = None):
    """
    Same as Optional[str] = None, but using Python 3.10+ syntax.
    
    str | None is equivalent to Optional[str]
    """
    if q:
        return {"query": q, "message": f"Searching for: {q}"}
    return {"message": "No query provided"}


@app.get("/users/search")
async def search_users(username: str):
    """
    Required query parameter (no default value).
    
    URL examples:
    - /users/search?username=alice → ✓ Works
    - /users/search → ✗ Returns 422 Validation Error
    
    FastAPI returns a validation error if the parameter is missing.
    """
    return {
        "username": username,
        "message": f"Searching for user: {username}"
    }


# =============================================================================
# 3. VALIDATION WITH Query()
# =============================================================================

@app.get("/items/validated")
async def validated_query_params(
    # String validation
    q: str = Query(
        None,  # Default value (None = optional)
        min_length=3,  # Minimum 3 characters
        max_length=50,  # Maximum 50 characters
        regex="^[a-zA-Z0-9_-]+$",  # Alphanumeric with _ and -
        description="Search query",
        example="laptop"
    ),
    
    # Numeric validation
    skip: int = Query(
        0,  # Default value
        ge=0,  # Greater than or equal to 0
        le=1000,  # Less than or equal to 1000
        description="Number of items to skip"
    ),
    
    limit: int = Query(
        10,  # Default value
        gt=0,  # Greater than 0 (must be positive)
        le=100,  # Less than or equal to 100
        description="Number of items to return"
    ),
    
    # String with description
    sort: str = Query(
        "created_at",
        description="Field to sort by",
        example="name"
    )
):
    """
    Advanced query parameter validation using Query().
    
    Query() Parameters:
    - default: Default value (or ... for required)
    - min_length, max_length: String length constraints
    - regex: Pattern matching for strings
    - gt, ge, lt, le: Numeric comparisons
    - description: Documentation string
    - example: Example value for docs
    - deprecated: Mark parameter as deprecated
    - alias: Alternative parameter name
    
    Validation rules:
    - q: 3-50 characters, alphanumeric with _ and -
    - skip: 0 to 1000
    - limit: 1 to 100 (must be positive)
    - sort: Any string, with description for docs
    
    URL examples:
    - /items/validated?q=laptop&skip=10&limit=20&sort=price → ✓
    - /items/validated?q=ab → ✗ (too short)
    - /items/validated?skip=-5 → ✗ (negative not allowed)
    - /items/validated?limit=0 → ✗ (must be > 0)
    """
    return {
        "q": q,
        "skip": skip,
        "limit": limit,
        "sort": sort
    }


@app.get("/users/search-explicit")
async def search_users_explicit(username: str = Query(...)):
    """
    Using Query(...) makes the requirement explicit.
    
    The ... (Ellipsis) means "required, no default"
    This is more explicit than just omitting the default value.
    """
    return {
        "username": username,
        "message": f"Searching for user: {username}"
    }


# =============================================================================
# 4. QUERY PARAMETER LISTS
# =============================================================================

@app.get("/items/filter")
async def filter_items(tags: List[str] = Query(None)):
    """
    Accept multiple values for the same parameter.
    
    URL examples:
    - /items/filter?tags=electronics&tags=sale&tags=new
      → tags = ["electronics", "sale", "new"]
    - /items/filter?tags=electronics
      → tags = ["electronics"]
    - /items/filter
      → tags = None
    """
    if tags:
        return {
            "tags": tags,
            "count": len(tags),
            "message": f"Filtering by tags: {', '.join(tags)}"
        }
    
    return {"message": "No tags provided"}


@app.get("/items/filter-validated")
async def filter_items_validated(
    tags: List[str] = Query(
        None,
        min_length=1,  # Each tag must be at least 1 char
        max_length=20,  # Each tag max 20 chars
        description="Filter by tags"
    )
):
    """
    Query parameter list with validation.
    
    Each item in the list is validated individually:
    - Each tag must be 1-20 characters
    - Empty tags will cause validation error
    """
    if tags:
        return {
            "tags": tags,
            "count": len(tags),
            "valid": all(1 <= len(tag) <= 20 for tag in tags)
        }
    
    return {"message": "No tags provided"}


# =============================================================================
# 5. ADVANCED FILTERING AND PAGINATION
# =============================================================================

@app.get("/products/advanced")
async def advanced_product_search(
    # Category filter (required)
    category: str = Query(..., description="Product category"),
    
    # Search query (optional)
    q: str | None = Query(None, min_length=3, max_length=50),
    
    # Price range
    min_price: float = Query(0, ge=0),
    max_price: float = Query(10000, ge=0),
    
    # Stock filter
    in_stock: bool = Query(True),
    
    # Pagination
    skip: int = Query(0, ge=0, description="Skip N items"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    
    # Sorting
    sort_by: str = Query(
        "created_at",
        regex="^(name|price|created_at)$",
        description="Sort field"
    ),
    sort_order: str = Query(
        "asc",
        regex="^(asc|desc)$",
        description="Sort order"
    ),
    
    # Tags (list)
    tags: List[str] = Query(None)
):
    """
    Comprehensive example combining all query parameter features.
    
    This demonstrates a real-world product search endpoint with:
    - Required parameters (category)
    - Optional search query
    - Price range filtering
    - Boolean filters
    - Pagination (skip/limit)
    - Sorting (field + order)
    - Tag filtering (list)
    
    Example URL:
    /products/advanced?category=electronics&q=laptop&min_price=500&max_price=2000
    &in_stock=true&skip=0&limit=20&sort_by=price&sort_order=desc
    &tags=gaming&tags=portable
    """
    # Simulate filtered results
    return {
        "filters": {
            "category": category,
            "query": q,
            "price_range": {"min": min_price, "max": max_price},
            "in_stock": in_stock,
            "tags": tags
        },
        "pagination": {
            "skip": skip,
            "limit": limit,
            "page": (skip // limit) + 1
        },
        "sorting": {
            "field": sort_by,
            "order": sort_order
        },
        "results": [
            {
                "id": 1,
                "name": "Gaming Laptop",
                "category": category,
                "price": 1200,
                "in_stock": True,
                "tags": ["gaming", "portable"]
            }
        ],
        "total": 1
    }


# =============================================================================
# 6. DOCUMENTATION EXAMPLES
# =============================================================================

@app.get("/search/documented")
async def documented_search(
    q: str = Query(
        ...,
        title="Query string",
        description="Search query for products",
        min_length=3,
        max_length=100,
        example="laptop gaming"
    ),
    price_min: float = Query(
        0,
        ge=0,
        description="Minimum price filter",
        example=100.0
    ),
    price_max: float = Query(
        10000,
        ge=0,
        description="Maximum price filter",
        example=2000.0
    )
):
    """
    Query parameters with comprehensive documentation.
    
    These examples appear in the interactive documentation (/docs).
    They help users understand how to use your API.
    
    The 'example' parameter in Query() shows up in the Swagger UI
    as example values users can try.
    """
    return {
        "query": q,
        "price_range": {"min": price_min, "max": price_max}
    }


# =============================================================================
# 7. COMMON PATTERNS
# =============================================================================

@app.get("/items/paginated")
async def paginated_items(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Pagination pattern using page numbers instead of skip/limit.
    
    This is more user-friendly for APIs consumed by humans.
    Internally, we convert to skip/limit for database queries.
    """
    skip = (page - 1) * page_size
    limit = page_size
    
    # Simulate database query
    total_items = 100
    total_pages = (total_items + page_size - 1) // page_size
    
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "skip": skip,
        "items": [{"id": i} for i in range(skip, min(skip + limit, total_items))]
    }


@app.get("/items/search")
async def search_with_filters(
    # Search term
    q: str | None = Query(None, min_length=2),
    
    # Multiple filter options
    category: str | None = None,
    brand: str | None = None,
    min_rating: float = Query(0, ge=0, le=5),
    
    # Pagination
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Real-world search pattern combining:
    - Optional search query
    - Multiple optional filters
    - Rating range
    - Pagination
    
    This is how most e-commerce search endpoints work.
    """
    filters_applied = []
    if q:
        filters_applied.append(f"search: {q}")
    if category:
        filters_applied.append(f"category: {category}")
    if brand:
        filters_applied.append(f"brand: {brand}")
    if min_rating > 0:
        filters_applied.append(f"rating >= {min_rating}")
    
    return {
        "query": q,
        "filters": {
            "category": category,
            "brand": brand,
            "min_rating": min_rating
        },
        "filters_applied": filters_applied,
        "pagination": {
            "page": page,
            "limit": limit
        },
        "results": []  # Would contain actual results from database
    }


# =============================================================================
# TESTING NOTES
# =============================================================================
"""
Testing Query Parameters:

1. Using Browser:
   Just navigate to the URLs with query strings:
   http://localhost:8000/items/basic?skip=5&limit=10

2. Using FastAPI Docs:
   Go to http://localhost:8000/docs
   - Try out each endpoint
   - See validation errors in real-time
   - View response schemas

3. Using curl:
   curl "http://localhost:8000/items/basic?skip=5&limit=10"

4. Using httpie:
   http GET localhost:8000/items/basic skip==5 limit==10

5. Using Python requests:
   import requests
   response = requests.get(
       "http://localhost:8000/items/basic",
       params={"skip": 5, "limit": 10}
   )

Common Validation Errors:
- Missing required parameter → 422 Unprocessable Entity
- Invalid type (string instead of int) → 422 with details
- Value out of range (skip=-5 with ge=0) → 422 with details
- String too short/long → 422 with details
- Regex pattern mismatch → 422 with details
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
