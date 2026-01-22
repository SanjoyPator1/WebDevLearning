"""
Combining Multiple Parameter Types - Complete Guide
===================================================

Topics covered:
1. How FastAPI decides where parameters come from
2. Path + Query + Body combinations
3. Multiple body parameters
4. Singular values in request body
5. Complex endpoint patterns
6. Mental model for parameter routing

Run: uvicorn 03_combining_parameters:app --reload
Test: http://localhost:8000/docs
"""

from fastapi import FastAPI, Body, Query, Path
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(
    title="Combining Parameters Guide",
    description="Learn how FastAPI routes different parameter types",
    version="1.0.0"
)

# =============================================================================
# 0. PYDANTIC MODELS FOR EXAMPLES
# =============================================================================

class Item(BaseModel):
    """Item model for request bodies"""
    name: str = Field(..., min_length=1)
    description: str | None = None
    price: float = Field(..., gt=0)
    tax: float | None = None


class User(BaseModel):
    """User model for request bodies"""
    username: str = Field(..., min_length=3)
    email: str
    full_name: str | None = None


# =============================================================================
# 1. HOW FASTAPI DECIDES PARAMETER SOURCES
# =============================================================================
"""
FastAPI infers parameter sources FROM THE FUNCTION SIGNATURE, not decorators.

Decision rules (in order):

1. PATH PARAMETERS
   - Parameter name appears in the route path
   - Example: /items/{item_id} → item_id is path parameter

2. REQUEST BODY
   - Parameter type is a Pydantic model
   - Or explicitly wrapped with Body(...)
   
3. QUERY PARAMETERS
   - Scalar types (int, str, bool, float, etc.)
   - Have a default value (including None)
   - Not part of the path

These rules are DETERMINISTIC and CONSISTENT.
"""


@app.get("/demo/parameter-inference")
async def demonstrate_inference(
    path_param: str,  # Would be path param if in URL
    query_param: str = "default",  # Query param (has default)
    optional_query: str | None = None  # Query param (optional)
):
    """
    This demonstrates the inference rules, but won't work as-is
    because path_param isn't in the route path.
    
    See the examples below for working demonstrations.
    """
    return {
        "path_param": path_param,
        "query_param": query_param,
        "optional_query": optional_query
    }


# =============================================================================
# 2. PATH + QUERY + BODY COMBINATION
# =============================================================================

@app.put("/items/{item_id}")
async def update_item(
    item_id: int,          # Path parameter (in URL path)
    item: Item,            # Request body (Pydantic model)
    q: str | None = None   # Query parameter (scalar with default)
):
    """
    Combines three parameter types in one endpoint.
    
    URL: PUT /items/5?q=search_term
    
    Body:
    {
        "name": "Updated Item",
        "description": "New description",
        "price": 150.0
    }
    
    How FastAPI interprets this:
    - item_id: Appears in URL path → PATH parameter
    - item: Pydantic model → REQUEST BODY
    - q: Scalar type + default value → QUERY parameter
    
    This is the most common pattern in REST APIs.
    """
    return {
        "item_id": item_id,
        "query": q,
        "item": item,
        "message": f"Updated item {item_id}"
    }


@app.get("/users/{user_id}/items/{item_id}")
async def get_user_item(
    user_id: int,  # Path parameter
    item_id: int,  # Path parameter
    q: str | None = None,  # Query parameter
    detailed: bool = False  # Query parameter
):
    """
    Multiple path parameters + multiple query parameters.
    
    URL: GET /users/10/items/5?q=laptop&detailed=true
    
    Parameter breakdown:
    - user_id: Path parameter (in URL)
    - item_id: Path parameter (in URL)
    - q: Query parameter (scalar with default)
    - detailed: Query parameter (scalar with default)
    
    No request body because this is a GET request.
    """
    return {
        "user_id": user_id,
        "item_id": item_id,
        "query": q,
        "detailed": detailed,
        "message": f"Getting item {item_id} for user {user_id}"
    }


# =============================================================================
# 3. MULTIPLE BODY PARAMETERS
# =============================================================================

@app.post("/items/assign")
async def assign_item_to_user(
    item: Item,
    user: User
):
    """
    Multiple request body models in a single endpoint.
    
    FastAPI creates a JSON structure where each model
    becomes a named key.
    
    Request body:
    {
        "item": {
            "name": "Laptop",
            "price": 999.99
        },
        "user": {
            "username": "alice",
            "email": "alice@example.com"
        }
    }
    
    How FastAPI handles this:
    - Each Pydantic model becomes a named key in JSON
    - This avoids ambiguity
    - OpenAPI schema is generated correctly
    - Validation is applied independently to each model
    """
    return {
        "message": f"Assigned {item.name} to {user.username}",
        "item": item,
        "user": user
    }


