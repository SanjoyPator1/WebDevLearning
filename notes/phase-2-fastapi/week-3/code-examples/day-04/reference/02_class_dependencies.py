"""
02_class_dependencies.py

Topics covered:
- Basic class dependencies
- Type annotation shortcut
- Class dependencies with processing logic
- Class dependencies with state
- Inheriting class dependencies

Run: uvicorn 02_class_dependencies:app --reload
"""

from fastapi import FastAPI, Depends, Query, Header, HTTPException

app = FastAPI()


# ============================================================================
# BASIC CLASS DEPENDENCY
# ============================================================================

class CommonQueryParams:
    """Groups related query parameters with helper methods"""
    
    def __init__(
        self,
        q: str | None = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100)
    ):
        self.q = q
        self.skip = skip
        self.limit = limit
    
    def get_offset(self) -> int:
        return self.skip
    
    def get_limit(self) -> int:
        return self.limit
    
    def has_query(self) -> bool:
        return self.q is not None


@app.get("/items-class")
async def read_items_class(commons: CommonQueryParams = Depends()):
    """
    FastAPI automatically instantiates CommonQueryParams.
    Note: Depends() with no argument uses type annotation.
    
    Test: /items-class?q=phone&skip=10&limit=20
    """
    return {
        "query": commons.q,
        "skip": commons.skip,
        "limit": commons.limit,
        "has_query": commons.has_query(),
        "offset": commons.get_offset()
    }


# ============================================================================
# TYPE ANNOTATION SHORTCUT
# ============================================================================

class Pagination:
    """Simple pagination class"""
    
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(10, ge=1, le=100, description="Maximum items to return")
    ):
        self.skip = skip
        self.limit = limit
    
    def as_dict(self):
        return {"skip": self.skip, "limit": self.limit}


@app.get("/items-explicit")
async def read_items_explicit(pagination: Pagination = Depends(Pagination)):
    """Explicit form - Depends(Pagination)"""
    return pagination.as_dict()


@app.get("/items-shortcut")
async def read_items_shortcut(pagination: Pagination = Depends()):
    """
    Shortcut form - Depends() with no argument.
    FastAPI uses type annotation (Pagination) automatically.
    """
    return pagination.as_dict()


# ============================================================================
# CLASS DEPENDENCY WITH PROCESSING LOGIC
# ============================================================================

class SearchParams:
    """Search parameters with validation and processing"""
    
    def __init__(
        self,
        q: str = Query(..., min_length=2, max_length=50),
        category: str = Query("all"),
        sort: str = Query("relevance", pattern="^(relevance|date|popularity)$")
    ):
        valid_categories = {"all", "books", "electronics", "clothing"}
        if category not in valid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )
        
        self.q = q.strip().lower()
        self.category = category
        self.sort = sort
        self.filter = self._build_filter()
    
    def _build_filter(self) -> dict:
        """Build database-friendly filter"""
        filters = {"query": self.q}
        if self.category != "all":
            filters["category"] = self.category
        return filters
    
    def get_sort_key(self) -> str:
        """Convert API sort value to DB field"""
        sort_map = {
            "relevance": "score",
            "date": "created_at",
            "popularity": "view_count",
        }
        return sort_map[self.sort]


@app.get("/search")
async def search(params: SearchParams = Depends()):
    """
    Handler receives fully processed search parameters.
    All validation, normalization, and filter building done in dependency.
    
    Test: /search?q=FastAPI&category=books&sort=date
    """
    results = [
        {"id": 1, "title": "Result 1"},
        {"id": 2, "title": "Result 2"},
    ]
    
    return {
        "query": params.q,
        "category": params.category,
        "sort": params.sort,
        "filter": params.filter,
        "sort_key": params.get_sort_key(),
        "results": results,
    }


# ============================================================================
# CLASS DEPENDENCY WITH STATE (per-request)
# ============================================================================

class RateLimiter:
    """
    Demonstrates per-request state.
    Note: This is NOT real rate limiting (state resets per request).
    Production would use Redis or similar.
    """
    
    def __init__(self, x_token: str = Header(...)):
        self.token = x_token
        self.requests_made = 0
        self.limit = 100
    
    def check_limit(self):
        if self.requests_made >= self.limit:
            raise HTTPException(429, "Rate limit exceeded")
    
    def increment(self):
        self.requests_made += 1
    
    def remaining(self) -> int:
        return self.limit - self.requests_made


@app.get("/limited-resource")
async def limited_resource(limiter: RateLimiter = Depends()):
    """
    Test with: curl -H "X-Token: any-token" http://localhost:8000/limited-resource
    
    Note: State resets per request in this example.
    """
    limiter.check_limit()
    limiter.increment()
    
    return {
        "message": "Success",
        "remaining_requests": limiter.remaining()
    }


# ============================================================================
# INHERITING CLASS DEPENDENCIES
# ============================================================================

class BaseQueryParams:
    """Base class with common pagination parameters"""
    
    def __init__(
        self,
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100)
    ):
        self.skip = skip
        self.limit = limit


class SearchQueryParams(BaseQueryParams):
    """Extends base with search capability"""
    
    def __init__(
        self,
        q: str = Query(..., min_length=2),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100)
    ):
        super().__init__(skip=skip, limit=limit)
        self.q = q


class FilteredSearchParams(SearchQueryParams):
    """Further extends with filtering"""
    
    def __init__(
        self,
        q: str = Query(..., min_length=2),
        category: str = Query("all"),
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100)
    ):
        super().__init__(q=q, skip=skip, limit=limit)
        self.category = category


@app.get("/simple-list")
async def simple_list(params: BaseQueryParams = Depends()):
    """Just pagination - Test: /simple-list?skip=5&limit=10"""
    return {"skip": params.skip, "limit": params.limit}


@app.get("/search-list")
async def search_list(params: SearchQueryParams = Depends()):
    """Pagination + search - Test: /search-list?q=test&skip=5&limit=10"""
    return {"q": params.q, "skip": params.skip, "limit": params.limit}


@app.get("/filtered-search-list")
async def filtered_search_list(params: FilteredSearchParams = Depends()):
    """
    Pagination + search + filtering
    Test: /filtered-search-list?q=test&category=books&skip=5&limit=10
    """
    return {
        "q": params.q,
        "category": params.category,
        "skip": params.skip,
        "limit": params.limit
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
