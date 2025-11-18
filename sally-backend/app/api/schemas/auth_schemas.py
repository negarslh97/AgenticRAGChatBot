"""Enhanced Authentication Schemas"""
from fastapi import Body, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, timedelta
from typing import Optional, List

from .validation_helpers import validate_password_strength_or_raise, validate_object_id
from .common_enums import UserType, APIErrorType


# Base schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name",
        example="علی احمدی"
    )
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="ali.ahmadi@example.com"
    )


# Registration schemas with improved validation
class CustomerRegister(UserBase):
    """Schema for customer registration."""
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (must meet complexity requirements)",
        example="SecurePass123!"
    )
    password_confirm: str = Field(
        ...,
        description="Password confirmation (must match password)",
        example="SecurePass123!"
    )
    
    # Use centralized password validation
    @validator('password')
    def validate_password(cls, password: str) -> str:
        return validate_password_strength_or_raise(password, "password")
    
    @validator('password_confirm')
    def validate_password_confirmation(cls, password_confirm: str, values: dict) -> str:
        password = values.get('password')
        if password and password_confirm != password:
            raise ValueError("Password confirmation must match password")
        return password_confirm


class CustomerRegisterRequest(BaseModel):
    """Schema for customer registration request."""
    customer_data: CustomerRegister = Field(
        ...,
        description="Customer registration data"
    )
    captcha_token: Optional[str] = Field(
        None,
        description="Captcha verification token"
    )
    privacy_accepted: bool = Field(
        True,
        description="User has accepted privacy policy"
    )
    terms_accepted: bool = Field(
        True,
        description="User has accepted terms of service"
    )


