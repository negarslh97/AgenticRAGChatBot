
"""
Advanced AI exception handling system with comprehensive error types and severity levels.
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import traceback
import json
from functools import wraps


logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Comprehensive error types for AI operations."""
    # Model-related errors
    MODEL_UNAVAILABLE = "model_unavailable"
    MODEL_TIMEOUT = "model_timeout"
    MODEL_RATE_LIMIT = "model_rate_limit"
    MODEL_INVALID_CONFIG = "model_invalid_config"
    MODEL_LOAD_FAILED = "model_load_failed"
    
    # Input/Output errors
    INVALID_INPUT = "invalid_input"
    INVALID_PROMPT = "invalid_prompt"
    OUTPUT_TRUNCATED = "output_truncated"
    OUTPUT_TOO_LONG = "output_too_long"
    OUTPUT_FORMAT_ERROR = "output_format_error"
    
    # Security errors
    PROMPT_INJECTION = "prompt_injection"
    SQL_INJECTION = "sql_injection"
    XSS_DETECTED = "xss_detected"
    SECURITY_VIOLATION = "security_violation"
    
    # Network/Connection errors
    NETWORK_ERROR = "network_error"
    CONNECTION_TIMEOUT = "connection_timeout"
    CONNECTION_FAILED = "connection_failed"
    API_UNAVAILABLE = "api_unavailable"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Authentication/Authorization errors
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHORIZATION_FAILED = "authorization_failed"
    INVALID_API_KEY = "invalid_api_key"
    TOKEN_EXPIRED = "token_expired"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    QUOTA_EXCEEDED = "quota_exceeded"
    
    # System errors
    INTERNAL_ERROR = "internal_error"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_ERROR = "dependency_error"
    TIMEOUT_ERROR = "timeout_error"


class AISeverity(str, Enum):
    """Severity levels for AI exceptions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: tuple = (Exception,)
    timeout: Optional[float] = None


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        """Call the wrapped function with circuit breaker protection."""
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise AIException(
                        message="Circuit breaker is open",
                        error_type=ErrorType.DEPENDENCY_ERROR,
                        severity=AISeverity.HIGH,
                        details={"state": self.state.value}
                    )
            
            try:
                if self.config.timeout:
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
                else:
                    result = await func(*args, **kwargs)
                
                await self._on_success()
                return result
                
            except self.config.expected_exception as e:
                await self._on_failure()
                raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    async def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Require 3 consecutive successes to close
                self.state = CircuitBreakerState.CLOSED
                logger.info("Circuit breaker closed after successful recovery")
    
    async def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker opened after failure in half-open state")
        elif self.state == CircuitBreakerState.CLOSED and self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def reset(self):
        """Reset the circuit breaker."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        logger.info("Circuit breaker manually reset")
    
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.state
    
    def get_failure_count(self) -> int:
        """Get current failure count."""
        return self.failure_count