@app.post("/items/with-importance")
async def create_item_with_importance(
    item: Item,
    importance: int = Body(...)  # Singular value in body
):
    """
    Combining Pydantic model with singular body value.
    
    Request body:
    {
        "item": {
            "name": "Laptop",
            "price": 999.99
        },
        "importance": 5
    }
    
    Note: importance is wrapped with Body(...) to force it
    into the request body instead of being a query parameter.
    """
    return {
        "item": item,
        "importance": importance,
        "message": f"Created {item.name} with importance {importance}"
    }


# =============================================================================
# 4. SINGULAR VALUES IN REQUEST BODY
# =============================================================================

@app.put("/items/{item_id}/priority")
async def set_item_priority(
    item_id: int,  # Path parameter
    priority: int = Body(...)  # Body parameter
):
    """
    Force scalar value into request body using Body(...).
    
    URL: PUT /items/5
    
    Body:
    {
        "priority": 5
    }
    
    Why Body(...) is required:
    - priority is a scalar type (int)
    - Without Body(...), FastAPI treats it as query parameter
    - Body(...) explicitly marks it as part of request body
    
    This is useful for simple updates that don't need a full model.
    """
    return {
        "item_id": item_id,
        "priority": priority,
        "message": f"Set priority of item {item_id} to {priority}"
    }


@app.post("/items/calculate")
async def calculate_item(
    quantity: int = Body(...),
    unit_price: float = Body(...),
    tax_rate: float = Body(0.1),
    discount: float = Body(0.0)
):
    """
    Multiple scalar values in request body.
    
    Request body:
    {
        "quantity": 10,
        "unit_price": 99.99,
        "tax_rate": 0.15,
        "discount": 0.05
    }
    
    Each Body(...) value becomes a JSON key.
    Defaults still work (tax_rate, discount).
    Full validation is applied.
    """
    subtotal = quantity * unit_price
    tax = subtotal * tax_rate
    discount_amount = subtotal * discount
    total = subtotal + tax - discount_amount
    
    return {
        "quantity": quantity,
        "unit_price": unit_price,
        "tax_rate": tax_rate,
        "discount": discount,
        "calculation": {
            "subtotal": subtotal,
            "tax": tax,
            "discount_amount": discount_amount,
            "total": total
        }
    }


# =============================================================================
# 5. COMPLEX ENDPOINT PATTERNS
# =============================================================================

@app.put("/users/{user_id}/items/{item_id}")
async def update_user_item_complex(
    user_id: int,          # Path parameter
    item_id: int,          # Path parameter
    item: Item,            # Request body
    q: str | None = None,  # Query parameter
    active: bool = True,   # Query parameter
    priority: int = Body(None)  # Additional body parameter
):
    """
    Complex endpoint combining all parameter types.
    
    URL: PUT /users/10/items/5?q=laptop&active=true
    
    Body:
    {
        "item": {
            "name": "Updated Laptop",
            "price": 1200.0
        },
        "priority": 3
    }
    
    Parameter breakdown:
    - user_id, item_id: Path parameters
    - item: Request body (Pydantic model)
    - priority: Request body (singular value with Body())
    - q, active: Query parameters
    
    FastAPI merges all of this into a single validated request.
    """
    return {
        "user_id": user_id,
        "item_id": item_id,
        "item": item,
        "priority": priority,
        "query": q,
        "active": active,
        "message": "Complex update completed"
    }


@app.post("/orders/create")
async def create_order(
    item: Item,
    user: User,
    quantity: int = Body(..., gt=0),
    express_shipping: bool = Body(False),
    gift_wrap: bool = Body(False),
    notes: str | None = Body(None)
):
    """
    Real-world order creation endpoint.
    
    Combines:
    - Two Pydantic models (item, user)
    - Multiple singular body values
    - Optional fields
    
    Request body:
    {
        "item": {
            "name": "Laptop",
            "price": 999.99
        },
        "user": {
            "username": "alice",
            "email": "alice@example.com"
        },
        "quantity": 2,
        "express_shipping": true,
        "gift_wrap": false,
        "notes": "Please deliver after 5 PM"
    }
    """
    total = item.price * quantity
    if express_shipping:
        total += 20.0  # Shipping fee
    if gift_wrap:
        total += 5.0   # Gift wrap fee
    
    return {
        "order": {
            "item": item,
            "user": user,
            "quantity": quantity,
            "express_shipping": express_shipping,
            "gift_wrap": gift_wrap,
            "notes": notes,
            "total": total
        },
        "message": "Order created successfully"
    }


