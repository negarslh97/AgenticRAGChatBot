"""
Category Management Schemas
===========================

Enhanced Pydantic schemas for category management.
Includes comprehensive validation rules and custom validators.
"""

from pydantic import BaseModel, Field, validator
import re
from typing import List, Optional, Dict, Any
from datetime import datetime


class CategoryBase(BaseModel):
    """Base schema for category with common fields."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Category name (1-200 characters)",
        example="Getting Started"
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Category slug (URL-friendly identifier)",
        example="getting-started"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Category description (max 1000 characters)",
        example="Articles to help new users get started with SallyBot"
    )
    parent_id: Optional[str] = Field(
        None,
        description="Parent category ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    is_public: bool = Field(
        True,
        description="Whether category is public (visible to all users)",
        example=True
    )
    color: Optional[str] = Field(
        None,
        description="Category color in hex format",
        example="#4CAF50"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate category name."""
        if not v.strip():
            raise ValueError('Category name cannot be empty')
        
        # Remove extra whitespace
        name = ' '.join(v.strip().split())
        
        if len(name) < 1:
            raise ValueError('Category name must be at least 1 character long')
        
        if len(name) > 200:
            raise ValueError('Category name must be at most 200 characters long')
        
        return name
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate category slug."""
        if not v.strip():
            raise ValueError('Category slug cannot be empty')
        
        # Remove extra whitespace and lowercase
        slug = ' '.join(v.strip().split()).lower()
        
        if len(slug) < 1:
            raise ValueError('Category slug must be at least 1 character long')
        
        if len(slug) > 200:
            raise ValueError('Category slug must be at most 200 characters long')
        
        # Check for valid slug characters (letters, numbers, hyphens, underscores)
        if not slug.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Category slug can only contain letters, numbers, hyphens, and underscores')
        
        # Check for reserved slugs
        reserved_slugs = ['admin', 'api', 'auth', 'dashboard', 'login', 'logout', 'register', 'user', 'users']
        if slug in reserved_slugs:
            raise ValueError(f'Category slug conflicts with reserved slug: {slug}')
        
        return slug
    
    @validator('description')
    def validate_description(cls, v):
        """Validate category description."""
        if v is None:
            return v
        
        if len(v) > 1000:
            raise ValueError('Description must be at most 1000 characters long')
        
        return v
    
    @validator('parent_id')
    def validate_parent_id(cls, v):
        """Validate parent category ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Parent category ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Parent category ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Parent category ID must contain only hexadecimal characters')
        
        return v
    
    @validator('color')
    def validate_color(cls, v):
        """Validate color format."""
        if v is None:
            return v
        
        if not v.strip():
            return None
        
        # Remove extra whitespace
        color = v.strip()
        
        # Check for valid hex color format (e.g., #4CAF50 or #FFF)
        if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color):
            raise ValueError('Color must be a valid hex code (e.g., #4CAF50 or #FFF)')
        
        return color


class CategoryCreate(CategoryBase):
    """Schema for category creation."""
    pass


