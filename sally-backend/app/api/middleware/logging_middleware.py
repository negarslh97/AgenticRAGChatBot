"""
Middleware برای logging همه درخواست‌ها و پاسخ‌ها در FastAPI
"""

import time
import uuid
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from app.core.logging_config import set_request_context, clear_request_context, get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware برای logging تمام درخواست‌ها و پاسخ‌ها
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details"""
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Extract user info from token if available
        user_id = None
        user_type = None
        
        try:
            # Try to extract user from Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # این اطلاعات می‌توانند از token استخراج شوند
                # برای سادگی فعلا از header استفاده می‌کنیم
                user_id = request.state.user_id if hasattr(request.state, 'user_id') else None
                user_type = request.state.user_type if hasattr(request.state, 'user_type') else None
        except Exception:
            pass
        
        # Set request context for logging
        set_request_context(request_id, user_id, user_type)
        
        # Add request_id to request state for use in routes
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        
        logger.info(
            f"🌐 Incoming Request",
            extra={
                'extra_data': {
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'query_params': dict(request.query_params),
                    'client_host': request.client.host if request.client else None,
                    'user_agent': request.headers.get('user-agent'),
                    'user_id': user_id,
                    'user_type': user_type
                }
            }
        )
        
        # Process request
        response = None
        error = None
        
        try:
            response = await call_next(request)
        except Exception as e:
            error = e
            logger.error(
                f"❌ Request failed with exception",
                exc_info=True,
                extra={
                    'extra_data': {
                        'request_id': request_id,
                        'method': request.method,
                        'path': request.url.path,
                        'error': str(e)
                    }
                }
            )
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            if response:
                status_code = response.status_code
                
                # Determine log level based on status code
                if status_code < 400:
                    log_level = logging.INFO
                    icon = "✅"
                elif status_code < 500:
                    log_level = logging.WARNING
                    icon = "⚠️"
                else:
                    log_level = logging.ERROR
                    icon = "❌"
                
                logger.log(
                    log_level,
                    f"{icon} Request completed",
                    extra={
                        'extra_data': {
                            'request_id': request_id,
                            'method': request.method,
                            'path': request.url.path,
                            'status_code': status_code,
                            'duration_ms': round(duration_ms, 2),
                            'user_id': user_id,
                            'user_type': user_type
                        }
                    }
                )
            
            # Clear request context
            clear_request_context()
        
        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware برای monitoring performance و slow queries
    """
    
    SLOW_REQUEST_THRESHOLD_MS = 1000  # 1 second
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.perf_logger = get_logger('performance')
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request performance"""
        
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log slow requests
        if duration_ms > self.SLOW_REQUEST_THRESHOLD_MS:
            self.perf_logger.warning(
                f"🐌 Slow request detected",
                extra={
                    'extra_data': {
                        'method': request.method,
                        'path': request.url.path,
                        'duration_ms': round(duration_ms, 2),
                        'threshold_ms': self.SLOW_REQUEST_THRESHOLD_MS,
                        'status_code': response.status_code
                    }
                }
            )
        
        # Add performance headers to response
        response.headers['X-Response-Time'] = f"{duration_ms:.2f}ms"
        
        if hasattr(request.state, 'request_id'):
            response.headers['X-Request-ID'] = request.state.request_id
        
        return response


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware برای catching و logging همه خطاهای unhandled
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Catch and log unhandled errors"""
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.exception(
                f"💥 Unhandled exception",
                extra={
                    'extra_data': {
                        'method': request.method,
                        'path': request.url.path,
                        'query_params': dict(request.query_params),
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                }
            )
            
            # Re-raise to let FastAPI handle it
            raise

