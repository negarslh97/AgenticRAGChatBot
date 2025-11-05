"""
Security Middleware
===================

Comprehensive security middleware for rate limiting and security headers.
Provides protection against common web vulnerabilities and API abuse.
"""

import time
import hashlib
import json
from typing import Dict, Optional, Set, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    
    requests_per_minute: int = Field(100, description="Requests per minute limit", example=100)
    requests_per_hour: int = Field(1000, description="Requests per hour limit", example=1000)
    requests_per_day: int = Field(10000, description="Requests per day limit", example=10000)
    burst_limit: int = Field(20, description="Maximum requests in a burst", example=20)
    window_seconds: int = Field(60, description="Burst window in seconds", example=60)
    
    def validate_limits(self) -> None:
        """Validate rate limit configuration."""
        if self.burst_limit > self.requests_per_minute:
            raise ValueError("Burst limit cannot exceed requests per minute")
        
        if self.requests_per_minute > self.requests_per_hour:
            raise ValueError("Requests per minute cannot exceed requests per hour")
        
        if self.requests_per_hour > self.requests_per_day:
            raise ValueError("Requests per hour cannot exceed requests per day")


class SecurityHeaders(BaseModel):
    """Security headers configuration."""
    
    enable_cors: bool = Field(True, description="Enable CORS headers")
    enable_hsts: bool = Field(True, description="Enable HSTS header")
    enable_content_security_policy: bool = Field(True, description="Enable CSP header")
    enable_x_frame_options: bool = Field(True, description="Enable X-Frame-Options header")
    enable_x_content_type_options: bool = Field(True, description="Enable X-Content-Type-Options header")
    enable_referrer_policy: bool = Field(True, description="Enable Referrer-Policy header")
    enable_permissions_policy: bool = Field(True, description="Enable Permissions-Policy header")
    
    # CORS configuration
    cors_origins: list = Field(["*"], description="Allowed CORS origins")
    cors_methods: list = Field(["GET", "POST", "PUT", "DELETE", "OPTIONS"], description="Allowed CORS methods")
    cors_headers: list = Field(["*"], description="Allowed CORS headers")
    cors_credentials: bool = Field(True, description="Allow CORS credentials")
    
    # CSP configuration
    csp_directives: Dict[str, str] = Field({
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline'",
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: https:",
        "font-src": "'self'",
        "connect-src": "'self' https:",
        "frame-ancestors": "'none'"
    }, description="Content Security Policy directives")
    
    # Rate limiting configuration
    rate_limit: RateLimitConfig = Field(RateLimitConfig(), description="Rate limiting configuration")


