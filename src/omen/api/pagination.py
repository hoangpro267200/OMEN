"""
Cursor-based Pagination for OMEN API.

Provides efficient pagination using opaque cursors instead of offset/limit.
Benefits:
- No page drift when data changes
- Consistent results across pages
- Efficient database queries (no OFFSET)
"""

from __future__ import annotations

import json
import logging
from base64 import b64decode, b64encode
from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CursorPagination(BaseModel, Generic[T]):
    """
    Cursor-based pagination response.
    
    Example response:
    {
        "items": [...],
        "next_cursor": "eyJsYXN0X2lkIjogIk9NRU4tMTIzIn0=",
        "prev_cursor": null,
        "has_more": true,
        "total_count": 1234
    }
    """
    
    model_config = ConfigDict(frozen=True)
    
    items: list[T] = Field(..., description="Page of items")
    next_cursor: Optional[str] = Field(
        None, 
        description="Cursor for next page (null if no more pages)"
    )
    prev_cursor: Optional[str] = Field(
        None, 
        description="Cursor for previous page (null if first page)"
    )
    has_more: bool = Field(..., description="Whether there are more items")
    total_count: Optional[int] = Field(
        None, 
        description="Total count (optional, may be expensive to compute)"
    )
    page_size: int = Field(..., description="Number of items in this page")


class CursorData(BaseModel):
    """Internal cursor data structure."""
    
    last_id: Optional[str] = None
    last_timestamp: Optional[str] = None
    direction: str = "forward"  # "forward" or "backward"


def encode_cursor(data: CursorData) -> str:
    """
    Encode cursor data to opaque string.
    
    Uses base64 encoding to create an opaque cursor.
    """
    json_str = data.model_dump_json()
    return b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> Optional[CursorData]:
    """
    Decode cursor string to data.
    
    Returns None if cursor is invalid.
    """
    try:
        json_str = b64decode(cursor.encode()).decode()
        return CursorData.model_validate_json(json_str)
    except Exception as e:
        logger.warning("Invalid cursor: %s", e)
        return None


def create_page_response(
    items: list,
    limit: int,
    get_item_id: callable,
    get_item_timestamp: Optional[callable] = None,
    total_count: Optional[int] = None,
    prev_cursor_data: Optional[CursorData] = None,
) -> CursorPagination:
    """
    Create a paginated response from items.
    
    Args:
        items: Items fetched (should be limit + 1 to check has_more)
        limit: Requested page size
        get_item_id: Function to extract item ID
        get_item_timestamp: Optional function to extract timestamp
        total_count: Optional total count
        prev_cursor_data: Previous cursor data for prev_cursor
        
    Returns:
        CursorPagination response
    """
    has_more = len(items) > limit
    
    # Trim to requested limit
    if has_more:
        items = items[:limit]
    
    # Create next cursor if there are more items
    next_cursor = None
    if has_more and items:
        last_item = items[-1]
        cursor_data = CursorData(
            last_id=get_item_id(last_item),
            last_timestamp=get_item_timestamp(last_item).isoformat() if get_item_timestamp else None,
            direction="forward",
        )
        next_cursor = encode_cursor(cursor_data)
    
    # Create prev cursor if not first page
    prev_cursor = None
    if prev_cursor_data and items:
        first_item = items[0]
        cursor_data = CursorData(
            last_id=get_item_id(first_item),
            last_timestamp=get_item_timestamp(first_item).isoformat() if get_item_timestamp else None,
            direction="backward",
        )
        prev_cursor = encode_cursor(cursor_data)
    
    return CursorPagination(
        items=items,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
        has_more=has_more,
        total_count=total_count,
        page_size=len(items),
    )


# Common pagination parameters
class PaginationParams(BaseModel):
    """Common pagination query parameters."""
    
    cursor: Optional[str] = Field(
        None, 
        description="Cursor from previous response for pagination"
    )
    limit: int = Field(
        50, 
        ge=1, 
        le=100, 
        description="Number of items per page (max 100)"
    )


def parse_pagination_params(
    cursor: Optional[str] = None,
    limit: int = 50,
) -> tuple[Optional[CursorData], int]:
    """
    Parse pagination parameters.
    
    Returns:
        (cursor_data, limit) tuple
    """
    cursor_data = None
    if cursor:
        cursor_data = decode_cursor(cursor)
    
    # Ensure limit is within bounds
    limit = min(max(1, limit), 100)
    
    return cursor_data, limit
