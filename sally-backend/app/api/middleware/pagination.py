"""
Pagination and Filtering Middleware
===================================

Comprehensive pagination and filtering system for API endpoints.
Provides consistent pagination parameters and filtering capabilities.
"""

from typing import Optional, List, Dict, Any, Union, Type
from pydantic import BaseModel, Field, validator
from fastapi import Query
from enum import Enum
from datetime import datetime


class SortOrder(str, Enum):
    """Sort order enumeration."""
    ASC = "asc"
    DESC = "desc"


class PaginationParams(BaseModel):
    """Base pagination parameters for all list endpoints."""
    
    page: int = Field(
        1,
        ge=1,
        le=10000,
        description="Page number (1-indexed)",
        example=1
    )
    
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of items per page",
        example=20
    )
    
    sort_by: Optional[str] = Field(
        None,
        description="Field to sort by",
        example="created_at"
    )
    
    sort_order: SortOrder = Field(
        SortOrder.DESC,
        description="Sort order (ascending or descending)",
        example=SortOrder.DESC
    )
    
    search: Optional[str] = Field(
        None,
        description="Search query string",
        example="john doe"
    )
    
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional filters as key-value pairs",
        example={"status": "active", "category": "user"}
    )
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.limit
    
    @property
    def skip(self) -> int:
        """Alias for offset (compatibility with existing code)."""
        return self.offset
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        if v is not None:
            # Remove any SQL injection attempts
            if any(char in v for char in [';', '--', '/*', '*/', 'xp_', 'sp_']):
                raise ValueError("Invalid sort field")
        
        return v


