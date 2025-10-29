"""
Knowledge Base Schemas
======================

Enhanced Pydantic schemas for knowledge base functionality.
Includes comprehensive validation rules and custom validators.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ArticleStatus(str, Enum):
    """Enum for article status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ArticleVisibility(str, Enum):
    """Enum for article visibility."""
    PUBLIC = "public"
    CUSTOMER = "customer"
    PRIVATE = "private"


class MarkdownNodeResponse(BaseModel):
    """Schema for markdown node response."""
    
    id: str = Field(..., description="Node ID", example="60c72b2f9b1d8e001f8e4cde")
    title: str = Field(..., description="Node title", example="Introduction")
    level: int = Field(..., description="Node level", example=1)
    content: str = Field(..., description="Node content", example="This is the introduction section...")
    parent_id: Optional[str] = Field(None, description="Parent node ID", example="60c72b2f9b1d8e001f8e4cdf")
    path: str = Field(..., description="Node path", example="/introduction")
    order: int = Field(..., description="Node order", example=1)
    children: List['MarkdownNodeResponse'] = Field(default_factory=list, description="Child nodes")


class MarkdownTreeResponse(BaseModel):
    """Schema for markdown tree response."""
    
    article_id: str = Field(..., description="Article ID", example="60c72b2f9b1d8e001f8e4cde")
    root_nodes: List[MarkdownNodeResponse] = Field(..., description="Root nodes of the tree")


