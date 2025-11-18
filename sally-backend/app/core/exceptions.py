"""
Custom Exceptions for SallyBot
==============================

این فایل exception های سفارشی برای مدیریت بهتر خطاها در سراسر برنامه را تعریف می‌کند.
"""

from typing import Optional, Dict, Any


class SallyBotException(Exception):
    """Base exception class for SallyBot"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(SallyBotException):
    """Database-related errors"""
    pass


class WeaviateError(SallyBotException):
    """Weaviate-related errors"""
    pass


class RepositoryError(SallyBotException):
    """Repository layer errors"""
    pass


class ValidationError(SallyBotException):
    """Data validation errors"""
    pass


class AuthenticationError(SallyBotException):
    """Authentication and authorization errors"""
    pass


class ExternalServiceError(SallyBotException):
    """External service (OpenAI, etc.) errors"""
    pass


class SyncError(SallyBotException):
    """Data synchronization errors"""
    pass