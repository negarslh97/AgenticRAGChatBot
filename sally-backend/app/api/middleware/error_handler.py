"""
Error Handling Middleware
=========================

Comprehensive error handling middleware for the SallyBot API.
Provides standardized error responses and consistent error handling across all endpoints.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError, BaseModel
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response model."""
    
    success: bool = False
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str
    request_id: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    status_code: int


class HTTPError:
    """Custom HTTP error classes with standardized messages."""
    
    # Authentication Errors
    AUTHENTICATION_REQUIRED = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials are required"
    )
    
    INVALID_CREDENTIALS = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password"
    )
    
    TOKEN_EXPIRED = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication token has expired"
    )
    
    TOKEN_INVALID = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token"
    )
    
    # Authorization Errors
    INSUFFICIENT_PERMISSIONS = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to access this resource"
    )
    
    ACCESS_DENIED = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied to this resource"
    )
    
    # Resource Errors
    RESOURCE_NOT_FOUND = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Requested resource was not found"
    )
    
    RESOURCE_ALREADY_EXISTS = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Resource already exists"
    )
    
    # Validation Errors
    INVALID_INPUT = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid input data provided"
    )
    
    MISSING_REQUIRED_FIELDS = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Required fields are missing"
    )
    
    # Database Errors
    DATABASE_CONNECTION_ERROR = HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database service is temporarily unavailable"
    )
    
    DATABASE_OPERATION_FAILED = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database operation failed"
    )
    
    # Service Errors
    SERVICE_UNAVAILABLE = HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Service is temporarily unavailable"
    )
    
    EXTERNAL_SERVICE_ERROR = HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="External service error occurred"
    )
    
    # System Errors
    INTERNAL_SERVER_ERROR = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error occurred"
    )
    
    BAD_REQUEST = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Bad request format"
    )
    
    METHOD_NOT_ALLOWED = HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="HTTP method not allowed"
    )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Comprehensive error handling middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Handle all requests and catch any errors."""
        request_id = self._generate_request_id()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            return await self._handle_http_exception(request, e, request_id)
            
        except RequestValidationError as e:
            return await self._handle_validation_error(request, e, request_id)
            
        except ValidationError as e:
            return await self._handle_pydantic_validation_error(request, e, request_id)
            
        except StarletteHTTPException as e:
            return await self._handle_starlette_http_exception(request, e, request_id)
            
        except ValueError as e:
            return await self._handle_value_error(request, e, request_id)
            
        except KeyError as e:
            return await self._handle_key_error(request, e, request_id)
            
        except TypeError as e:
            return await self._handle_type_error(request, e, request_id)
            
        except ConnectionError as e:
            return await self._handle_connection_error(request, e, request_id)
            
        except Exception as e:
            return await self._handle_unexpected_error(request, e, request_id)
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        import uuid
        return str(uuid.uuid4())
    
    async def _handle_http_exception(self, request: Request, e: HTTPException, request_id: str) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        error_response = ErrorResponse(
            success=False,
            error="HTTP_ERROR",
            message=e.detail,
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=e.status_code
        )
        
        self.logger.warning(
            f"HTTP Error: {e.status_code} - {e.detail}",
            extra={
                'request_id': request_id,
                'path': str(request.url.path),
                'method': request.method,
                'status_code': e.status_code,
                'client_ip': request.client.host if request.client else None
            }
        )
        
        return JSONResponse(
            status_code=e.status_code,
            content=error_response.dict()
        )
    
    async def _handle_validation_error(self, request: Request, e: RequestValidationError, request_id: str) -> JSONResponse:
        """Handle FastAPI request validation errors."""
        errors = []
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'] if x != 'body')
            errors.append({
                'field': field,
                'message': error['msg'],
                'type': error['type']
            })
        
        error_response = ErrorResponse(
            success=False,
            error="VALIDATION_ERROR",
            message="Request validation failed",
            details={
                'validation_errors': errors,
                'error_count': len(errors)
            },
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        
        self.logger.warning(
            f"Validation Error: {len(errors)} validation errors",
            extra={
                'request_id': request_id,
                'path': str(request.url.path),
                'method': request.method,
                'validation_errors': errors
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.dict()
        )
    
    async def _handle_pydantic_validation_error(self, request: Request, e: ValidationError, request_id: str) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = []
        for error in e.errors():
            field = '.'.join(str(x) for x in error['loc'] if x != 'body')
            errors.append({
                'field': field,
                'message': error['msg'],
                'type': error['type']
            })
        
        error_response = ErrorResponse(
            success=False,
            error="DATA_VALIDATION_ERROR",
            message="Data validation failed",
            details={
                'validation_errors': errors,
                'error_count': len(errors)
            },
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        self.logger.warning(
            f"Pydantic Validation Error: {len(errors)} validation errors",
            extra={
                'request_id': request_id,
                'path': str(request.url.path),
                'method': request.method,
                'validation_errors': errors
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.dict()
        )
    
    async def _handle_starlette_http_exception(self, request: Request, e: StarletteHTTPException, request_id: str) -> JSONResponse:
        """Handle Starlette HTTP exceptions."""
        error_response = ErrorResponse(
            success=False,
            error="HTTP_ERROR",
            message=e.detail,
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=e.status_code
        )
        
        self.logger.warning(
            f"Starlette HTTP Error: {e.status_code} - {e.detail}",
            extra={
                'request_id': request_id,
                'path': str(request.url.path),
                'method': request.method,
                'status_code': e.status_code
            }
        )
        
        return JSONResponse(
            status_code=e.status_code,
            content=error_response.dict()
        )
    
    async def _handle_value_error(self, request: Request, e: ValueError, request_id: str) -> JSONResponse:
        """Handle ValueError exceptions."""
        error_response = ErrorResponse(
            success=False,
            error="VALUE_ERROR",
            message=str(e),
            details={'exception_type': 'ValueError'},
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        self.logger.warning(
            f"Value Error: {str(e)}",
            extra={
                'request_id': request_id,
                'path': str(request.url.path),
                'method': request.method,
                'exception': str(e)
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.dict()
        )
    
    async def _handle_key_error(self, request: Request, e: KeyError, request_id: str) -> JSONResponse:
        """Handle KeyError exceptions."""
        error_response = ErrorResponse(
            success=False,
            error="KEY_ERROR",
            message=f"Required key not found: {str(e)}",
            details={'exception_type': 'KeyError', 'missing_key': str(e)},
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        self.logger.warning(
            f"Key Error: {str(e)}",
            extra={
                'request_id': request_id,
                'path': str(request.url.path),
                'method': request.method,
                'missing_key': str(e)
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.dict()
        )
    
    async def _handle_type_error(self, request: Request, e: TypeError, request_id: str) -> JSONResponse:
        """Handle TypeError exceptions."""
        error_response = ErrorResponse(
            success=False,
            error="TYPE_ERROR",
            message=str(e),
            details={'exception_type': 'TypeError'},
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        self.logger.warning(
            f"Type Error: {str(e)}",
            extra={
                'request_id': request_id,
                'path': str(request.url.path),
                'method': request.method,
                'exception': str(e)
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.dict()
        )
    
    async def _handle_connection_error(self, request: Request, e: ConnectionError, request_id: str) -> JSONResponse:
        """Handle ConnectionError exceptions."""
        error_response = ErrorResponse(
            success=False,
            error="CONNECTION_ERROR",
            message="Connection to external service failed",
            details={'exception_type': 'ConnectionError', 'original_error': str(e)},
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
        
        self.logger.error(
            f"Connection Error: {str(e)}",
            extra={
                'request_id': request_id,
                'path': str(request.url.path),
                'method': request.method,
                'exception': str(e)
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response.dict()
        )
    
    async def _handle_unexpected_error(self, request: Request, e: Exception, request_id: str) -> JSONResponse:
        """Handle unexpected exceptions."""
        error_response = ErrorResponse(
            success=False,
            error="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details={'exception_type': type(e).__name__},
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        # Get stack trace for debugging
        stack_trace = traceback.format_exc()
        
        self.logger.error(
            f"Unexpected Error: {type(e).__name__}: {str(e)}",
            extra={
                'request_id': request_id,
                'path': str(request.url.path),
                'method': request.method,
                'exception_type': type(e).__name__,
                'exception_message': str(e),
                'stack_trace': stack_trace
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.dict()
        )


def create_success_response(
    data: Any,
    message: str = "Success",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {
        'success': True,
        'message': message,
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if meta:
        response['meta'] = meta
    
    return response


def create_error_response(
    error: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400
) -> Dict[str, Any]:
    """Create a standardized error response."""
    response = {
        'success': False,
        'error': error,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'status_code': status_code
    }
    
    if details:
        response['details'] = details
    
    return response


class APIException(Exception):
    """Custom API exception for consistent error handling."""
    
    def __init__(
        self,
        error: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(f"{error}: {message}")


# Convenience functions for common error scenarios
def raise_not_found(resource: str = "Resource") -> None:
    """Raise a not found exception."""
    raise HTTPError.RESOURCE_NOT_FOUND


def raise_bad_request(message: str = "Bad request") -> None:
    """Raise a bad request exception."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )


def raise_unauthorized(message: str = "Authentication required") -> None:
    """Raise an unauthorized exception."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message
    )


def raise_forbidden(message: str = "Access denied") -> None:
    """Raise a forbidden exception."""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message
    )


def raise_validation_error(message: str = "Validation failed", details: Optional[Dict[str, Any]] = None) -> None:
    """Raise a validation error exception."""
    error_details = details or {}
    error_details['message'] = message
    raise APIException(
        error="VALIDATION_ERROR",
        message=message,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=error_details
    )


def raise_service_unavailable(message: str = "Service temporarily unavailable") -> None:
    """Raise a service unavailable exception."""
    raise HTTPError.SERVICE_UNAVAILABLE


def raise_database_error(message: str = "Database operation failed") -> None:
    """Raise a database error exception."""
    raise HTTPError.DATABASE_OPERATION_FAILED


def raise_external_service_error(message: str = "External service error") -> None:
    """Raise an external service error exception."""
    raise HTTPError.EXTERNAL_SERVICE_ERROR