class ArticleCreate(BaseModel):
    """Schema for article creation."""
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Article title (1-200 characters)",
        example="Getting Started with SallyBot"
    )
    content_markdown: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Article content in markdown format (10-50000 characters)",
        example="# Getting Started with SallyBot\n\nWelcome to SallyBot..."
    )
    content_html: Optional[str] = Field(
        None,
        max_length=100000,
        description="Article content in HTML format (max 100000 characters)",
        example="<h1>Getting Started with SallyBot</h1><p>Welcome to SallyBot...</p>"
    )
    summary: Optional[str] = Field(
        None,
        max_length=1000,
        description="Article summary (max 1000 characters)",
        example="This guide will help you get started with SallyBot and understand its core features."
    )
    category_id: Optional[str] = Field(
        None,
        description="Category ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    tag_names: List[str] = Field(
        default_factory=list,
        description="List of tag names",
        example=["getting-started", "tutorial", "basics"]
    )
    status: ArticleStatus = Field(
        ArticleStatus.DRAFT,
        description="Article status",
        example=ArticleStatus.DRAFT
    )
    visibility: ArticleVisibility = Field(
        ArticleVisibility.PUBLIC,
        description="Article visibility",
        example=ArticleVisibility.PUBLIC
    )
    
    @validator('title')
    def validate_title(cls, v):
        """Validate article title."""
        if not v.strip():
            raise ValueError('Title cannot be empty')
        
        # Remove extra whitespace
        title = ' '.join(v.strip().split())
        
        if len(title) < 1:
            raise ValueError('Title must be at least 1 character long')
        
        if len(title) > 200:
            raise ValueError('Title must be at most 200 characters long')
        
        return title
    
    @validator('content_markdown')
    def validate_content_markdown(cls, v):
        """Validate markdown content."""
        if not v.strip():
            raise ValueError('Content cannot be empty')
        
        # Remove extra whitespace
        content = ' '.join(v.strip().split())
        
        if len(content) < 10:
            raise ValueError('Content must be at least 10 characters long')
        
        if len(content) > 50000:
            raise ValueError('Content must be at most 50000 characters long')
        
        return content
    
    @validator('content_html')
    def validate_content_html(cls, v):
        """Validate HTML content."""
        if v is None:
            return v
        
        if len(v) > 100000:
            raise ValueError('HTML content must be at most 100000 characters long')
        
        return v
    
    @validator('summary')
    def validate_summary(cls, v):
        """Validate article summary."""
        if v is None:
            return v
        
        if len(v) > 1000:
            raise ValueError('Summary must be at most 1000 characters long')
        
        return v
    
    @validator('category_id')
    def validate_category_id(cls, v):
        """Validate category ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Category ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Category ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Category ID must contain only hexadecimal characters')
        
        return v
    
    @validator('tag_names')
    def validate_tag_names(cls, v):
        """Validate tag names."""
        if not v:
            return v
        
        if len(v) > 50:
            raise ValueError('Cannot assign more than 50 tags to an article')
        
        for tag_name in v:
            if not tag_name.strip():
                raise ValueError('Tag name cannot be empty')
            
            if len(tag_name) > 50:
                raise ValueError('Tag name must be at most 50 characters long')
            
            # Check for valid tag name characters
            if not tag_name.replace('-', '').replace('_', '').isalnum():
                raise ValueError('Tag name can only contain letters, numbers, hyphens, and underscores')
        
        return v


class ArticleUpdate(BaseModel):
    """Schema for article update."""
    
    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Article title (1-200 characters)",
        example="Getting Started with SallyBot"
    )
    content_markdown: Optional[str] = Field(
        None,
        min_length=10,
        max_length=50000,
        description="Article content in markdown format (10-50000 characters)",
        example="# Getting Started with SallyBot\n\nWelcome to SallyBot..."
    )
    content_html: Optional[str] = Field(
        None,
        max_length=100000,
        description="Article content in HTML format (max 100000 characters)",
        example="<h1>Getting Started with SallyBot</h1><p>Welcome to SallyBot...</p>"
    )
    summary: Optional[str] = Field(
        None,
        max_length=1000,
        description="Article summary (max 1000 characters)",
        example="This guide will help you get started with SallyBot and understand its core features."
    )
    category_id: Optional[str] = Field(
        None,
        description="Category ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    tag_names: Optional[List[str]] = Field(
        None,
        description="List of tag names",
        example=["getting-started", "tutorial", "basics"]
    )
    status: Optional[ArticleStatus] = Field(
        None,
        description="Article status",
        example=ArticleStatus.PUBLISHED
    )
    visibility: Optional[ArticleVisibility] = Field(
        None,
        description="Article visibility",
        example=ArticleVisibility.PUBLIC
    )
    
    @validator('title')
    def validate_title(cls, v):
        """Validate article title."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Title cannot be empty')
        
        # Remove extra whitespace
        title = ' '.join(v.strip().split())
        
        if len(title) < 1:
            raise ValueError('Title must be at least 1 character long')
        
        if len(title) > 200:
            raise ValueError('Title must be at most 200 characters long')
        
        return title
    
    @validator('content_markdown')
    def validate_content_markdown(cls, v):
        """Validate markdown content."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Content cannot be empty')
        
        # Remove extra whitespace
        content = ' '.join(v.strip().split())
        
        if len(content) < 10:
            raise ValueError('Content must be at least 10 characters long')
        
        if len(content) > 50000:
            raise ValueError('Content must be at most 50000 characters long')
        
        return content
    
    @validator('content_html')
    def validate_content_html(cls, v):
        """Validate HTML content."""
        if v is None:
            return v
        
        if len(v) > 100000:
            raise ValueError('HTML content must be at most 100000 characters long')
        
        return v
    
    @validator('summary')
    def validate_summary(cls, v):
        """Validate article summary."""
        if v is None:
            return v
        
        if len(v) > 1000:
            raise ValueError('Summary must be at most 1000 characters long')
        
        return v
    
    @validator('category_id')
    def validate_category_id(cls, v):
        """Validate category ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Category ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Category ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Category ID must contain only hexadecimal characters')
        
        return v
    
    @validator('tag_names')
    def validate_tag_names(cls, v):
        """Validate tag names."""
        if v is None:
            return v
        
        if not v:
            return v
        
        if len(v) > 50:
            raise ValueError('Cannot assign more than 50 tags to an article')
        
        for tag_name in v:
            if not tag_name.strip():
                raise ValueError('Tag name cannot be empty')
            
            if len(tag_name) > 50:
                raise ValueError('Tag name must be at most 50 characters long')
            
            # Check for valid tag name characters
            if not tag_name.replace('-', '').replace('_', '').isalnum():
                raise ValueError('Tag name can only contain letters, numbers, hyphens, and underscores')
        
        return v


