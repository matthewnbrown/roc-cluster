"""
Pagination utilities for API responses
"""

from typing import List, TypeVar, Type
from sqlalchemy.orm import Query
from api.schemas import PaginationMeta, PaginatedResponse

T = TypeVar('T')

def create_pagination_meta(page: int, per_page: int, total: int) -> PaginationMeta:
    """Create pagination metadata"""
    total_pages = (total + per_page - 1) // per_page  # Ceiling division
    has_next = page < total_pages
    has_prev = page > 1
    next_page = page + 1 if has_next else None
    prev_page = page - 1 if has_prev else None
    
    return PaginationMeta(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        next_page=next_page,
        prev_page=prev_page
    )

def paginate_query(
    query: Query, 
    page: int, 
    per_page: int, 
    response_model: Type[T]
) -> PaginatedResponse[T]:
    """Paginate a SQLAlchemy query and return a paginated response"""
    # Get total count
    total = query.count()
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get paginated results
    items = query.offset(offset).limit(per_page).all()
    
    # Convert to response models
    data = [response_model.from_orm(item) for item in items]
    
    # Create pagination metadata
    pagination = create_pagination_meta(page, per_page, total)
    
    return PaginatedResponse(data=data, pagination=pagination)

def paginate_list(
    items: List[T], 
    page: int, 
    per_page: int
) -> PaginatedResponse[T]:
    """Paginate a list of items and return a paginated response"""
    total = len(items)
    
    # Calculate offset and slice
    offset = (page - 1) * per_page
    paginated_items = items[offset:offset + per_page]
    
    # Create pagination metadata
    pagination = create_pagination_meta(page, per_page, total)
    
    return PaginatedResponse(data=paginated_items, pagination=pagination)