@dataclass
class ErrorContext:
    """Context information for errors."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    model_name: Optional[str] = None
    operation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "model_name": self.model_name,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class AIException(Exception):
    """Advanced AI exception with comprehensive error information."""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        severity: AISeverity = AISeverity.MEDIUM,
        model_name: Optional[str] = None,
        operation: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        original_exception: Optional[Exception] = None,
        original_error: Optional[Exception] = None,  # For backward compatibility
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
        auto_recovery: bool = False,
        recovery_strategy: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.severity = severity
        self.model_name = model_name
        self.operation = operation
        self.user_id = user_id
        self.session_id = session_id
        self.request_id = request_id
        # Use original_error if provided, otherwise use original_exception
        self.original_exception = original_error or original_exception
        self.details = details or {}
        self.retry_after = retry_after
        self.auto_recovery = auto_recovery
        self.recovery_strategy = recovery_strategy
        self.timestamp = datetime.now()
        self.error_id = self._generate_error_id()
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        
        # Log the exception
        self._log_exception()
    
    def _generate_error_id(self) -> str:
        """Generate a unique error ID."""
        import hashlib
        import uuid
        
        unique_id = str(uuid.uuid4())
        content = f"{self.error_type.value}_{self.timestamp.isoformat()}_{unique_id}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _sanitize_sensitive_data(self, data: Any) -> Any:
        """Sanitize sensitive data from logs."""
        if isinstance(data, dict):
            sanitized = {}
            sensitive_keys = {
                'password', 'pwd', 'secret', 'token', 'key', 'api_key',
                'authorization', 'auth', 'credit_card', 'card_number',
                'ssn', 'social_security', 'passport', 'id_card',
                'private_key', 'access_token', 'refresh_token'
            }
            
            for key, value in data.items():
                if key.lower() in sensitive_keys:
                    sanitized[key] = "***REDACTED***"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_sensitive_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_sensitive_data(item) for item in data]
        else:
            return data
    
    def _log_exception(self):
        """Log the exception with appropriate level."""
        log_data = {
            "error_id": self.error_id,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "model_name": self.model_name,
            "operation": self.operation,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self._sanitize_sensitive_data(self.details),
            "retry_after": self.retry_after
        }
        
        if self.original_exception:
            log_data["original_exception"] = str(self.original_exception)
            log_data["traceback"] = traceback.format_exc()
        
        # Log based on severity
        if self.severity == AISeverity.CRITICAL:
            logger.critical(f"AI Exception: {json.dumps(log_data, ensure_ascii=False)}")
        elif self.severity == AISeverity.HIGH:
            logger.error(f"AI Exception: {json.dumps(log_data, ensure_ascii=False)}")
        elif self.severity == AISeverity.MEDIUM:
            logger.warning(f"AI Exception: {json.dumps(log_data, ensure_ascii=False)}")
        else:
            logger.info(f"AI Exception: {json.dumps(log_data, ensure_ascii=False)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error_id": self.error_id,
            "message": self.message,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "model_name": self.model_name,
            "operation": self.operation,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "retry_after": self.retry_after,
            "auto_recovery": self.auto_recovery,
            "recovery_strategy": self.recovery_strategy,
            "recovery_attempts": self.recovery_attempts,
            "max_recovery_attempts": self.max_recovery_attempts,
            "original_exception": str(self.original_exception) if self.original_exception else None
        }
    
    def to_json(self) -> str:
        """Convert exception to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def __str__(self) -> str:
        """String representation of the exception."""
        return f"AIException[{self.error_type.value}]: {self.message}"
    
    def can_recover(self) -> bool:
        """Check if the exception can be recovered."""
        return self.auto_recovery and self.recovery_attempts < self.max_recovery_attempts
    
    def increment_recovery_attempt(self):
        """Increment recovery attempt counter."""
        self.recovery_attempts += 1
    
    def get_recovery_delay(self) -> float:
        """Get recovery delay based on attempt count."""
        if self.retry_after:
            return float(self.retry_after)
        
        # Exponential backoff: 1s, 2s, 4s, 8s, etc.
        return min(2 ** self.recovery_attempts, 60)  # Max 60 seconds
    
    def should_retry(self) -> bool:
        """Check if the operation should be retried."""
        return self.can_recover() and self.recovery_attempts < self.max_recovery_attempts


class ModelUnavailableException(AIException):
    """Exception raised when a model is unavailable."""
    
    def __init__(self, model_name: str, message: Optional[str] = None, **kwargs):
        self.model_name = model_name
        super().__init__(
            message=message or f"Model {model_name} is currently unavailable",
            error_type=ErrorType.MODEL_UNAVAILABLE,
            severity=AISeverity.HIGH,
            model_name=model_name,
            **kwargs
        )


class RateLimitException(AIException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, retry_after: int, message: Optional[str] = None, **kwargs):
        super().__init__(
            message=message or f"Rate limit exceeded. Retry after {retry_after} seconds",
            error_type=ErrorType.RATE_LIMIT_EXCEEDED,
            severity=AISeverity.MEDIUM,
            retry_after=retry_after,
            **kwargs
        )