class PaginatedResponse(BaseModel):
    """Standard paginated response structure."""
    
    success: bool = Field(True, description="Whether the request was successful")
    data: List[Any] = Field(..., description="List of items for the current page")
    meta: Dict[str, Any] = Field(..., description="Pagination metadata")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    timestamp: str = Field(..., description="Response timestamp", example="2025-10-29T07:35:15.297Z")
    
    @classmethod
    def create(
        cls,
        items: List[Any],
        total_count: int,
        page: int,
        limit: int,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        search: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> 'PaginatedResponse':
        """Create a paginated response."""
        
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        has_next = page < total_pages
        has_previous = page > 1
        
        meta = {
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "per_page": limit,
            "has_next": has_next,
            "has_previous": has_previous,
            "next_page": page + 1 if has_next else None,
            "previous_page": page - 1 if has_previous else None
        }
        
        pagination = {
            "sort_by": sort_by,
            "sort_order": sort_order,
            "search": search,
            "filters": filters or {},
            "showing": f"{(page - 1) * limit + 1}-{min(page * limit, total_count)} of {total_count}"
        }
        
        return cls(
            data=items,
            meta=meta,
            pagination=pagination,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


class FilterField(BaseModel):
    """Represents a filterable field."""
    
    name: str = Field(..., description="Field name", example="status")
    field_type: str = Field(..., description="Field type", example="string")
    allowed_values: Optional[List[str]] = Field(None, description="Allowed values for enum fields", example=["active", "inactive"])
    case_sensitive: bool = Field(True, description="Whether search is case sensitive", example=True)
    search_type: str = Field("exact", description="Search type: exact, contains, starts_with, ends_with", example="contains")


class FilteringSchema(BaseModel):
    """Schema for defining available filters for an endpoint."""
    
    allowed_sorts: List[str] = Field(..., description="Fields that can be sorted", example=["created_at", "updated_at", "name"])
    allowed_filters: List[FilterField] = Field(..., description="Available filter fields", example=[])
    default_sort: str = Field("created_at", description="Default sort field", example="created_at")
    default_sort_order: SortOrder = Field(SortOrder.DESC, description="Default sort order", example=SortOrder.DESC)
    default_limit: int = Field(20, description="Default items per page", example=20)
    max_limit: int = Field(100, description="Maximum items per page", example=100)


class PaginationConfig:
    """Configuration for pagination on specific endpoints."""
    
    def __init__(
        self,
        allowed_sorts: List[str],
        allowed_filters: List[FilterField] = None,
        default_sort: str = "created_at",
        default_sort_order: SortOrder = SortOrder.DESC,
        default_limit: int = 20,
        max_limit: int = 100
    ):
        self.allowed_sorts = allowed_sorts
        self.allowed_filters = allowed_filters or []
        self.default_sort = default_sort
        self.default_sort_order = default_sort_order
        self.default_limit = default_limit
        self.max_limit = max_limit
    
    def create_filtering_schema(self) -> FilteringSchema:
        """Create a filtering schema from this config."""
        return FilteringSchema(
            allowed_sorts=self.allowed_sorts,
            allowed_filters=self.allowed_filters,
            default_sort=self.default_sort,
            default_sort_order=self.default_sort_order,
            default_limit=self.default_limit,
            max_limit=self.max_limit
        )


class PaginationService:
    """Service for handling pagination and filtering operations."""
    
    @staticmethod
    def build_query_params(params: PaginationParams, config: PaginationConfig) -> Dict[str, Any]:
        """Build query parameters for database operations."""
        
        query_params = {
            "skip": params.skip,
            "limit": min(params.limit, config.max_limit)
        }
        
        # Add sorting
        sort_field = params.sort_by or config.default_sort
        if sort_field in config.allowed_sorts:
            sort_order = params.sort_order.value
            if sort_order == "asc":
                query_params["sort"] = [(sort_field, 1)]
            else:
                query_params["sort"] = [(sort_field, -1)]
        
        # Add search
        if params.search:
            query_params["search"] = params.search
        
        # Add filters
        if params.filters:
            query_params["filters"] = params.filters
        
        return query_params
    
    @staticmethod
    def build_mongodb_sort(sort_by: str, sort_order: SortOrder) -> List[tuple]:
        """Build MongoDB sort specification."""
        if sort_order == SortOrder.ASC:
            return [(sort_by, 1)]
        else:
            return [(sort_by, -1)]
    
    @staticmethod
    def apply_search_filter(query: Dict[str, Any], search_field: str, search_value: str, case_sensitive: bool = True) -> Dict[str, Any]:
        """Apply search filter to a query."""
        if case_sensitive:
            query[search_field] = {"$regex": search_value, "$options": "i"}
        else:
            query[search_field] = {"$regex": search_value, "$options": "i"}
        
        return query
    
    @staticmethod
    def apply_exact_filter(query: Dict[str, Any], field: str, value: Any) -> Dict[str, Any]:
        """Apply exact value filter."""
        query[field] = value
        return query
    
    @staticmethod
    def apply_range_filter(query: Dict[str, Any], field: str, min_value: Any = None, max_value: Any = None) -> Dict[str, Any]:
        """Apply range filter for numeric/date fields."""
        range_condition = {}
        if min_value is not None:
            range_condition["$gte"] = min_value
        if max_value is not None:
            range_condition["$lte"] = max_value
        
        if range_condition:
            query[field] = range_condition
        
        return query


# Predefined pagination configurations for common use cases
ADMIN_USERS_PAGINATION = PaginationConfig(
    allowed_sorts=["created_at", "updated_at", "full_name", "email", "is_active"],
    allowed_filters=[
        FilterField(name="is_active", field_type="boolean"),
        FilterField(name="role_name", field_type="string"),
        FilterField(name="email", field_type="string", search_type="contains"),
        FilterField(name="full_name", field_type="string", search_type="contains")
    ],
    default_sort="created_at",
    default_sort_order=SortOrder.DESC,
    default_limit=10,
    max_limit=50
)

ARTICLES_PAGINATION = PaginationConfig(
    allowed_sorts=["created_at", "updated_at", "published_at", "title", "status"],
    allowed_filters=[
        FilterField(name="status", field_type="string", allowed_values=["draft", "published", "archived"]),
        FilterField(name="visibility", field_type="string", allowed_values=["public", "customer", "private"]),
        FilterField(name="title", field_type="string", search_type="contains"),
        FilterField(name="content", field_type="string", search_type="contains")
    ],
    default_sort="created_at",
    default_sort_order=SortOrder.DESC,
    default_limit=20,
    max_limit=50
)

CONVERSATIONS_PAGINATION = PaginationConfig(
    allowed_sorts=["created_at", "updated_at", "customer_id", "admin_id"],
    allowed_filters=[
        FilterField(name="status", field_type="string", allowed_values=["active", "completed"]),
        FilterField(name="customer_id", field_type="string"),
        FilterField(name="admin_id", field_type="string"),
        FilterField(name="title", field_type="string", search_type="contains")
    ],
    default_sort="updated_at",
    default_sort_order=SortOrder.DESC,
    default_limit=20,
    max_limit=50
)

CATEGORIES_PAGINATION = PaginationConfig(
    allowed_sorts=["created_at", "updated_at", "name", "slug"],
    allowed_filters=[
        FilterField(name="is_public", field_type="boolean"),
        FilterField(name="parent_id", field_type="string"),
        FilterField(name="name", field_type="string", search_type="contains"),
        FilterField(name="slug", field_type="string", search_type="contains")
    ],
    default_sort="name",
    default_sort_order=SortOrder.ASC,
    default_limit=20,
    max_limit=100
)

ACTIVITY_LOGS_PAGINATION = PaginationConfig(
    allowed_sorts=["created_at", "action", "admin_id"],
    allowed_filters=[
        FilterField(name="action", field_type="string"),
        FilterField(name="admin_id", field_type="string"),
        FilterField(name="resource_type", field_type="string"),
        FilterField(name="resource_id", field_type="string")
    ],
    default_sort="created_at",
    default_sort_order=SortOrder.DESC,
    default_limit=50,
    max_limit=100
)


def create_paginated_response(
    items: List[Any],
    total_count: int,
    page: int,
    limit: int,
    params: PaginationParams
) -> PaginatedResponse:
    """Helper function to create a paginated response."""
    return PaginatedResponse.create(
        items=items,
        total_count=total_count,
        page=page,
        limit=limit,
        sort_by=params.sort_by,
        sort_order=params.sort_order.value,
        search=params.search,
        filters=params.filters
    )


# FastAPI dependency functions for easy integration
def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    search: Optional[str] = Query(None, description="Search query"),
    filters: Optional[str] = Query(None, description="JSON filters")
) -> PaginationParams:
    """Dependency function to get pagination parameters from query string."""
    
    # Parse filters JSON string if provided
    parsed_filters = None
    if filters:
        try:
            import json
            parsed_filters = json.loads(filters)
        except json.JSONDecodeError:
            parsed_filters = None
    
    return PaginationParams(
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        filters=parsed_filters
    )