class RateLimiter:
    """In-memory rate limiter with sliding window."""
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.hits: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.blocked_ips: Dict[str, float] = {}
        self.block_duration = 3600  # 1 hour block duration
    
    def _generate_key(self, identifier: str, window: str) -> str:
        """Generate a unique key for rate limiting."""
        return f"{identifier}:{window}:{int(time.time() // self._get_window_seconds(window))}"
    
    def _get_window_seconds(self, window: str) -> int:
        """Get window duration in seconds."""
        windows = {
            "burst": 60,  # 1 minute
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        return windows.get(window, 60)
    
    def is_rate_limited(self, identifier: str, limit: int, window: str = "minute") -> Tuple[bool, Dict[str, int]]:
        """Check if identifier is rate limited."""
        
        # Check if IP is blocked
        if identifier in self.blocked_ips:
            if time.time() < self.blocked_ips[identifier]:
                return True, {"remaining": 0, "reset_time": self.blocked_ips[identifier]}
            else:
                # Unblock the IP
                del self.blocked_ips[identifier]
        
        current_time = time.time()
        window_seconds = self._get_window_seconds(window)
        
        # Clean old entries
        self._clean_old_entries(identifier, current_time, window_seconds)
        
        # Check rate limit
        request_times = self.requests[identifier]
        current_window_start = int(current_time // window_seconds)
        
        # Count requests in current window
        current_window_requests = sum(
            1 for timestamp in request_times
            if int(timestamp // window_seconds) == current_window_start
        )
        
        if current_window_requests >= limit:
            # Block the IP if it's consistently hitting limits
            if self._should_block_ip(identifier, current_time):
                self.blocked_ips[identifier] = current_time + self.block_duration
                logger.warning(f"IP {identifier} blocked for rate limit abuse", extra={
                    'ip': identifier,
                    'blocked_until': self.blocked_ips[identifier],
                    'reason': 'Rate limit exceeded'
                })
            
            return True, {"remaining": 0, "reset_time": (current_window_start + 1) * window_seconds}
        
        # Add current request
        request_times.append(current_time)
        
        remaining = max(0, limit - current_window_requests - 1)
        reset_time = (current_window_start + 1) * window_seconds
        
        return False, {"remaining": remaining, "reset_time": reset_time}
    
    def _should_block_ip(self, identifier: str, current_time: float) -> bool:
        """Determine if IP should be blocked based on pattern."""
        # Simple heuristic: block if multiple consecutive rate limit violations
        violation_count = self.hits[identifier].get("violations", 0)
        if violation_count >= 3:  # Block after 3 violations
            return True
        return False
    
    def record_violation(self, identifier: str) -> None:
        """Record a rate limit violation."""
        self.hits[identifier]["violations"] += 1
        logger.warning(f"Rate limit violation recorded for {identifier}", extra={
            'ip': identifier,
            'violations': self.hits[identifier]["violations"]
        })
    
    def _clean_old_entries(self, identifier: str, current_time: float, window_seconds: int) -> None:
        """Clean old entries from the queue."""
        request_times = self.requests[identifier]
        cutoff_time = current_time - (window_seconds * 2)  # Keep 2 windows worth of data
        
        while request_times and request_times[0] < cutoff_time:
            request_times.popleft()
    
    def reset_limits(self, identifier: str) -> None:
        """Reset rate limits for an identifier."""
        if identifier in self.requests:
            self.requests[identifier].clear()
        if identifier in self.hits:
            self.hits[identifier].clear()
        if identifier in self.blocked_ips:
            del self.blocked_ips[identifier]


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""
    
    def __init__(self, app, config: SecurityHeaders = None):
        super().__init__(app)
        self.config = config or SecurityHeaders()
        self.rate_limiter = RateLimiter()
        self.logger = logger
        
        # Paths that should be rate limited
        self.rate_limited_paths: Set[str] = {
            "/api/auth/",
            "/api/chat/",
            "/api/admin/",
            "/api/super-admin/"
        }
        
        # Paths that should have strict rate limiting
        self.strict_rate_limited_paths: Set[str] = {
            "/api/auth/login",
            "/api/auth/register"
        }
        
        # Paths that should bypass rate limiting (webhooks, health checks)
        self.bypass_rate_limiting: Set[str] = {
            "/health",
            "/api/system/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through security layers."""
        client_ip = self._get_client_ip(request)
        
        try:
            # 1. Rate limiting
            rate_limit_response = await self._check_rate_limit(request, client_ip)
            if rate_limit_response:
                return rate_limit_response
            
            # 2. Security headers
            response = await call_next(request)
            return self._add_security_headers(request, response)
            
        except Exception as e:
            self.logger.error(f"Security middleware error: {str(e)}", extra={
                'ip': client_ip,
                'path': str(request.url.path),
                'method': request.method,
                'exception': str(e)
            }, exc_info=True)
            
            # Return error response with security headers
            error_response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": "SECURITY_ERROR",
                    "message": "Security processing failed",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
            return self._add_security_headers(request, error_response)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def _check_rate_limit(self, request: Request, client_ip: str) -> Optional[Response]:
        """Check rate limiting for the request."""
        path = str(request.url.path)
        method = request.method
        
        # Skip rate limiting for certain paths
        if any(path.startswith(bypass_path) for bypass_path in self.bypass_rate_limiting):
            return None
        
        # Get rate limit configuration based on path
        rate_limit_config = self._get_rate_limit_config(path, method)
        
        # Check different time windows
        violations = []
        
        # Check burst limit (short-term)
        is_limited, burst_info = self.rate_limiter.is_rate_limited(
            f"{client_ip}:burst", 
            rate_limit_config.burst_limit, 
            "burst"
        )
        if is_limited:
            violations.append("burst")
            self.rate_limiter.record_violation(client_ip)
        
        # Check minute limit
        is_limited, minute_info = self.rate_limiter.is_rate_limited(
            f"{client_ip}:minute", 
            rate_limit_config.requests_per_minute, 
            "minute"
        )
        if is_limited:
            violations.append("minute")
            self.rate_limiter.record_violation(client_ip)
        
        # Check hour limit
        is_limited, hour_info = self.rate_limiter.is_rate_limited(
            f"{client_ip}:hour", 
            rate_limit_config.requests_per_hour, 
            "hour"
        )
        if is_limited:
            violations.append("hour")
            self.rate_limiter.record_violation(client_ip)
        
        # Check day limit
        is_limited, day_info = self.rate_limiter.is_rate_limited(
            f"{client_ip}:day", 
            rate_limit_config.requests_per_day, 
            "day"
        )
        if is_limited:
            violations.append("day")
            self.rate_limiter.record_violation(client_ip)
        
        # Return rate limit response if violated
        if violations:
            return self._create_rate_limit_response(request, client_ip, violations)
        
        # Add rate limit headers to response
        return None
    
    def _get_rate_limit_config(self, path: str, method: str) -> RateLimitConfig:
        """Get rate limit configuration for the path."""
        # Strict limits for authentication endpoints
        if any(path.startswith(strict_path) for strict_path in self.strict_rate_limited_paths):
            return RateLimitConfig(
                requests_per_minute=5,
                requests_per_hour=20,
                requests_per_day=100,
                burst_limit=3,
                window_seconds=60
            )
        
        # Normal limits for API endpoints
        if any(path.startswith(api_path) for api_path in self.rate_limited_paths):
            return self.config.rate_limit
        
        # Higher limits for public endpoints
        return RateLimitConfig(
            requests_per_minute=200,
            requests_per_hour=2000,
            requests_per_day=20000,
            burst_limit=30,
            window_seconds=60
        )
    
    def _create_rate_limit_response(self, request: Request, client_ip: str, violations: list) -> Response:
        """Create a rate limit response."""
        self.logger.warning(
            f"Rate limit exceeded for {client_ip} on {request.url.path}",
            extra={
                'ip': client_ip,
                'path': str(request.url.path),
                'method': request.method,
                'violations': violations,
                'user_agent': request.headers.get('User-Agent')
            }
        )
        
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded. Please try again later.",
                "violations": violations,
                "retry_after": 60,  # seconds
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = "100"
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        response.headers["Retry-After"] = "60"
        
        return response
    
    def _add_security_headers(self, request: Request, response: Response) -> Response:
        """Add security headers to the response."""
        
        # Content Security Policy
        if self.config.enable_content_security_policy:
            csp_value = "; ".join([f"{key} {value}" for key, value in self.config.csp_directives.items()])
            response.headers["Content-Security-Policy"] = csp_value
        
        # HTTP Strict Transport Security
        if self.config.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # X-Frame-Options
        if self.config.enable_x_frame_options:
            response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options
        if self.config.enable_x_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Referrer-Policy
        if self.config.enable_referrer_policy:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy
        if self.config.enable_permissions_policy:
            permissions_policy = (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=(), "
                "speaker=(self), vibrate=(), fullscreen=(self), "
                "sync-xhr=()"
            )
            response.headers["Permissions-Policy"] = permissions_policy
        
        # CORS headers
        if self.config.enable_cors:
            origin = request.headers.get("Origin")
            if origin and self._is_allowed_origin(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.config.cors_methods)
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.config.cors_headers)
                if self.config.cors_credentials:
                    response.headers["Access-Control-Allow-Credentials"] = "true"
        
        # Additional security headers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response
    
    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed for CORS."""
        if "*" in self.config.cors_origins:
            return True
        
        return origin in self.config.cors_origins


# Security configuration presets
SECURITY_PRESETS = {
    "development": SecurityHeaders(
        enable_hsts=False,
        enable_content_security_policy=False,
        cors_origins=["http://localhost:3000", "http://localhost:3001", "http://0.0.0.0:3000", "http://0.0.0.0:3001"],
        csp_directives={
            "default-src": "'self' 'unsafe-inline' 'unsafe-eval'",
            "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src": "'self' 'unsafe-inline'"
        }
    ),
    "production": SecurityHeaders(
        rate_limit=RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_limit=10,
            window_seconds=60
        ),
        cors_origins=["https://yourdomain.com"],
        csp_directives={
            "default-src": "'self'",
            "script-src": "'self'",
            "style-src": "'self' 'unsafe-inline'",
            "img-src": "'self' data: https:",
            "connect-src": "'self' https:",
            "frame-ancestors": "'none'"
        }
    )
}


def get_security_config(environment: str = "development") -> SecurityHeaders:
    """Get security configuration for the specified environment."""
    return SECURITY_PRESETS.get(environment, SECURITY_PRESETS["development"])