class CategoryUpdate(BaseModel):
    """Schema for category update."""
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Category name (1-200 characters)",
        example="Getting Started"
    )
    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Category slug (URL-friendly identifier)",
        example="getting-started"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Category description (max 1000 characters)",
        example="Articles to help new users get started with SallyBot"
    )
    parent_id: Optional[str] = Field(
        None,
        description="Parent category ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    is_public: Optional[bool] = Field(
        None,
        description="Whether category is public (visible to all users)",
        example=True
    )
    color: Optional[str] = Field(
        None,
        description="Category color in hex format",
        example="#4CAF50"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate category name."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Category name cannot be empty')
        
        # Remove extra whitespace
        name = ' '.join(v.strip().split())
        
        if len(name) < 1:
            raise ValueError('Category name must be at least 1 character long')
        
        if len(name) > 200:
            raise ValueError('Category name must be at most 200 characters long')
        
        return name
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate category slug."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Category slug cannot be empty')
        
        # Remove extra whitespace and lowercase
        slug = ' '.join(v.strip().split()).lower()
        
        if len(slug) < 1:
            raise ValueError('Category slug must be at least 1 character long')
        
        if len(slug) > 200:
            raise ValueError('Category slug must be at most 200 characters long')
        
        # Check for valid slug characters (letters, numbers, hyphens, underscores)
        if not slug.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Category slug can only contain letters, numbers, hyphens, and underscores')
        
        # Check for reserved slugs
        reserved_slugs = ['admin', 'api', 'auth', 'dashboard', 'login', 'logout', 'register', 'user', 'users']
        if slug in reserved_slugs:
            raise ValueError(f'Category slug conflicts with reserved slug: {slug}')
        
        return slug
    
    @validator('description')
    def validate_description(cls, v):
        """Validate category description."""
        if v is None:
            return v
        
        if len(v) > 1000:
            raise ValueError('Description must be at most 1000 characters long')
        
        return v
    
    @validator('parent_id')
    def validate_parent_id(cls, v):
        """Validate parent category ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Parent category ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Parent category ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Parent category ID must contain only hexadecimal characters')
        
        return v
    
    @validator('color')
    def validate_color(cls, v):
        """Validate color format."""
        if v is None:
            return v
        
        if not v.strip():
            return None
        
        # Remove extra whitespace
        color = v.strip()
        
        # Check for valid hex color format (e.g., #4CAF50 or #FFF)
        if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color):
            raise ValueError('Color must be a valid hex code (e.g., #4CAF50 or #FFF)')
        
        return color


class CategoryResponse(BaseModel):
    """Schema for category response."""
    
    id: str = Field(..., description="Category ID", example="60c72b2f9b1d8e001f8e4cde")
    name: str = Field(..., description="Category name", example="Getting Started")
    slug: str = Field(..., description="Category slug", example="getting-started")
    description: Optional[str] = Field(None, description="Category description", example="Articles to help new users get started...")
    color: Optional[str] = Field(None, description="Category color in hex format", example="#4CAF50")
    parent_id: Optional[str] = Field(None, description="Parent category ID", example="60c72b2f9b1d8e001f8e4cdf")
    is_public: bool = Field(..., description="Category public status", example=True)
    created_at: datetime = Field(..., description="Category creation timestamp")
    updated_at: datetime = Field(..., description="Category update timestamp")
    
    # Additional information
    articles_count: Optional[int] = Field(0, description="Number of articles in category", example=15)
    children_count: Optional[int] = Field(0, description="Number of child categories", example=3)
    depth: Optional[int] = Field(0, description="Category depth in hierarchy", example=1)
    path: Optional[str] = Field(None, description="Category path in hierarchy", example="/getting-started")


class CategoryTreeNode(BaseModel):
    """Schema for category tree node."""
    
    id: str = Field(..., description="Category ID", example="60c72b2f9b1d8e001f8e4cde")
    name: str = Field(..., description="Category name", example="Getting Started")
    slug: str = Field(..., description="Category slug", example="getting-started")
    description: Optional[str] = Field(None, description="Category description", example="Articles to help new users...")
    color: Optional[str] = Field(None, description="Category color in hex format", example="#4CAF50")
    is_public: bool = Field(..., description="Category public status", example=True)
    depth: int = Field(..., description="Category depth in hierarchy", example=1)
    path: str = Field(..., description="Category path", example="/getting-started")
    children: List['CategoryTreeNode'] = Field(default_factory=list, description="Child categories")
    articles_count: int = Field(..., description="Number of articles", example=15)


class CategoryDeleteResult(BaseModel):
    """Schema for category delete operation result."""
    
    category_id: str = Field(..., description="Deleted category ID", example="60c72b2f9b1d8e001f8e4cde")
    category_name: str = Field(..., description="Deleted category name", example="Getting Started")
    children_count: int = Field(..., description="Number of child categories", example=3)
    articles_count: int = Field(..., description="Number of articles", example=15)
    deleted_categories: List[str] = Field(default_factory=list, description="List of deleted category IDs", example=["60c72b2f9b1d8e001f8e4cde", "60c72b2f9b1d8e001f8e4cdf"])
    affected_articles: List[Dict[str, Any]] = Field(default_factory=list, description="List of affected articles", example=[{"id": "60c72b2f9b1d8e001f8e4cdg", "title": "Article Title"}])
    moved_children: List[str] = Field(default_factory=list, description="List of moved child category IDs", example=["60c72b2f9b1d8e001f8e4cdh"])
    message: str = Field(..., description="Operation result message", example="Category 'Getting Started' deleted successfully")


class CategoryStatsResponse(BaseModel):
    """Schema for category statistics response."""
    
    total_categories: int = Field(..., description="Total number of categories", example=25)
    public_categories: int = Field(..., description="Number of public categories", example=20)
    private_categories: int = Field(..., description="Number of private categories", example=5)
    top_level_categories: int = Field(..., description="Number of top-level categories", example=8)
    total_articles: int = Field(..., description="Total number of articles", example=150)
    most_popular_categories: List[Dict[str, Any]] = Field(..., description="Most popular categories", example=[{"name": "Getting Started", "articles_count": 25}, {"name": "Advanced", "articles_count": 18}])
    recent_categories: List[CategoryResponse] = Field(..., description="Recently created categories", example=[])


class CategoryListResponse(BaseModel):
    """Schema for category list response."""
    
    categories: List[CategoryResponse] = Field(..., description="List of categories")
    total: int = Field(..., description="Total number of categories")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")


class CategorySearchRequest(BaseModel):
    """Schema for category search request."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query (1-200 characters)",
        example="getting started"
    )
    is_public_only: bool = Field(
        False,
        description="Search only public categories",
        example=False
    )
    parent_id: Optional[str] = Field(
        None,
        description="Parent category ID to limit search scope",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    max_depth: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Maximum depth to search",
        example=3
    )
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of results to return (1-100)",
        example=20
    )
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query."""
        if not v.strip():
            raise ValueError('Search query cannot be empty')
        
        # Remove extra whitespace
        query = ' '.join(v.strip().split())
        
        if len(query) < 1:
            raise ValueError('Search query must be at least 1 character long')
        
        if len(query) > 200:
            raise ValueError('Search query must be at most 200 characters long')
        
        return query
    
    @validator('parent_id')
    def validate_parent_id(cls, v):
        """Validate parent category ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Parent category ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Parent category ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Parent category ID must contain only hexadecimal characters')
        
        return v