class ArticleCategoryResponse(BaseModel):
    """Schema for article category response with color."""
    
    id: str = Field(..., description="Category ID", example="60c72b2f9b1d8e001f8e4cde")
    name: str = Field(..., description="Category name", example="Getting Started")
    slug: str = Field(..., description="Category slug", example="getting-started")
    color: Optional[str] = Field(None, description="Category color in hex format", example="#4CAF50")


class ArticleResponse(BaseModel):
    """Schema for article response."""
    
    id: str = Field(..., description="Article ID", example="60c72b2f9b1d8e001f8e4cde")
    title: str = Field(..., description="Article title", example="Getting Started with SallyBot")
    content_html: str = Field(..., description="Article content in HTML", example="<h1>Getting Started with SallyBot</h1>...")
    content_markdown: str = Field(..., description="Article content in markdown", example="# Getting Started with SallyBot\n...")
    summary: Optional[str] = Field(None, description="Article summary", example="This guide will help you get started...")
    category: Optional[ArticleCategoryResponse] = Field(None, description="Article category")
    tags: List[Any] = Field(default_factory=list, description="Article tags")
    status: ArticleStatus = Field(..., description="Article status", example=ArticleStatus.PUBLISHED)
    visibility: ArticleVisibility = Field(..., description="Article visibility", example=ArticleVisibility.PUBLIC)
    created_at: datetime = Field(..., description="Article creation timestamp")
    updated_at: datetime = Field(..., description="Article update timestamp")
    author_id: str = Field(..., description="Author ID", example="60c72b2f9b1d8e001f8e4cde")
    view_count: int = Field(0, description="View count", example=150)
    like_count: int = Field(0, description="Like count", example=25)
    markdown_tree: Optional[MarkdownTreeResponse] = Field(None, description="Markdown tree structure")


class ArticleSearchRequest(BaseModel):
    """Schema for article search request."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query (1-200 characters)",
        example="getting started"
    )
    category_id: Optional[str] = Field(
        None,
        description="Category ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    tag_names: Optional[List[str]] = Field(
        None,
        description="List of tag names",
        example=["tutorial", "basics"]
    )
    status: Optional[ArticleStatus] = Field(
        None,
        description="Article status",
        example=ArticleStatus.PUBLISHED
    )
    visibility: Optional[ArticleVisibility] = Field(
        None,
        description="Article visibility",
        example=ArticleVisibility.PUBLIC
    )
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Number of results to return (1-100)",
        example=10
    )
    offset: int = Field(
        0,
        ge=0,
        description="Offset for pagination",
        example=0
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
    
    @validator('category_id')
    def validate_category_id(cls, v):
        """Validate category ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Category ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Category ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Category ID must contain only hexadecimal characters')
        
        return v
    
    @validator('tag_names')
    def validate_tag_names(cls, v):
        """Validate tag names."""
        if v is None:
            return v
        
        if not v:
            return v
        
        if len(v) > 10:
            raise ValueError('Cannot search for more than 10 tags at once')
        
        for tag_name in v:
            if not tag_name.strip():
                raise ValueError('Tag name cannot be empty')
            
            if len(tag_name) > 50:
                raise ValueError('Tag name must be at most 50 characters long')
        
        return v


class ArticleSearchResponse(BaseModel):
    """Schema for article search response."""
    
    articles: List[ArticleResponse] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Search query", example="getting started")
    limit: int = Field(..., description="Number of results returned", example=10)
    offset: int = Field(..., description="Offset used", example=0)