class AdminRegister(UserBase):
    """Schema for admin registration."""
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Admin password (must meet complexity requirements)",
        example="AdminSecure123!"
    )
    role_id: str = Field(
        ...,
        min_length=1,
        description="Admin role ObjectId",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    
    @validator('password')
    def validate_password(cls, password: str) -> str:
        return validate_password_strength_or_raise(password, "password")
    
    @validator('role_id')
    def validate_role_id(cls, role_id: str) -> str:
        return validate_object_id(role_id, "role_id")


class AdminRegisterRequest(BaseModel):
    """Schema for admin registration request."""
    admin_data: AdminRegister = Field(
        ...,
        description="Admin registration data"
    )


# Password management schemas
class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""
    
    current_password: str = Field(
        ...,
        description="Current password for verification",
        example="CurrentPass123!"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (must meet complexity requirements)",
        example="NewSecure123!"
    )
    new_password_confirm: str = Field(
        ...,
        description="New password confirmation (must match new password)",
        example="NewSecure123!"
    )
    
    @validator('new_password')
    def validate_new_password(cls, new_password: str) -> str:
        return validate_password_strength_or_raise(new_password, "new_password")
    
    @validator('new_password_confirm')
    def validate_new_password_confirmation(cls, new_password_confirm: str, values: dict) -> str:
        new_password = values.get('new_password')
        if new_password and new_password_confirm != new_password:
            raise ValueError("New password confirmation must match new password")
        return new_password_confirm


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    
    email: EmailStr = Field(
        ...,
        description="Email address for password reset",
        example="user@example.com"
    )
    captcha_token: Optional[str] = Field(
        None,
        description="Captcha verification token"
    )


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    
    token: str = Field(
        ...,
        description="Password reset token",
        example="reset_token_here"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (must meet complexity requirements)",
        example="NewSecure123!"
    )
    new_password_confirm: str = Field(
        ...,
        description="New password confirmation (must match new password)",
        example="NewSecure123!"
    )
    
    @validator('new_password')
    def validate_new_password(cls, new_password: str) -> str:
        return validate_password_strength_or_raise(new_password, "new_password")
    
    @validator('new_password_confirm')
    def validate_new_password_confirmation(cls, new_password_confirm: str, values: dict) -> str:
        new_password = values.get('new_password')
        if new_password and new_password_confirm != new_password:
            raise ValueError("New password confirmation must match new password")
        return new_password_confirm


# Response schemas with inheritance
class UserResponse(UserBase):
    """Schema for user response (base)."""
    id: str = Field(
        ...,
        description="User ID",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    is_active: bool = Field(
        ...,
        description="Whether the user account is active",
        example=True
    )
    created_at: datetime = Field(
        ...,
        description="User registration timestamp"
    )
    updated_at: datetime = Field(
        ...,
        description="User last update timestamp"
    )
    last_login: Optional[datetime] = Field(
        None,
        description="User last login timestamp"
    )
    is_verified: bool = Field(
        False,
        description="Whether the user email is verified"
    )

    class Config:
        from_attributes = True


class CustomerResponse(UserResponse):
    """Schema for customer response."""
    user_type: UserType = Field(
        UserType.CUSTOMER,
        description="User type",
        example=UserType.CUSTOMER
    )
    conversation_count: Optional[int] = Field(
        0,
        description="Number of conversations started by this customer",
        example=5
    )
    avg_satisfaction: Optional[float] = Field(
        None,
        ge=1.0,
        le=5.0,
        description="Average conversation satisfaction rating",
        example=4.2
    )

    class Config:
        from_attributes = True


class AdminResponse(UserResponse):
    """Schema for admin response."""
    
    role_id: str = Field(
        ...,
        description="Admin role ObjectId",
        example="60c72b2f9b1d8e001f8e4cde"
    )
    role_name: str = Field(
        ...,
        description="Admin role name",
        example="Admin"
    )
    user_type: UserType = Field(
        ...,
        description="User type",
        example=UserType.ADMIN
    )
    permissions: List[str] = Field(
        default_factory=list,
        description="List of admin permissions",
        example=["VIEW_CUSTOMERS", "CREATE_KB_ARTICLES"]
    )
    last_activity: Optional[datetime] = Field(
        None,
        description="Admin last activity timestamp"
    )

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str = Field(
        ...,
        description="JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        "bearer",
        description="Token type (bearer)",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds",
        example=2592000
    )


class UserLoginResponse(BaseModel):
    """Schema for login response with user information."""
    success: bool = Field(
        True,
        description="Login operation status",
        example=True
    )
    message: str = Field(
        "Login successful",
        description="Login response message",
        example="Login successful"
    )
    token: Token = Field(
        ...,
        description="Authentication token information"
    )
    user: UserResponse = Field(
        ...,
        description="User information"
    )
    user_type: UserType = Field(
        ...,
        description="User type (admin, customer, etc.)"
    )
    timestamp: datetime = Field(
        ...,
        description="Response timestamp"
    )

    class Config:
        from_attributes = True


class LogoutResponse(BaseModel):
    """Schema for logout response."""
    success: bool = Field(
        True,
        description="Logout operation status",
        example=True
    )
    message: str = Field(
        "Logout successful",
        description="Logout response message",
        example="Logout successful"
    )


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(
        ...,
        description="Valid refresh token",
        example="refresh_token_here"
    )


class RefreshTokenResponse(BaseModel):
    """Schema for token refresh response."""
    success: bool = Field(
        True,
        description="Token refresh status",
        example=True
    )
    message: str = Field(
        "Token refreshed successfully",
        description="Token refresh response message"
    )
    token: Token = Field(
        ...,
        description="New authentication token information"
    )


# Profile and preferences schemas
class UserProfileUpdate(BaseModel):
    """Schema for user profile update."""
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Updated user name"
    )
    phone: Optional[str] = Field(
        None,
        description="Updated phone number",
        example="+1-555-0123"
    )
    avatar_url: Optional[str] = Field(
        None,
        description="Updated avatar URL",
        example="https://example.com/avatar.jpg"
    )


class UserPreferences(BaseModel):
    """Schema for user preferences."""
    language: str = Field(
        "en",
        description="User preferred language",
        example="en"
    )
    theme: str = Field(
        "light",
        description="User preferred theme",
        example="light"
    )
    notifications_enabled: bool = Field(
        True,
        description="Whether notifications are enabled"
    )
    email_notifications: bool = Field(
        True,
        description="Whether email notifications are enabled"
    )


class UserInfoResponse(BaseModel):
    """Schema for complete user information response."""
    user: UserResponse = Field(
        ...,
        description="Basic user information"
    )
    preferences: Optional[UserPreferences] = Field(
        None,
        description="User preferences"
    )
    profile_data: Optional[UserProfileUpdate] = Field(
        None,
        description="Extended profile data"
    )


# Error response schemas using enums
class AuthenticationErrorResponse(BaseModel):
    """Schema for authentication error response."""
    success: bool = Field(
        False,
        description="Operation status",
        example=False
    )
    error: APIErrorType = Field(
        APIErrorType.AUTHENTICATION_ERROR,
        description="Error type",
        example=APIErrorType.AUTHENTICATION_ERROR
    )
    message: str = Field(
        ...,
        description="Error message",
        example="Invalid credentials"
    )
    details: Optional[dict] = Field(
        None,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        ...,
        description="Error timestamp"
    )


class AuthorizationErrorResponse(BaseModel):
    """Schema for authorization error response."""
    success: bool = Field(
        False,
        description="Operation status",
        example=False
    )
    error: APIErrorType = Field(
        APIErrorType.AUTHORIZATION_ERROR,
        description="Error type",
        example=APIErrorType.AUTHORIZATION_ERROR
    )
    message: str = Field(
        ...,
        description="Error message",
        example="Insufficient permissions"
    )
    required_permissions: Optional[List[str]] = Field(
        None,
        description="List of required permissions"
    )
    timestamp: datetime = Field(
        ...,
        description="Error timestamp"
    )


class ValidationErrorResponse(BaseModel):
    """Schema for validation error response."""
    success: bool = Field(
        False,
        description="Operation status",
        example=False
    )
    error: APIErrorType = Field(
        APIErrorType.VALIDATION_ERROR,
        description="Error type",
        example=APIErrorType.VALIDATION_ERROR
    )
    message: str = Field(
        ...,
        description="Error message",
        example="Validation failed"
    )
    validation_errors: List[dict] = Field(
        ...,
        description="List of validation errors",
        example=[
            {
                "field": "email",
                "message": "Invalid email format",
                "type": "value_error.email"
            }
        ]
    )
    timestamp: datetime = Field(
        ...,
        description="Error timestamp"
    )


# Advanced security schemas
class LoginAttempt(BaseModel):
    """Schema for tracking login attempts."""
    user_id: Optional[str] = Field(
        None,
        description="User ID (if successful)"
    )
    email: str = Field(
        ...,
        description="Attempted email"
    )
    ip_address: str = Field(
        ...,
        description="IP address of the attempt"
    )
    user_agent: Optional[str] = Field(
        None,
        description="User agent string"
    )
    success: bool = Field(
        ...,
        description="Whether login was successful"
    )
    failure_reason: Optional[str] = Field(
        None,
        description="Reason for failure (if any)"
    )


class AccountLockout(BaseModel):
    """Schema for account lockout information."""
    user_id: str = Field(
        ...,
        description="User ID"
    )
    locked_until: datetime = Field(
        ...,
        description="When the lockout expires"
    )
    failed_attempts: int = Field(
        ...,
        description="Number of failed attempts"
    )
    lockout_reason: str = Field(
        ...,
        description="Reason for lockout"
    )


class SecurityEvent(BaseModel):
    """Schema for security-related events."""
    user_id: Optional[str] = Field(
        None,
        description="User ID associated with the event"
    )
    event_type: str = Field(
        ...,
        description="Type of security event",
        example="login"
    )
    ip_address: str = Field(
        ...,
        description="IP address where event occurred"
    )
    user_agent: Optional[str] = Field(
        None,
        description="User agent string"
    )
    success: bool = Field(
        ...,
        description="Whether the event was successful"
    )
    details: Optional[dict] = Field(
        None,
        description="Additional event details"
    )
    timestamp: datetime = Field(
        ...,
        description="Event timestamp"
    )