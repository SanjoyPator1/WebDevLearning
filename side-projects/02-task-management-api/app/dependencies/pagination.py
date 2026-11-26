from fastapi import Query
from pydantic import BaseModel
from typing import Optional, Any, List, Dict

class PaginationParams(BaseModel):
    """Pagination parameters model"""
    limit: int
    offset: int
    page: int
    per_page: int

    @property
    def skip(self) -> int:
        """Alias for offset"""
        return self.offset

    def paginate_list(self, items: List[Any]) -> Dict[str, Any]:
        """Apply pagination to a list and return metadata"""
        total = len(items)
        paginated_items = items[self.offset:self.offset + self.limit]

        return {
            "items": paginated_items,
            "pagination": {
                "total": total,
                "page": self.page,
                "per_page": self.per_page,
                "total_pages": (total + self.per_page - 1) // self.per_page,
                "has_next": (self.offset + self.limit) < total,
                "has_prev": self.offset > 0,
                "next_page": self.page + 1 if (self.offset + self.limit) < total else None,
                "prev_page": self.page - 1 if self.offset > 0 else None
            }
        }

def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page (1-100)")
) -> PaginationParams:
    """
    Pagination dependency - converts page/per_page to limit/offset
    """
    limit = per_page
    offset = (page - 1) * per_page

    return PaginationParams(
        limit=limit,
        offset=offset,
        page=page,
        per_page=per_page
    )

def get_flexible_pagination(
    limit: Optional[int] = Query(10, ge=1, le=100, description="Number of items to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of items to skip"),
    page: Optional[int] = Query(None, ge=1, description="Page number (alternative to offset)"),
    per_page: Optional[int] = Query(None, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """
    Flexible pagination dependency - supports both offset/limit and page/per_page
    """

    # If page-based pagination is used
    if page is not None:
        per_page = per_page or 10
        limit = per_page
        offset = (page - 1) * per_page
        return PaginationParams(
            limit=limit,
            offset=offset,
            page=page,
            per_page=per_page
        )

    # Use offset/limit pagination
    limit = limit or 10
    offset = offset or 0
    page = (offset // limit) + 1
    per_page = limit

    return PaginationParams(
        limit=limit,
        offset=offset,
        page=page,
        per_page=per_page
    )