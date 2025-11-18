"""
Admin Management Schemas
========================

Enhanced Pydantic schemas for admin and permission management.
Includes comprehensive validation rules and custom validators.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class PermissionDetailResponse(BaseModel):
    """Schema for permission detail response."""
    
    id: str = Field(..., description="Permission ID", example="60c72b2f9b1d8e001f8e4cde")
    permission_key: str = Field(..., description="Permission key", example="MANAGE_ADMINS")
    permission_name: str = Field(..., description="Permission display name", example="Manage Admins")
    description: Optional[str] = Field(None, description="Permission description", example="Create, read, update, delete admin users")
    created_at: Optional[datetime] = Field(None, description="Permission creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Permission update timestamp")


class RoleResponse(BaseModel):
    """Schema for role response."""
    
    id: str = Field(..., description="Role ID", example="60c72b2f9b1d8e001f8e4cde")
    name: str = Field(..., description="Role name", example="SuperAdmin")
    description: Optional[str] = Field(None, description="Role description", example="Super administrator with full access")
    permissions: List[PermissionDetailResponse] = Field(default_factory=list, description="Role permissions")
    is_active: bool = Field(True, description="Role active status", example=True)
    created_at: Optional[datetime] = Field(None, description="Role creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Role update timestamp")


class RoleCreate(BaseModel):
    """Schema for role creation."""
    
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Role name (2-50 characters)",
        example="SuperAdmin"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Role description (max 500 characters)",
        example="Super administrator with full access"
    )
    permission_ids: List[str] = Field(
        default_factory=list,
        description="List of permission IDs",
        example=["60c72b2f9b1d8e001f8e4cde", "60c72b2f9b1d8e001f8e4cdf"]
    )
    is_active: bool = Field(True, description="Role active status", example=True)
    
    @validator('name')
    def validate_role_name(cls, v):
        """Validate role name format."""
        if not v.strip():
            raise ValueError('Role name cannot be empty or whitespace only')
        
        # Remove extra whitespace
        cleaned_name = ' '.join(v.strip().split())
        
        # Check for valid role name characters
        if not cleaned_name.replace(' ', '').replace('-', '').isalnum():
            raise ValueError('Role name can only contain letters, numbers, spaces, and hyphens')
        
        # Check for common role name patterns
        if cleaned_name.lower() in ['admin', 'administrator', 'superadmin', 'root', 'system']:
            raise ValueError('Role name conflicts with reserved system roles')
        
        return cleaned_name
    
    @validator('permission_ids')
    def validate_permission_ids(cls, v):
        """Validate permission IDs format."""
        if not v:
            raise ValueError('At least one permission ID is required')
        
        if len(v) > 100:
            raise ValueError('Cannot assign more than 100 permissions to a role')
        
        for permission_id in v:
            if not permission_id.strip():
                raise ValueError('Permission ID cannot be empty')
            
            # Basic ObjectId format validation
            if len(permission_id) != 24:
                raise ValueError(f'Invalid permission ID format: {permission_id}')
            
            # Check for valid hex characters
            if not all(c in '0123456789abcdefABCDEF' for c in permission_id):
                raise ValueError(f'Permission ID must contain only hexadecimal characters: {permission_id}')
        
        return v


class RoleUpdate(BaseModel):
    """Schema for role update."""
    
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="Role name (2-50 characters)",
        example="SuperAdmin"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Role description (max 500 characters)",
        example="Super administrator with full access"
    )
    permission_ids: Optional[List[str]] = Field(
        None,
        description="List of permission IDs",
        example=["60c72b2f9b1d8e001f8e4cde", "60c72b2f9b1d8e001f8e4cdf"]
    )
    is_active: Optional[bool] = Field(None, description="Role active status", example=True)
    
    @validator('name')
    def validate_role_name(cls, v):
        """Validate role name format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Role name cannot be empty or whitespace only')
        
        # Remove extra whitespace
        cleaned_name = ' '.join(v.strip().split())
        
        # Check for valid role name characters
        if not cleaned_name.replace(' ', '').replace('-', '').isalnum():
            raise ValueError('Role name can only contain letters, numbers, spaces, and hyphens')
        
        # Check for common role name patterns
        if cleaned_name.lower() in ['admin', 'administrator', 'superadmin', 'root', 'system']:
            raise ValueError('Role name conflicts with reserved system roles')
        
        return cleaned_name
    
    @validator('permission_ids')
    def validate_permission_ids(cls, v):
        """Validate permission IDs format."""
        if v is None:
            return v
        
        if not v:
            raise ValueError('At least one permission ID is required')
        
        if len(v) > 100:
            raise ValueError('Cannot assign more than 100 permissions to a role')
        
        for permission_id in v:
            if not permission_id.strip():
                raise ValueError('Permission ID cannot be empty')
            
            # Basic ObjectId format validation
            if len(permission_id) != 24:
                raise ValueError(f'Invalid permission ID format: {permission_id}')
            
            # Check for valid hex characters
            if not all(c in '0123456789abcdefABCDEF' for c in permission_id):
                raise ValueError(f'Permission ID must contain only hexadecimal characters: {permission_id}')
        
        return v