class ArticleStatsResponse(BaseModel):
    """Schema for article statistics response."""
    
    total_articles: int = Field(..., description="Total number of articles", example=150)
    published_articles: int = Field(..., description="Number of published articles", example=120)
    draft_articles: int = Field(..., description="Number of draft articles", example=25)
    archived_articles: int = Field(..., description="Number of archived articles", example=5)
    total_views: int = Field(..., description="Total view count", example=15000)
    total_likes: int = Field(..., description="Total like count", example=2500)
    top_categories: List[Dict[str, Any]] = Field(..., description="Top categories", example=[{"name": "Getting Started", "count": 25}, {"name": "Advanced", "count": 15}])
    top_tags: List[Dict[str, Any]] = Field(..., description="Top tags", example=[{"name": "tutorial", "count": 45}, {"name": "guide", "count": 32}])
    recent_articles: List[ArticleResponse] = Field(..., description="Recent articles", example=[])


class ArticleRatingRequest(BaseModel):
    """Schema for article rating request."""
    
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating (1-5 stars)",
        example=4
    )
    
    @validator('rating')
    def validate_rating(cls, v):
        """Validate rating value."""
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class ArticleRatingResponse(BaseModel):
    """Schema for article rating response."""
    
    article_id: str = Field(..., description="Article ID", example="60c72b2f9b1d8e001f8e4cde")
    rating: int = Field(..., description="Rating (1-5 stars)", example=4)
    created_at: datetime = Field(..., description="Rating creation timestamp")


class ArticleViewRequest(BaseModel):
    """Schema for article view request."""
    
    article_id: str = Field(..., description="Article ID", example="60c72b2f9b1d8e001f8e4cde")
    
    @validator('article_id')
    def validate_article_id(cls, v):
        """Validate article ID format."""
        if not v.strip():
            raise ValueError('Article ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Article ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Article ID must contain only hexadecimal characters')
        
        return v


class ArticleViewResponse(BaseModel):
    """Schema for article view response."""
    
    article_id: str = Field(..., description="Article ID", example="60c72b2f9b1d8e001f8e4cde")
    view_count: int = Field(..., description="Updated view count", example=151)
    created_at: datetime = Field(..., description="View creation timestamp")


class ArticleBulkActionRequest(BaseModel):
    """Schema for article bulk action request."""
    
    article_ids: List[str] = Field(..., description="List of article IDs", example=["60c72b2f9b1d8e001f8e4cde", "60c72b2f9b1d8e001f8e4cdf"])
    action: str = Field(..., description="Action to perform", example="publish")
    
    @validator('article_ids')
    def validate_article_ids(cls, v):
        """Validate article IDs format."""
        if not v:
            raise ValueError('At least one article ID is required')
        
        if len(v) > 100:
            raise ValueError('Cannot perform bulk action on more than 100 articles')
        
        for article_id in v:
            if not article_id.strip():
                raise ValueError('Article ID cannot be empty')
            
            # Basic ObjectId format validation
            if len(article_id) != 24:
                raise ValueError(f'Invalid article ID format: {article_id}')
            
            # Check for valid hex characters
            if not all(c in '0123456789abcdefABCDEF' for c in article_id):
                raise ValueError(f'Article ID must contain only hexadecimal characters: {article_id}')
        
        return v
    
    @validator('action')
    def validate_action(cls, v):
        """Validate action value."""
        valid_actions = ['publish', 'archive', 'delete', 'move_to_category']
        if v not in valid_actions:
            raise ValueError(f'Invalid action. Must be one of: {", ".join(valid_actions)}')
        return v


class ArticleBulkActionResponse(BaseModel):
    """Schema for article bulk action response."""
    
    success_count: int = Field(..., description="Number of successful actions", example=5)
    failure_count: int = Field(..., description="Number of failed actions", example=1)
    errors: List[str] = Field(default_factory=list, description="Error messages", example=["Article not found: 60c72b2f9b1d8e001f8e4cde"])
    message: str = Field(..., description="Action result message", example="Bulk action completed with 5 successes and 1 failure")