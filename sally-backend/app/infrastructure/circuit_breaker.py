"""
Advanced circuit breaker pattern implementation with monitoring and recovery.
"""

import asyncio
import logging
import time
import threading
from typing import Dict, Any, Optional, Callable, List, TypeVar, Generic, Type

# Define TypeVar for the CircuitBreaker class
T = TypeVar('T')
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from datetime import datetime, timedelta
import weakref
import json

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"      # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if the service has recovered


class FailureCondition(str, Enum):
    """Conditions that trigger circuit breaker failure."""
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    ERROR_RATE = "error_rate"
    FAILURE_COUNT = "failure_count"
    CUSTOM = "custom"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Number of failures before opening circuit
    recovery_timeout: int = 60  # Seconds to wait before trying again
    timeout: int = 30  # Request timeout in seconds
    expected_exception: Optional[Type[Exception]] = Exception
    failure_conditions: List[FailureCondition] = field(default_factory=lambda: [FailureCondition.FAILURE_COUNT])
    error_rate_threshold: float = 0.5  # Error rate threshold (0.0 to 1.0)
    max_requests: int = 10  # Max requests allowed in half-open state
    rolling_window_size: int = 100  # Number of requests to consider for error rate
    monitor_interval: int = 10  # Seconds between health checks
    health_check_interval: int = 30  # Seconds between health checks
    enable_metrics: bool = True
    enable_logging: bool = True
    name: Optional[str] = None
    
    def __post_init__(self):
        if self.failure_threshold <= 0:
            raise ValueError("Failure threshold must be positive")
        if self.recovery_timeout <= 0:
            raise ValueError("Recovery timeout must be positive")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.error_rate_threshold <= 0 or self.error_rate_threshold > 1:
            raise ValueError("Error rate threshold must be between 0 and 1")
        if self.max_requests <= 0:
            raise ValueError("Max requests must be positive")
        if self.rolling_window_size <= 0:
            raise ValueError("Rolling window size must be positive")


@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker monitoring."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeouts: int = 0
    exceptions: int = 0
    error_rate: float = 0.0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    rolling_window: List[bool] = field(default_factory=list)  # True for success, False for failure
    
    def record_success(self):
        """Record a successful request."""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success_time = datetime.now()
        
        # Update rolling window
        self._update_rolling_window(True)
        
        # Update error rate
        self._update_error_rate()
    
    def record_failure(self, failure_type: FailureCondition):
        """Record a failed request."""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = datetime.now()
        
        # Update rolling window
        self._update_rolling_window(False)
        
        # Update error rate
        self._update_error_rate()
        
        # Track specific failure types
        if failure_type == FailureCondition.TIMEOUT:
            self.timeouts += 1
        elif failure_type == FailureCondition.EXCEPTION:
            self.exceptions += 1
    
    def _update_rolling_window(self, success: bool):
        """Update the rolling window of results."""
        self.rolling_window.append(success)
        if len(self.rolling_window) > 100:  # Keep window size manageable
            self.rolling_window.pop(0)
    
    def _update_error_rate(self):
        """Update the error rate based on rolling window."""
        if len(self.rolling_window) == 0:
            self.error_rate = 0.0
        else:
            failures = sum(1 for result in self.rolling_window if not result)
            self.error_rate = failures / len(self.rolling_window)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "timeouts": self.timeouts,
            "exceptions": self.exceptions,
            "error_rate": self.error_rate,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "rolling_window_size": len(self.rolling_window)
        }