class RoleInadminResponse(BaseModel):
    """Schema for role in admin response."""
    
    id: str = Field(..., description="Role ID", example="60c72b2f9b1d8e001f8e4cde")
    name: str = Field(..., description="Role name", example="SuperAdmin")
    description: Optional[str] = Field(None, description="Role description", example="Super administrator with full access")


class adminUserResponse(BaseModel):
    """Schema for admin user response."""
    
    id: str = Field(..., description="Admin user ID", example="60c72b2f9b1d8e001f8e4cde")
    email: str = Field(..., description="Admin user email", example="admin@example.com")
    full_name: str = Field(..., description="Admin user full name", example="Admin User")
    role: RoleInadminResponse = Field(..., description="Admin user role")
    is_active: bool = Field(..., description="Admin user active status", example=True)
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: Optional[datetime] = Field(None, description="Admin user creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Admin user update timestamp")


class adminUserCreate(BaseModel):
    """Schema for admin user creation."""
    
    email: str = Field(
        ...,
        description="Admin user email address",
        example="admin@example.com"
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Admin user full name (2-100 characters)",
        example="Admin User"
    )
    role_id: str = Field(
        ...,
        description="Role ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="Admin user password (8-128 characters)",
        example="SecureAdminPassword123!"
    )
    is_active: bool = Field(True, description="Admin user active status", example=True)
    
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
        
        # Remove extra whitespace
        return ' '.join(v.strip().split())
    
    @validator('role_id')
    def validate_role_id(cls, v):
        """Validate role ID format."""
        if not v.strip():
            raise ValueError('Role ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Role ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Role ID must contain only hexadecimal characters')
        
        return v
    
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


class adminUserUpdate(BaseModel):
    """Schema for admin user update."""
    
    email: Optional[str] = Field(
        None,
        description="Admin user email address",
        example="admin@example.com"
    )
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Admin user full name (2-100 characters)",
        example="Admin User"
    )
    role_id: Optional[str] = Field(
        None,
        description="Role ID (ObjectId as string)",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="Admin user password (8-128 characters)",
        example="SecureAdminPassword123!"
    )
    is_active: Optional[bool] = Field(None, description="Admin user active status", example=True)
    
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
    
    @validator('role_id')
    def validate_role_id(cls, v):
        """Validate role ID format."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Role ID cannot be empty')
        
        # Basic ObjectId format validation
        if len(v) != 24:
            raise ValueError('Role ID must be a valid 24-character ObjectId')
        
        # Check for valid hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in v):
            raise ValueError('Role ID must contain only hexadecimal characters')
        
        return v
    
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


class AdminListResponse(BaseModel):
    """Schema for admin list response."""
    
    admins: List[adminUserResponse] = Field(..., description="List of admin users")
    total: int = Field(..., description="Total number of admin users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")


class AdminStatsResponse(BaseModel):
    """Schema for admin statistics response."""
    
    total_admins: int = Field(..., description="Total number of admin users")
    active_admins: int = Field(..., description="Number of active admin users")
    inactive_admins: int = Field(..., description="Number of inactive admin users")
    roles_count: int = Field(..., description="Number of roles")
    permissions_count: int = Field(..., description="Number of permissions")
    recent_admins: List[adminUserResponse] = Field(default_factory=list, description="Recently created admins")


class AdminActivityLogResponse(BaseModel):
    """Schema for admin activity log response."""
    
    id: str = Field(..., description="Activity log ID", example="60c72b2f9b1d8e001f8e4cde")
    admin_id: str = Field(..., description="Admin user ID", example="60c72b2f9b1d8e001f8e4cde")
    action: str = Field(..., description="Action performed", example="create_admin")
    resource_type: str = Field(..., description="Resource type", example="admin")
    resource_id: Optional[str] = Field(None, description="Resource ID", example="60c72b2f9b1d8e001f8e4cde")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details", example={"created_admin_email": "admin@example.com"})
    ip_address: Optional[str] = Field(None, description="IP address", example="192.168.1.1")
    user_agent: Optional[str] = Field(None, description="User agent", example="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    created_at: Optional[datetime] = Field(None, description="Activity timestamp")


class AdminActivityLogListResponse(BaseModel):
    """Schema for admin activity log list response."""
    
    activities: List[AdminActivityLogResponse] = Field(..., description="List of activity logs")
    total: int = Field(..., description="Total number of activity logs")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")