class AuthenticationException(AIException):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: Optional[str] = None, **kwargs):
        super().__init__(
            message=message or "Authentication failed",
            error_type=ErrorType.AUTHENTICATION_FAILED,
            severity=AISeverity.HIGH,
            **kwargs
        )


class SecurityException(AIException):
    """Exception raised for security violations."""
    
    def __init__(self, message: Optional[str] = None, **kwargs):
        super().__init__(
            message=message or "Security violation detected",
            error_type=ErrorType.SECURITY_VIOLATION,
            severity=AISeverity.CRITICAL,
            **kwargs
        )


class NetworkException(AIException):
    """Exception raised for network-related errors."""
    
    def __init__(self, message: Optional[str] = None, **kwargs):
        super().__init__(
            message=message or "Network error occurred",
            error_type=ErrorType.NETWORK_ERROR,
            severity=AISeverity.MEDIUM,
            auto_recovery=True,
            recovery_strategy="retry_with_backoff",
            **kwargs
        )


class ResourceException(AIException):
    """Exception raised for resource-related errors."""
    
    def __init__(self, resource_type: str, message: Optional[str] = None, **kwargs):
        super().__init__(
            message=message or f"Resource {resource_type} error occurred",
            error_type=ErrorType.RESOURCE_NOT_FOUND,
            severity=AISeverity.MEDIUM,
            **kwargs
        )


class RecoveryStrategy:
    """Base class for recovery strategies."""
    
    def __init__(self, name: str):
        self.name = name
    
    async def execute(self, exception: AIException, context: Dict[str, Any]) -> bool:
        """Execute the recovery strategy."""
        raise NotImplementedError


class RetryWithBackoffStrategy(RecoveryStrategy):
    """Strategy for retrying with exponential backoff."""
    
    def __init__(self, base_delay: float = 1.0):
        super().__init__("retry_with_backoff")
        self.base_delay = base_delay
    
    async def execute(self, exception: AIException, context: Dict[str, Any]) -> bool:
        """Retry with exponential backoff."""
        delay = exception.get_recovery_delay()
        logger.info(f"Retrying operation after {delay}s (attempt {exception.recovery_attempts})")
        
        await asyncio.sleep(delay)
        return True  # Assume retry will succeed


class FallbackModelStrategy(RecoveryStrategy):
    """Strategy for switching to fallback model."""
    
    def __init__(self, model_factory=None):
        super().__init__("fallback_model")
        self.model_factory = model_factory
    
    async def execute(self, exception: AIException, context: Dict[str, Any]) -> bool:
        """Switch to fallback model."""
        model_factory = context.get("model_factory") or self.model_factory
        if model_factory:
            try:
                # Get alternative model
                alternative_model = model_factory.get_optimal_model("chat")
                logger.info(f"Switched to fallback model: {alternative_model}")
                return True
            except Exception as e:
                logger.warning(f"Fallback model selection failed: {e}")
                return False
        return False


class CircuitBreakerResetStrategy(RecoveryStrategy):
    """Strategy for resetting circuit breaker."""
    
    def __init__(self):
        super().__init__("circuit_breaker_reset")
    
    async def execute(self, exception: AIException, context: Dict[str, Any]) -> bool:
        """Reset circuit breaker."""
        if "circuit_breaker" in context:
            circuit_breaker = context["circuit_breaker"]
            try:
                circuit_breaker.reset()
                logger.info("Circuit breaker reset successfully")
                return True
            except Exception as e:
                logger.warning(f"Circuit breaker reset failed: {e}")
                return False
        return False


class CacheRefreshStrategy(RecoveryStrategy):
    """Strategy for refreshing cache entries."""
    
    def __init__(self):
        super().__init__("cache_refresh")
    
    async def execute(self, exception: AIException, context: Dict[str, Any]) -> bool:
        """Refresh cache entries."""
        if "cache_manager" in context:
            cache_manager = context["cache_manager"]
            try:
                cache_manager.cleanup()
                logger.info("Cache refreshed successfully")
                return True
            except Exception as e:
                logger.warning(f"Cache refresh failed: {e}")
                return False
        return False