class CategorySearchResponse(BaseModel):
    """Schema for category search response."""
    
    categories: List[CategoryResponse] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Search query", example="getting started")
    limit: int = Field(..., description="Number of results returned", example=20)


class CategoryBulkActionRequest(BaseModel):
    """Schema for category bulk action request."""
    
    category_ids: List[str] = Field(..., description="List of category IDs", example=["60c72b2f9b1d8e001f8e4cde", "60c72b2f9b1d8e001f8e4cdf"])
    action: str = Field(..., description="Action to perform", example="make_public")
    value: Optional[Any] = Field(None, description="Action value (e.g., new parent_id)", example="60c72b2f9b1d8e001f8e4cdg")
    
    @validator('category_ids')
    def validate_category_ids(cls, v):
        """Validate category IDs format."""
        if not v:
            raise ValueError('At least one category ID is required')
        
        if len(v) > 50:
            raise ValueError('Cannot perform bulk action on more than 50 categories')
        
        for category_id in v:
            if not category_id.strip():
                raise ValueError('Category ID cannot be empty')
            
            # Basic ObjectId format validation
            if len(category_id) != 24:
                raise ValueError(f'Invalid category ID format: {category_id}')
            
            # Check for valid hex characters
            if not all(c in '0123456789abcdefABCDEF' for c in category_id):
                raise ValueError(f'Category ID must contain only hexadecimal characters: {category_id}')
        
        return v
    
    @validator('action')
    def validate_action(cls, v):
        """Validate action value."""
        valid_actions = ['make_public', 'make_private', 'move_to_parent', 'delete']
        if v not in valid_actions:
            raise ValueError(f'Invalid action. Must be one of: {", ".join(valid_actions)}')
        return v


class CategoryBulkActionResponse(BaseModel):
    """Schema for category bulk action response."""
    
    success_count: int = Field(..., description="Number of successful actions", example=5)
    failure_count: int = Field(..., description="Number of failed actions", example=1)
    errors: List[str] = Field(default_factory=list, description="Error messages", example=["Category not found: 60c72b2f9b1d8e001f8e4cde"])
    message: str = Field(..., description="Action result message", example="Bulk action completed with 5 successes and 1 failure")


class CategoryReorderRequest(BaseModel):
    """Schema for category reorder request."""
    
    category_id: str = Field(..., description="Category ID to reorder", example="60c72b2f9b1d8e001f8e4cde")
    new_parent_id: Optional[str] = Field(None, description="New parent category ID", example="60c72b2f9b1d8e001f8e4cdf")
    new_order: Optional[int] = Field(None, description="New order position", example=2)
    
    @validator('category_id')
    def validate_category_id(cls, v):
        """Validate category ID format."""
        if not v.strip():
            raise ValueError('Category ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Category ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Category ID must contain only hexadecimal characters')
        
        return v
    
    @validator('new_parent_id')
    def validate_new_parent_id(cls, v):
        """Validate new parent category ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('New parent category ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('New parent category ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('New parent category ID must contain only hexadecimal characters')
        
        return v
    
    @validator('new_order')
    def validate_new_order(cls, v):
        """Validate new order position."""
        if v is None:
            return v
        
        if v < 0:
            raise ValueError('Order position cannot be negative')
        
        if v > 1000:
            raise ValueError('Order position cannot be greater than 1000')
        
        return v


class CategoryReorderResponse(BaseModel):
    """Schema for category reorder response."""
    
    category_id: str = Field(..., description="Reordered category ID", example="60c72b2f9b1d8e001f8e4cde")
    new_parent_id: Optional[str] = Field(None, description="New parent category ID", example="60c72b2f9b1d8e001f8e4cdf")
    new_order: Optional[int] = Field(None, description="New order position", example=2)
    message: str = Field(..., description="Reorder result message", example="Category reordered successfully")