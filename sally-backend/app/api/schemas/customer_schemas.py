"""
Customer Management Schemas
===========================

Enhanced Pydantic schemas for customer management.
Includes comprehensive validation rules and custom validators.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class CustomerResponse(BaseModel):
    """Schema for customer response data."""
    
    id: str = Field(..., description="Customer ID", example="60c72b2f9b1d8e001f8e4cde")
    email: str = Field(..., description="Customer email", example="customer@example.com")
    full_name: str = Field(..., description="Customer full name", example="John Doe")
    is_active: bool = Field(..., description="Customer account status", example=True)
    created_at: Optional[datetime] = Field(None, description="Customer creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")


class CustomerCreate(BaseModel):
    """Schema for customer creation."""
    
    email: str = Field(
        ...,
        description="Customer email address",
        example="customer@example.com"
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Customer full name (2-100 characters)",
        example="John Doe"
    )
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="Customer password (8-128 characters)",
        example="SecurePassword123!"
    )
    is_active: bool = Field(True, description="Customer active status", example=True)
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if not v.strip():
            raise ValueError('Email cannot be empty')
        
        # Basic email format validation
        if '@' not in v:
            raise ValueError('Invalid email format')
        
        if '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        
        return v.strip()
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Validate full name format."""
        if not v.strip():
            raise ValueError('Full name cannot be empty or whitespace only')
        
        # Check for common name patterns
        if len(v.split()) < 2:
            raise ValueError('Full name should contain at least first and last name')
        
        # Remove extra whitespace
        return ' '.join(v.strip().split())
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength requirements."""
        if v is None:
            return v
        
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if len(v) > 128:
            raise ValueError('Password must be at most 128 characters long')
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for c in v):
            raise ValueError('Password must contain at least one special character')
        
        return v


class CustomerUpdate(BaseModel):
    """Schema for customer update."""
    
    email: Optional[str] = Field(
        None,
        description="Customer email address",
        example="customer@example.com"
    )
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Customer full name (2-100 characters)",
        example="John Doe"
    )
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="Customer password (8-128 characters)",
        example="SecurePassword123!"
    )
    is_active: Optional[bool] = Field(None, description="Customer active status", example=True)
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Email cannot be empty')
        
        # Basic email format validation
        if '@' not in v:
            raise ValueError('Invalid email format')
        
        if '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        
        return v.strip()
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Validate full name format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Full name cannot be empty or whitespace only')
        
        # Remove extra whitespace
        return ' '.join(v.strip().split())
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength requirements."""
        if v is None:
            return v
        
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if len(v) > 128:
            raise ValueError('Password must be at most 128 characters long')
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for c in v):
            raise ValueError('Password must contain at least one special character')
        
        return v


class CustomerListResponse(BaseModel):
    """Schema for customer list response."""
    
    customers: List[CustomerResponse] = Field(..., description="List of customers")
    total: int = Field(..., description="Total number of customers")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")


class CustomerStatsResponse(BaseModel):
    """Schema for customer statistics response."""
    
    total_customers: int = Field(..., description="Total number of customers")
    active_customers: int = Field(..., description="Number of active customers")
    inactive_customers: int = Field(..., description="Number of inactive customers")
    recent_customers: List[CustomerResponse] = Field(default_factory=list, description="Recently created customers")


class CustomerActivityLogResponse(BaseModel):
    """Schema for customer activity log response."""
    
    id: str = Field(..., description="Activity log ID", example="60c72b2f9b1d8e001f8e4cde")
    customer_id: str = Field(..., description="Customer ID", example="60c72b2f9b1d8e001f8e4cde")
    action: str = Field(..., description="Action performed", example="login")
    resource_type: str = Field(..., description="Resource type", example="customer")
    resource_id: Optional[str] = Field(None, description="Resource ID", example="60c72b2f9b1d8e001f8e4cde")
    details: Optional[dict] = Field(None, description="Additional details", example={"login_method": "email"})
    ip_address: Optional[str] = Field(None, description="IP address", example="192.168.1.1")
    user_agent: Optional[str] = Field(None, description="User agent", example="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    created_at: Optional[datetime] = Field(None, description="Activity timestamp")


class CustomerActivityLogListResponse(BaseModel):
    """Schema for customer activity log list response."""
    
    activities: List[CustomerActivityLogResponse] = Field(..., description="List of activity logs")
    total: int = Field(..., description="Total number of activity logs")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")


class CustomerProfileUpdate(BaseModel):
    """Schema for customer profile update."""
    
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Customer full name (2-100 characters)",
        example="John Doe"
    )
    email: Optional[str] = Field(
        None,
        description="Customer email address",
        example="customer@example.com"
    )
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Email cannot be empty')
        
        # Basic email format validation
        if '@' not in v:
            raise ValueError('Invalid email format')
        
        if '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        
        return v.strip()
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Validate full name format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Full name cannot be empty or whitespace only')
        
        # Remove extra whitespace
        return ' '.join(v.strip().split())


class CustomerPasswordChange(BaseModel):
    """Schema for customer password change."""
    
    current_password: str = Field(..., description="Current password", example="OldPassword123!")
    new_password: str = Field(..., description="New password", example="NewSecurePassword123!")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if len(v) > 128:
            raise ValueError('Password must be at most 128 characters long')
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for c in v):
            raise ValueError('Password must contain at least one special character')
        
        return v


class CustomerPasswordChangeResponse(BaseModel):
    """Schema for customer password change response."""
    
    message: str = Field(..., description="Password change message", example="Password changed successfully")


class CustomerDeactivateRequest(BaseModel):
    """Schema for customer deactivation request."""
    
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for deactivation",
        example="Customer requested account deactivation"
    )


class CustomerDeactivateResponse(BaseModel):
    """Schema for customer deactivation response."""
    
    message: str = Field(..., description="Deactivation message", example="Customer account deactivated successfully")


class CustomerReactivateRequest(BaseModel):
    """Schema for customer reactivation request."""
    
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for reactivation",
        example="Customer requested account reactivation"
    )


class CustomerReactivateResponse(BaseModel):
    """Schema for customer reactivation response."""
    
    message: str = Field(..., description="Reactivation message", example="Customer account reactivated successfully")