class RecoveryManager:
    """Manages auto-recovery for exceptions using Strategy Pattern."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, model_factory=None):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.model_factory = model_factory
        
        # Initialize strategies
        self.strategies = {
            "retry_with_backoff": RetryWithBackoffStrategy(base_delay),
            "fallback_model": FallbackModelStrategy(model_factory),
            "circuit_breaker_reset": CircuitBreakerResetStrategy(),
            "cache_refresh": CacheRefreshStrategy()
        }
    
    def can_recover(self, exception: AIException) -> bool:
        """Check if an exception can be recovered."""
        return exception.can_recover()
    
    async def recover(self, exception: AIException, context: Optional[Dict[str, Any]] = None) -> bool:
        """Attempt to recover from an exception."""
        if not self.can_recover(exception):
            return False
        
        exception.increment_recovery_attempt()
        
        if exception.recovery_strategy and exception.recovery_strategy in self.strategies:
            strategy = self.strategies[exception.recovery_strategy]
            try:
                return await strategy.execute(exception, context or {})
            except Exception as e:
                logger.warning(f"Recovery strategy {exception.recovery_strategy} failed: {e}")
                return False
        
        # Default retry with backoff
        return await self.strategies["retry_with_backoff"].execute(exception, context or {})
    
    def add_strategy(self, name: str, strategy: RecoveryStrategy):
        """Add a new recovery strategy."""
        self.strategies[name] = strategy
    
    def remove_strategy(self, name: str):
        """Remove a recovery strategy."""
        if name in self.strategies:
            del self.strategies[name]


# Global recovery manager instance
recovery_manager = RecoveryManager()


def with_auto_recovery(recovery_strategy: Optional[str] = None, max_attempts: Optional[int] = None):
    """Decorator for automatic exception recovery."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = kwargs.get("context", {})
            last_exception = None
            
            # Set max attempts
            attempts = max_attempts or recovery_manager.max_attempts
            
            for attempt in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except AIException as e:
                    last_exception = e
                    
                    if not e.should_retry():
                        raise
                    
                    # Add context to recovery attempt
                    recovery_context = context.copy()
                    recovery_context.update({
                        "function_name": func.__name__,
                        "attempt": attempt + 1,
                        "max_attempts": attempts
                    })
                    
                    # Attempt recovery
                    recovered = await recovery_manager.recover(e, recovery_context)
                    if not recovered:
                        raise
                    
                    # Wait before retry
                    delay = e.get_recovery_delay()
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    # Wrap non-AI exceptions
                    ai_exception = AIException(
                        message=str(e),
                        error_type=ErrorType.INTERNAL_ERROR,
                        severity=AISeverity.HIGH,
                        original_exception=e,
                        auto_recovery=True,
                        recovery_strategy=recovery_strategy or "retry_with_backoff"
                    )
                    last_exception = ai_exception
                    
                    if not ai_exception.should_retry():
                        raise
                    
                    # Add context to recovery attempt
                    recovery_context = context.copy()
                    recovery_context.update({
                        "function_name": func.__name__,
                        "attempt": attempt + 1,
                        "max_attempts": attempts
                    })
                    
                    # Attempt recovery
                    recovered = await recovery_manager.recover(ai_exception, recovery_context)
                    if not recovered:
                        raise
                    
                    # Wait before retry
                    delay = ai_exception.get_recovery_delay()
                    await asyncio.sleep(delay)
            
            # If we get here, all attempts failed
            if last_exception:
                raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, use a shared event loop to avoid creating new loops
            try:
                # Try to get existing event loop
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop exists, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(async_wrapper(*args, **kwargs))
                finally:
                    loop.close()
            else:
                # Event loop exists, run in it
                if loop.is_running():
                    # If loop is running, create a task and wait for it
                    import concurrent.futures
                    import threading
                    
                    # Run in a separate thread to avoid blocking the main loop
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(async_wrapper(*args, **kwargs))
                        )
                        return future.result()
                else:
                    # Loop exists but is not running, use it directly
                    return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        # Return appropriate wrapper based on function signature
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator