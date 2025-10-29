"""
Validation Helper Functions
===========================

Centralized validation functions to eliminate code duplication (DRY principle).
Provides reusable validators for common validation patterns.
"""

import re
import json
from typing import Any, Dict, List, Optional, Type, Union
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel, validator
from enum import Enum


# Password strength validation
def validate_password_strength(password: str) -> bool:
    """
    Validate password strength according to security requirements.
    
    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    - No spaces
    """
    if not password or len(password) < 8:
        return False
    
    if ' ' in password:
        return False
    
    if not re.search(r'[A-Z]', password):
        return False
    
    if not re.search(r'[a-z]', password):
        return False
    
    if not re.search(r'\d', password):
        return False
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        return False
    
    return True


def validate_password_strength_or_raise(password: str, field_name: str = "password") -> str:
    """Validate password strength and raise ValueError if invalid."""
    if not validate_password_strength(password):
        raise ValueError(
            f"{field_name} must be at least 8 characters long and contain "
            "at least one uppercase letter, one lowercase letter, "
            "one digit, and one special character. No spaces allowed."
        )
    return password


# ObjectId validation
def validate_object_id(object_id_str: str, field_name: str = "ID") -> str:
    """Validate that the string is a valid ObjectId."""
    if not object_id_str:
        raise ValueError(f"{field_name} is required")
    
    try:
        ObjectId(object_id_str)
    except (InvalidId, TypeError):
        raise ValueError(f"{field_name} must be a valid ObjectId")
    
    return object_id_str


def validate_optional_object_id(object_id_str: Optional[str], field_name: str = "ID") -> Optional[str]:
    """Validate ObjectId if provided."""
    if object_id_str is None:
        return None
    return validate_object_id(object_id_str, field_name)