class CircuitBreaker(Generic[TypeVar('T')]):
    """Advanced circuit breaker implementation."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self._stop_event = threading.Event()
        self.config = config
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self._lock = threading.RLock()
        self._last_state_change = datetime.now()
        self._half_open_requests = 0
        self._health_check_task = None
        
        # Start monitoring task
        if config.enable_metrics:
            self._start_monitoring_task()
        
        logger.info(f"Circuit breaker initialized: {config.name or 'unnamed'}")
    
    def _start_monitoring_task(self):
        """Start background monitoring task."""
        def monitoring_task():
            while not self._stop_event.wait(self.config.monitor_interval):
                try:
                    self._check_health()
                except Exception as e:
                    logger.error(f"Monitoring task error: {e}")
        
        self._health_check_task = threading.Thread(target=monitoring_task, daemon=True)
        self._health_check_task.start()
    
    def _check_health(self):
        """Check the health of the service."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                # Check if we should try to recover
                if datetime.now() - self._last_state_change >= timedelta(seconds=self.config.recovery_timeout):
                    logger.info(f"Circuit breaker health check: attempting recovery")
                    self.state = CircuitState.HALF_OPEN
                    self._half_open_requests = 0
                    self._last_state_change = datetime.now()
            
            elif self.state == CircuitState.HALF_OPEN:
                # Check if we should close the circuit
                if self.metrics.consecutive_successes >= self.config.max_requests:
                    logger.info(f"Circuit breaker health check: service recovered, closing circuit")
                    self.state = CircuitState.CLOSED
                    self._last_state_change = datetime.now()
                    self.metrics.consecutive_successes = 0
    
    def _should_open_circuit(self) -> bool:
        """Check if the circuit should be opened."""
        # Check failure count
        if (FailureCondition.FAILURE_COUNT in self.config.failure_conditions and
            self.metrics.consecutive_failures >= self.config.failure_threshold):
            return True
        
        # Check error rate
        if (FailureCondition.ERROR_RATE in self.config.failure_conditions and
            self.metrics.error_rate >= self.config.error_rate_threshold):
            return True
        
        return False
    
    def _should_allow_request(self) -> bool:
        """Check if a request should be allowed."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            elif self.state == CircuitState.OPEN:
                return False
            
            elif self.state == CircuitState.HALF_OPEN:
                # Allow limited requests in half-open state
                if self._half_open_requests < self.config.max_requests:
                    self._half_open_requests += 1
                    return True
                else:
                    return False
            
            return False
    
    def _record_success(self):
        """Record a successful request."""
        with self._lock:
            self.metrics.record_success()
            
            # Check if we should close the circuit
            if self.state == CircuitState.HALF_OPEN:
                if self.metrics.consecutive_successes >= self.config.max_requests:
                    self.state = CircuitState.CLOSED
                    self._last_state_change = datetime.now()
                    logger.info(f"Circuit breaker closed after {self.metrics.consecutive_successes} consecutive successes")
    
    def _record_failure(self, failure_type: FailureCondition):
        """Record a failed request."""
        with self._lock:
            self.metrics.record_failure(failure_type)
            
            # Check if we should open the circuit
            if self.state == CircuitState.CLOSED and self._should_open_circuit():
                self.state = CircuitState.OPEN
                self._last_state_change = datetime.now()
                logger.warning(f"Circuit breaker opened after {self.metrics.consecutive_failures} consecutive failures")
            
            elif self.state == CircuitState.HALF_OPEN:
                # Immediately open circuit if a request fails in half-open state
                self.state = CircuitState.OPEN
                self._last_state_change = datetime.now()
                logger.warning(f"Circuit breaker reopened after failure in half-open state")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        with self._lock:
            return {
                "state": self.state.value,
                "last_state_change": self._last_state_change.isoformat(),
                "half_open_requests": self._half_open_requests,
                "metrics": self.metrics.to_dict()
            }
    
    def get_metrics(self) -> CircuitMetrics:
        """Get circuit breaker metrics."""
        return self.metrics
    
    def reset(self):
        """Reset the circuit breaker."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.metrics = CircuitMetrics()
            self._half_open_requests = 0
            self._last_state_change = datetime.now()
            logger.info("Circuit breaker reset")
    
    def close(self):
        """Force close the circuit breaker."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self._last_state_change = datetime.now()
            logger.info("Circuit breaker force closed")
    
    def open(self):
        """Force open the circuit breaker."""
        with self._lock:
            self.state = CircuitState.OPEN
            self._last_state_change = datetime.now()
            logger.info("Circuit breaker force opened")
    
    def stop(self):
        """Stop the circuit breaker and cleanup resources."""
        self._stop_event.set()
        if self._health_check_task and self._health_check_task.is_alive():
            self._health_check_task.join(timeout=2)  # Wait for thread to finish
        logger.info(f"Circuit breaker stopped: {self.config.name or 'unnamed'}")
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator for circuit breaker protection."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.protect(func, *args, **kwargs)
        
        return wrapper
    
    async def __call_async__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Async decorator for circuit breaker protection."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.protect_async(func, *args, **kwargs)
        
        return wrapper
    
    def protect(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Protect a synchronous function call."""
        if not self._should_allow_request():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is {self.state.value}",
                self.state,
                self.metrics
            )
        
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Record success
            self._record_success()
            
            if self.config.enable_logging:
                logger.debug(f"Circuit breaker success: {func.__name__} ({execution_time:.2f}s)")
            
            return result
            
        except self.config.expected_exception as e:
            execution_time = time.time() - start_time
            self._record_failure(FailureCondition.EXCEPTION)
            
            if self.config.enable_logging:
                logger.warning(f"Circuit breaker exception: {func.__name__} - {e} ({execution_time:.2f}s)")
            
            raise
        
        except TimeoutError:
            execution_time = time.time() - start_time
            self._record_failure(FailureCondition.TIMEOUT)
            
            if self.config.enable_logging:
                logger.warning(f"Circuit breaker timeout: {func.__name__} ({execution_time:.2f}s)")
            
            raise
    
    async def protect_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Protect an asynchronous function call."""
        if not self._should_allow_request():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is {self.state.value}",
                self.state,
                self.metrics
            )
        
        try:
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Record success
            self._record_success()
            
            if self.config.enable_logging:
                logger.debug(f"Circuit breaker success: {func.__name__} ({execution_time:.2f}s)")
            
            return result
            
        except self.config.expected_exception as e:
            execution_time = time.time() - start_time
            self._record_failure(FailureCondition.EXCEPTION)
            
            if self.config.enable_logging:
                logger.warning(f"Circuit breaker exception: {func.__name__} - {e} ({execution_time:.2f}s)")
            
            raise
        
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self._record_failure(FailureCondition.TIMEOUT)
            
            if self.config.enable_logging:
                logger.warning(f"Circuit breaker timeout: {func.__name__} ({execution_time:.2f}s)")
            
            raise
    
    def __del__(self):
        """Cleanup when circuit breaker is destroyed."""
        self.stop()


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, message: str, state: CircuitState, metrics: CircuitMetrics):
        super().__init__(message)
        self.state = state
        self.metrics = metrics
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message": self.message,
            "state": self.state.value,
            "metrics": self.metrics.to_dict()
        }


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_circuit_breakers_lock = threading.RLock()


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    with _circuit_breakers_lock:
        if name not in _circuit_breakers:
            if config is None:
                config = CircuitBreakerConfig(name=name)
            _circuit_breakers[name] = CircuitBreaker(config)
        
        return _circuit_breakers[name]


def list_circuit_breakers() -> List[Dict[str, Any]]:
    """List all circuit breakers."""
    with _circuit_breakers_lock:
        return [
            {
                "name": name,
                "state": cb.get_state(),
                "config": cb.config.__dict__
            }
            for name, cb in _circuit_breakers.items()
        ]


def reset_circuit_breaker(name: str):
    """Reset a circuit breaker by name."""
    with _circuit_breakers_lock:
        if name in _circuit_breakers:
            _circuit_breakers[name].reset()


def reset_all_circuit_breakers():
    """Reset all circuit breakers."""
    with _circuit_breakers_lock:
        for cb in _circuit_breakers.values():
            cb.reset()


def stop_all_circuit_breakers():
    """Stop all circuit breakers and cleanup resources."""
    with _circuit_breakers_lock:
        for name, cb in _circuit_breakers.items():
            try:
                cb.stop()
            except Exception as e:
                logger.error(f"Error stopping circuit breaker {name}: {e}")


# Decorator functions for easy circuit breaker usage
def circuit_breaker_protect(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    timeout: int = 30,
    name: Optional[str] = None,
    **kwargs
):
    """Decorator to protect a function with circuit breaker."""
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        timeout=timeout,
        name=name,
        **kwargs
    )
    
    def decorator(func: Callable):
        cb = get_circuit_breaker(name or func.__name__, config)

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # برای متدهای کلاس، self به عنوان اولین آرگومان است
                return await cb.protect_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # برای متدهای کلاس، self به عنوان اولین آرگومان است
                return cb.protect(func, *args, **kwargs)
            return sync_wrapper

    return decorator

# Global circuit breaker instance for general use
default_circuit_breaker = CircuitBreaker(CircuitBreakerConfig())