# =============================================================================
# 6. EMBED SINGLE MODEL IN BODY
# =============================================================================

@app.post("/items/embed")
async def create_item_embedded(
    item: Item = Body(..., embed=True)
):
    """
    Force single Pydantic model to be embedded under a key.
    
    Without embed=True, body would be:
    {
        "name": "Laptop",
        "price": 999.99
    }
    
    With embed=True, body must be:
    {
        "item": {
            "name": "Laptop",
            "price": 999.99
        }
    }
    
    This is useful for consistency when you sometimes have
    multiple body parameters and sometimes have one.
    """
    return {
        "message": "Item created with embedding",
        "item": item
    }


# =============================================================================
# 7. DECISION FLOW EXAMPLES
# =============================================================================

@app.post("/demo/all-types")
async def demonstrate_all_types(
    # Path parameters (must be in route)
    # user_id: int,  # Commented because not in route path
    
    # Query parameters (scalars with defaults)
    skip: int = 0,
    limit: int = 10,
    q: str | None = None,
    
    # Body parameters (models and Body() wrapped values)
    item: Item = Body(...),
    importance: int = Body(...),
    tags: list[str] = Body(default_factory=list)
):
    """
    Demonstrates how FastAPI categorizes parameters.
    
    Decision process for each parameter:
    
    1. Is it in the URL path?
       → Path parameter
       
    2. Is it a Pydantic model or wrapped in Body()?
       → Request body
       
    3. Is it a scalar with a default value?
       → Query parameter
    
    This mental model scales from simple to complex APIs.
    """
    return {
        "query_params": {
            "skip": skip,
            "limit": limit,
            "q": q
        },
        "body_params": {
            "item": item,
            "importance": importance,
            "tags": tags
        }
    }


# =============================================================================
# PRACTICAL GUIDELINES
# =============================================================================
"""
When to use each parameter type:

PATH PARAMETERS:
- Identify specific resources
- Example: /users/{user_id}/posts/{post_id}
- Always required
- Part of the resource URL

QUERY PARAMETERS:
- Filtering (category, price_range)
- Sorting (sort_by, order)
- Pagination (skip, limit)
- Optional flags (active, detailed)
- Search terms (q, search)

REQUEST BODY:
- Creating resources (POST)
- Updating resources (PUT/PATCH)
- Complex data structures
- Multiple related values
- Large amounts of data

COMBINING THEM:
- Use path params to identify resources
- Use query params for options/filters
- Use request body for resource data
- Example: PUT /users/{user_id}?notify=true with user data in body

MENTAL MODEL:
Think in this order:
1. Is it in the URL path? → Path parameter
2. Is it a Pydantic model or Body()? → Request body
3. Is it a scalar with default? → Query parameter

Let FastAPI infer whenever possible.
Override only when needed.
"""


# =============================================================================
# TESTING NOTES
# =============================================================================
"""
Testing Combined Parameters:

1. Using FastAPI Docs:
   http://localhost:8000/docs
   - Path parameters show in the URL
   - Query parameters show as form fields
   - Body parameters show as JSON editor
   - Try different combinations

2. Using curl:
   # Path + Query + Body
   curl -X PUT "http://localhost:8000/items/5?q=search" \
     -H "Content-Type: application/json" \
     -d '{"name": "Laptop", "price": 999.99}'

3. Using httpie:
   # Path + Query + Body
   http PUT localhost:8000/items/5 q==search \
     name="Laptop" price:=999.99

4. Using Python requests:
   response = requests.put(
       "http://localhost:8000/items/5",
       params={"q": "search"},
       json={"name": "Laptop", "price": 999.99}
   )

Common Mistakes:
- Forgetting to use Body() for scalars → becomes query param
- Not understanding embed=True behavior
- Mixing path param names with route path
- Trying to use GET with request body (not standard)

Best Practices:
- Keep path params for resource identification
- Use query params for filtering/options
- Use request body for resource data
- Document your parameter choices
- Be consistent across your API
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