# Email validation
def validate_email(email: str) -> str:
    """Validate email format."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValueError("Invalid email format")
    
    return email.lower().strip()


# Name validation
def validate_name(name: str, field_name: str = "name", min_length: int = 2, max_length: int = 100) -> str:
    """Validate name fields."""
    if not name or not name.strip():
        raise ValueError(f"{field_name} is required")
    
    name = name.strip()
    
    if len(name) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters long")
    
    if len(name) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters long")
    
    # Allow letters, spaces, hyphens, and some special characters
    if not re.match(r'^[a-zA-Z\s\-\'\.]+$', name):
        raise ValueError(f"{field_name} contains invalid characters")
    
    return name


# Content validation
def validate_content(content: str, field_name: str = "content", min_length: int = 1, max_length: int = 10000) -> str:
    """Validate content fields like descriptions, messages, etc."""
    if not content or not content.strip():
        raise ValueError(f"{field_name} is required")
    
    content = content.strip()
    
    if len(content) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters long")
    
    if len(content) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters long")
    
    return content


# Title validation
def validate_title(title: str, min_length: int = 1, max_length: int = 200) -> str:
    """Validate title fields."""
    if not title or not title.strip():
        raise ValueError("Title is required")
    
    title = title.strip()
    
    if len(title) < min_length:
        raise ValueError("Title must be at least {min_length} characters long")
    
    if len(title) > max_length:
        raise ValueError("Title must be at most {max_length} characters long")
    
    return title


# Date validation
def validate_date_range(start_date: datetime, end_date: Optional[datetime] = None) -> tuple:
    """Validate date ranges."""
    if start_date > datetime.utcnow():
        raise ValueError("Start date cannot be in the future")
    
    if end_date and start_date >= end_date:
        raise ValueError("End date must be after start date")
    
    if end_date and end_date > datetime.utcnow():
        raise ValueError("End date cannot be in the future")
    
    return start_date, end_date


# JSON validation
def validate_json_string(json_str: str, field_name: str = "JSON") -> Dict[str, Any]:
    """Validate and parse JSON string."""
    if not json_str or not json_str.strip():
        return {}
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"{field_name} contains invalid JSON: {str(e)}")


def validate_optional_json_string(json_str: Optional[str], field_name: str = "JSON") -> Optional[Dict[str, Any]]:
    """Validate JSON string if provided."""
    if json_str is None:
        return None
    return validate_json_string(json_str, field_name)


# List validation
def validate_list_items(items: List[str], min_items: int = 0, max_items: int = 100, min_length: int = 1, max_length: int = 100) -> List[str]:
    """Validate list of strings."""
    if not isinstance(items, list):
        raise ValueError("Items must be a list")
    
    if len(items) < min_items:
        raise ValueError(f"List must contain at least {min_items} items")
    
    if len(items) > max_items:
        raise ValueError(f"List cannot contain more than {max_items} items")
    
    validated_items = []
    for i, item in enumerate(items):
        if not isinstance(item, str):
            raise ValueError(f"Item at index {i} must be a string")
        
        item = item.strip()
        if len(item) < min_length:
            raise ValueError(f"Item at index {i} must be at least {min_length} characters long")
        
        if len(item) > max_length:
            raise ValueError(f"Item at index {i} must be at most {max_length} characters long")
        
        validated_items.append(item)
    
    return validated_items


# URL validation
def validate_url(url: str, field_name: str = "URL") -> str:
    """Validate URL format."""
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    
    if not re.match(url_pattern, url):
        raise ValueError(f"{field_name} must be a valid HTTP or HTTPS URL")
    
    return url


def validate_optional_url(url: Optional[str], field_name: str = "URL") -> Optional[str]:
    """Validate URL if provided."""
    if url is None:
        return None
    return validate_url(url, field_name)


# Generic enum validation
def validate_enum_value(value: str, enum_class: Type[Enum], field_name: str = "value") -> str:
    """Validate that value is in the provided enum."""
    try:
        return enum_class(value).value
    except ValueError:
        valid_values = [e.value for e in enum_class]
        raise ValueError(f"{field_name} must be one of: {', '.join(valid_values)}")


def validate_optional_enum_value(value: Optional[str], enum_class: Type[Enum], field_name: str = "value") -> Optional[str]:
    """Validate enum value if provided."""
    if value is None:
        return None
    return validate_enum_value(value, enum_class, field_name)


# Slug validation
def validate_slug(slug: str) -> str:
    """Validate slug format (URL-friendly identifier)."""
    if not slug or not slug.strip():
        raise ValueError("Slug is required")
    
    slug = slug.strip().lower()
    
    # Only allow alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-z0-9\-_]+$', slug):
        raise ValueError("Slug can only contain lowercase letters, numbers, hyphens, and underscores")
    
    # Cannot start or end with hyphen or underscore
    if slug.startswith('-') or slug.startswith('_') or slug.endswith('-') or slug.endswith('_'):
        raise ValueError("Slug cannot start or end with hyphen or underscore")
    
    return slug


# Tag validation
def validate_tags(tags: List[str]) -> List[str]:
    """Validate list of tags."""
    validated_tags = []
    for tag in tags:
        # Remove special characters and normalize
        clean_tag = re.sub(r'[^a-zA-Z0-9\s\-]', '', tag).strip().lower()
        
        if clean_tag and len(clean_tag) >= 2 and len(clean_tag) <= 50:
            validated_tags.append(clean_tag)
    
    return list(set(validated_tags))  # Remove duplicates


# Phone number validation (basic)
def validate_phone_number(phone: str) -> str:
    """Validate phone number format (basic)."""
    # Remove all non-digits for validation
    digits_only = re.sub(r'\D', '', phone)
    
    if len(digits_only) < 10:
        raise ValueError("Phone number must contain at least 10 digits")
    
    if len(digits_only) > 15:
        raise ValueError("Phone number cannot contain more than 15 digits")
    
    # Format the phone number
    if len(digits_only) == 10:
        return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
    else:
        return f"+{digits_only[:-10]} {digits_only[-10:-7]} {digits_only[-7:-4]} {digits_only[-4:]}"


# Rate limiting validation
def validate_rate_limit_value(value: int, min_value: int = 1, max_value: int = 10000, field_name: str = "rate limit") -> int:
    """Validate rate limiting values."""
    if not isinstance(value, int) or value < min_value or value > max_value:
        raise ValueError(f"{field_name} must be an integer between {min_value} and {max_value}")
    return value


# Pagination validation
def validate_pagination_params(page: int, limit: int, max_limit: int = 100) -> tuple:
    """Validate pagination parameters."""
    if page < 1:
        raise ValueError("Page number must be greater than 0")
    
    if limit < 1:
        raise ValueError("Limit must be greater than 0")
    
    if limit > max_limit:
        raise ValueError(f"Limit cannot exceed {max_limit}")
    
    return page, limit


# Search query validation
def validate_search_query(query: str, max_length: int = 200) -> str:
    """Validate search query."""
    if not query or not query.strip():
        return ""
    
    query = query.strip()
    
    if len(query) > max_length:
        raise ValueError(f"Search query cannot exceed {max_length} characters")
    
    # Remove potentially dangerous characters
    query = re.sub(r'[<>"\';]', '', query)
    
    return query