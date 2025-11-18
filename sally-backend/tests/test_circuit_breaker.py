"""
Tests for the circuit breaker implementation.
"""

import time
import threading
import pytest
from unittest.mock import patch, MagicMock

from app.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    get_circuit_breaker,
    stop_all_circuit_breakers
)


def test_circuit_breaker_stop():
    """Test that the stop() method properly stops the circuit breaker."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1,
        name="test_circuit_breaker"
    )
    
    # Create a circuit breaker
    cb = CircuitBreaker(config)
    
    # Verify the health check task is running
    assert cb._health_check_task is not None
    assert cb._health_check_task.is_alive()
    
    # Stop the circuit breaker
    cb.stop()
    
    # Verify the health check task is no longer running
    assert not cb._health_check_task.is_alive()
    assert cb._stop_event.is_set()


def test_circuit_breaker_stop_all():
    """Test that stop_all_circuit_breakers() properly stops all circuit breakers."""
    config1 = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1,
        name="test_circuit_breaker_1"
    )
    
    config2 = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1,
        name="test_circuit_breaker_2"
    )
    
    # Create two circuit breakers using the registry
    cb1 = get_circuit_breaker("test_circuit_breaker_1", config1)
    cb2 = get_circuit_breaker("test_circuit_breaker_2", config2)
    
    # Verify the health check tasks are running
    assert cb1._health_check_task is not None
    assert cb1._health_check_task.is_alive()
    assert cb2._health_check_task is not None
    assert cb2._health_check_task.is_alive()
    
    # Stop all circuit breakers
    stop_all_circuit_breakers()
    
    # Verify the health check tasks are no longer running
    assert not cb1._health_check_task.is_alive()
    assert not cb2._health_check_task.is_alive()
    assert cb1._stop_event.is_set()
    assert cb2._stop_event.is_set()


def test_circuit_breaker_stop_multiple_times():
    """Test that calling stop() multiple times doesn't cause issues."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1,
        name="test_circuit_breaker"
    )
    
    # Create a circuit breaker
    cb = CircuitBreaker(config)
    
    # Stop the circuit breaker multiple times
    cb.stop()
    cb.stop()
    cb.stop()
    
    # Verify the circuit breaker is still in a stopped state
    assert not cb._health_check_task.is_alive()
    assert cb._stop_event.is_set()


def test_circuit_breaker_cleanup_in_del():
    """Test that __del__ method calls stop()."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1,
        name="test_circuit_breaker"
    )
    
    # Create a circuit breaker
    cb = CircuitBreaker(config)
    
    # Mock the stop method to verify it's called
    cb.stop = MagicMock()
    
    # Delete the circuit breaker
    del cb
    
    # Note: In a real test scenario, we'd need to handle garbage collection
    # This test mainly verifies the method exists and can be called


def test_circuit_breaker_state_after_stop():
    """Test that circuit breaker state is properly maintained after stopping."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1,
        name="test_circuit_breaker"
    )
    
    # Create a circuit breaker
    cb = CircuitBreaker(config)
    
    # Change state to something other than CLOSED
    cb.open()
    assert cb.state == CircuitState.OPEN
    
    # Stop the circuit breaker
    cb.stop()
    
    # Verify state is maintained
    assert cb.state == CircuitState.OPEN
    assert cb._stop_event.is_set()


if __name__ == "__main__":
    test_circuit_breaker_stop()
    test_circuit_breaker_stop_all()
    test_circuit_breaker_stop_multiple_times()
    test_circuit_breaker_cleanup_in_del()
    test_circuit_breaker_state_after_stop()
    print("All tests passed!")