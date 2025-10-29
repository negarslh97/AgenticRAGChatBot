"""
System Management Schemas
=========================

Enhanced Pydantic schemas for system monitoring and management.
Includes comprehensive validation rules and custom validators.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SystemStatus(str, Enum):
    """Enum for system status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ConnectionStatus(str, Enum):
    """Enum for connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TIMEOUT = "timeout"


class HealthResponse(BaseModel):
    """Schema for health check response."""
    
    status: SystemStatus = Field(..., description="Overall system status", example=SystemStatus.HEALTHY)
    service: str = Field(..., description="Service name", example="SallyBot API")
    version: str = Field(..., description="Service version", example="1.0.0")
    timestamp: datetime = Field(..., description="Health check timestamp")
    uptime: Optional[int] = Field(None, description="Uptime in seconds", example=86400)
    components: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Individual component status", example={
        "mongodb": {"status": "connected", "latency": 45},
        "weaviate": {"status": "connected", "latency": 120}
    })


class ResourceStatsResponse(BaseModel):
    """Schema for resource statistics response."""
    
    status: SystemStatus = Field(..., description="System status", example=SystemStatus.HEALTHY)
    data: Dict[str, Any] = Field(..., description="Resource statistics data")
    timestamp: datetime = Field(..., description="Statistics timestamp")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    has_warnings: bool = Field(..., description="Whether system has warnings", example=False)


class ConnectionStatsResponse(BaseModel):
    """Schema for connection statistics response."""
    
    status: SystemStatus = Field(..., description="Overall connection status", example=SystemStatus.HEALTHY)
    data: Dict[str, Any] = Field(..., description="Connection statistics data")
    timestamp: datetime = Field(..., description="Statistics timestamp")
    total_connections: int = Field(..., description="Total number of connections", example=15)
    active_connections: int = Field(..., description="Number of active connections", example=12)
    failed_connections: int = Field(..., description="Number of failed connections", example=0)
    average_latency: Optional[float] = Field(None, description="Average latency in milliseconds", example=85.5)
    max_latency: Optional[float] = Field(None, description="Maximum latency in milliseconds", example=250.0)
    min_latency: Optional[float] = Field(None, description="Minimum latency in milliseconds", example=25.0)


class MemoryUsageResponse(BaseModel):
    """Schema for memory usage response."""
    
    status: SystemStatus = Field(..., description="Memory status", example=SystemStatus.HEALTHY)
    data: Dict[str, Any] = Field(..., description="Memory usage data")
    timestamp: datetime = Field(..., description="Statistics timestamp")
    total_memory: int = Field(..., description="Total memory in bytes", example=8589934592)
    used_memory: int = Field(..., description="Used memory in bytes", example=4294967296)
    free_memory: int = Field(..., description="Free memory in bytes", example=4294967296)
    memory_usage_percentage: float = Field(..., description="Memory usage percentage", example=50.0)
    available_memory: int = Field(..., description="Available memory in bytes", example=3221225472)
    peak_memory_usage: Optional[int] = Field(None, description="Peak memory usage in bytes", example=5368709120)


class CPUUsageResponse(BaseModel):
    """Schema for CPU usage response."""
    
    status: SystemStatus = Field(..., description="CPU status", example=SystemStatus.HEALTHY)
    data: Dict[str, Any] = Field(..., description="CPU usage data")
    timestamp: datetime = Field(..., description="Statistics timestamp")
    cpu_usage_percentage: float = Field(..., description="CPU usage percentage", example=25.5)
    cpu_count: int = Field(..., description="Number of CPU cores", example=4)
    load_average: List[float] = Field(..., description="Load average (1, 5, 15 minutes)", example=[0.5, 0.3, 0.2])
    processes_count: int = Field(..., description="Number of running processes", example=150)


class DiskUsageResponse(BaseModel):
    """Schema for disk usage response."""
    
    status: SystemStatus = Field(..., description="Disk status", example=SystemStatus.HEALTHY)
    data: Dict[str, Any] = Field(..., description="Disk usage data")
    timestamp: datetime = Field(..., description="Statistics timestamp")
    total_space: int = Field(..., description="Total disk space in bytes", example=1073741824000)
    used_space: int = Field(..., description="Used disk space in bytes", example=536870912000)
    free_space: int = Field(..., description="Free disk space in bytes", example=536870912000)
    usage_percentage: float = Field(..., description="Disk usage percentage", example=50.0)
    available_space: int = Field(..., description="Available disk space in bytes", example=429496729600)
    mount_point: str = Field(..., description="Mount point", example="/")
    filesystem: str = Field(..., description="Filesystem type", example="ext4")


class CleanupResponse(BaseModel):
    """Schema for cleanup operation response."""
    
    status: str = Field(..., description="Operation status", example="success")
    message: str = Field(..., description="Operation result message", example="All connections cleaned up successfully")
    timestamp: datetime = Field(..., description="Operation timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional operation details")


class SystemMetricsRequest(BaseModel):
    """Schema for system metrics request."""
    
    start_time: Optional[datetime] = Field(
        None,
        description="Start time for metrics collection",
        example="2025-10-29T07:00:00Z"
    )
    end_time: Optional[datetime] = Field(
        None,
        description="End time for metrics collection",
        example="2025-10-29T07:30:00Z"
    )
    interval: Optional[str] = Field(
        "1m",
        description="Metrics interval",
        example="1m"
    )
    
    @validator('start_time')
    def validate_start_time(cls, v):
        """Validate start time."""
        if v is None:
            return v
        
        if v > datetime.now():
            raise ValueError('Start time cannot be in the future')
        
        return v
    
    @validator('end_time')
    def validate_end_time(cls, v):
        """Validate end time."""
        if v is None:
            return v
        
        if v > datetime.now():
            raise ValueError('End time cannot be in the future')
        
        return v
    
    @validator('interval')
    def validate_interval(cls, v):
        """Validate interval format."""
        if v is None:
            return v
        
        valid_intervals = ['1s', '1m', '5m', '15m', '1h', '1d']
        if v not in valid_intervals:
            raise ValueError(f'Invalid interval. Must be one of: {", ".join(valid_intervals)}')
        
        return v


class SystemMetricsResponse(BaseModel):
    """Schema for system metrics response."""
    
    timestamp: datetime = Field(..., description="Metrics timestamp")
    duration: str = Field(..., description="Metrics collection duration", example="30 minutes")
    interval: str = Field(..., description="Metrics interval", example="1m")
    data_points: List[Dict[str, Any]] = Field(..., description="Metrics data points", example=[
        {"timestamp": "2025-10-29T07:00:00Z", "cpu_usage": 25.5, "memory_usage": 50.0},
        {"timestamp": "2025-10-29T07:01:00Z", "cpu_usage": 30.2, "memory_usage": 52.5}
    ])
    summary: Dict[str, Any] = Field(..., description="Metrics summary statistics")


class DatabaseHealthCheckRequest(BaseModel):
    """Schema for database health check request."""
    
    database_type: str = Field(
        ...,
        description="Database type to check",
        example="mongodb"
    )
    connection_string: Optional[str] = Field(
        None,
        description="Database connection string",
        example="mongodb://localhost:27017/SallyChatBot"
    )
    timeout: Optional[int] = Field(
        30,
        ge=1,
        le=300,
        description="Connection timeout in seconds",
        example=30
    )
    
    @validator('database_type')
    def validate_database_type(cls, v):
        """Validate database type."""
        valid_types = ['mongodb', 'redis', 'weaviate', 'postgres', 'mysql']
        if v.lower() not in valid_types:
            raise ValueError(f'Invalid database type. Must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout value."""
        if v < 1:
            raise ValueError('Timeout must be at least 1 second')
        
        if v > 300:
            raise ValueError('Timeout cannot be more than 300 seconds')
        
        return v


class DatabaseHealthCheckResponse(BaseModel):
    """Schema for database health check response."""
    
    database_type: str = Field(..., description="Database type", example="mongodb")
    status: SystemStatus = Field(..., description="Database connection status", example=SystemStatus.HEALTHY)
    connection_string: Optional[str] = Field(None, description="Connection string (with password masked)")
    response_time: Optional[float] = Field(None, description="Response time in milliseconds", example=45.2)
    error_message: Optional[str] = Field(None, description="Error message if connection failed")
    timestamp: datetime = Field(..., description="Check timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional connection details")


class SystemLogRequest(BaseModel):
    """Schema for system log request."""
    
    level: Optional[str] = Field(
        None,
        description="Log level filter",
        example="ERROR"
    )
    component: Optional[str] = Field(
        None,
        description="Component filter",
        example="database"
    )
    start_time: Optional[datetime] = Field(
        None,
        description="Start time for log search"
    )
    end_time: Optional[datetime] = Field(
        None,
        description="End time for log search"
    )
    search_query: Optional[str] = Field(
        None,
        description="Search query for log content",
        example="connection failed"
    )
    limit: int = Field(
        100,
        ge=1,
        le=1000,
        description="Number of log entries to return (1-1000)",
        example=100
    )
    
    @validator('level')
    def validate_level(cls, v):
        """Validate log level."""
        if v is None:
            return v
        
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Invalid log level. Must be one of: {", ".join(valid_levels)}')
        return v.upper()
    
    @validator('component')
    def validate_component(cls, v):
        """Validate component."""
        if v is None:
            return v
        
        valid_components = ['api', 'database', 'weaviate', 'auth', 'chat', 'kb', 'system']
        if v.lower() not in valid_components:
            raise ValueError(f'Invalid component. Must be one of: {", ".join(valid_components)}')
        return v.lower()
    
    @validator('start_time')
    def validate_start_time(cls, v):
        """Validate start time."""
        if v is None:
            return v
        
        if v > datetime.now():
            raise ValueError('Start time cannot be in the future')
        
        return v
    
    @validator('end_time')
    def validate_end_time(cls, v):
        """Validate end time."""
        if v is None:
            return v
        
        if v > datetime.now():
            raise ValueError('End time cannot be in the future')
        
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        """Validate limit."""
        if v < 1 or v > 1000:
            raise ValueError('Limit must be between 1 and 1000')
        return v


class SystemLogResponse(BaseModel):
    """Schema for system log response."""
    
    logs: List[Dict[str, Any]] = Field(..., description="Log entries", example=[
        {
            "timestamp": "2025-10-29T07:00:00Z",
            "level": "ERROR",
            "component": "database",
            "message": "Connection failed to MongoDB",
            "request_id": "req_123456789"
        }
    ])
    total_count: int = Field(..., description="Total number of matching log entries", example=15)
    start_time: Optional[datetime] = Field(None, description="Search start time")
    end_time: Optional[datetime] = Field(None, description="Search end time")


class SystemConfigurationRequest(BaseModel):
    """Schema for system configuration request."""
    
    config_key: str = Field(
        ...,
        description="Configuration key to update",
        example="max_connections"
    )
    config_value: Any = Field(
        ...,
        description="Configuration value",
        example=100
    )
    description: Optional[str] = Field(
        None,
        description="Configuration change description",
        example="Increase maximum database connections"
    )
    
    @validator('config_key')
    def validate_config_key(cls, v):
        """Validate configuration key."""
        if not v.strip():
            raise ValueError('Configuration key cannot be empty')
        
        # Check for valid key format (alphanumeric, underscores, hyphens)
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Configuration key can only contain letters, numbers, hyphens, and underscores')
        
        return v.strip()


class SystemConfigurationResponse(BaseModel):
    """Schema for system configuration response."""
    
    config_key: str = Field(..., description="Configuration key", example="max_connections")
    config_value: Any = Field(..., description="Configuration value", example=100)
    previous_value: Optional[Any] = Field(None, description="Previous configuration value")
    description: Optional[str] = Field(None, description="Configuration description")
    timestamp: datetime = Field(..., description="Configuration update timestamp")
    updated_by: Optional[str] = Field(None, description="User who updated the configuration")


class SystemAlertRequest(BaseModel):
    """Schema for system alert request."""
    
    alert_type: str = Field(
        ...,
        description="Alert type",
        example="high_memory_usage"
    )
    severity: str = Field(
        ...,
        description="Alert severity",
        example="WARNING"
    )
    message: str = Field(
        ...,
        description="Alert message",
        example="Memory usage is above 80%"
    )
    component: Optional[str] = Field(
        None,
        description="Component causing the alert",
        example="system"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional alert metadata",
        example={"memory_usage": 85.5}
    )
    
    @validator('alert_type')
    def validate_alert_type(cls, v):
        """Validate alert type."""
        valid_types = ['high_cpu_usage', 'high_memory_usage', 'high_disk_usage', 'database_error', 'weaviate_error', 'connection_timeout']
        if v not in valid_types:
            raise ValueError(f'Invalid alert type. Must be one of: {", ".join(valid_types)}')
        return v
    
    @validator('severity')
    def validate_severity(cls, v):
        """Validate severity."""
        valid_severities = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_severities:
            raise ValueError(f'Invalid severity. Must be one of: {", ".join(valid_severities)}')
        return v.upper()
    
    @validator('component')
    def validate_component(cls, v):
        """Validate component."""
        if v is None:
            return v
        
        valid_components = ['api', 'database', 'weaviate', 'auth', 'chat', 'kb', 'system']
        if v.lower() not in valid_components:
            raise ValueError(f'Invalid component. Must be one of: {", ".join(valid_components)}')
        return v.lower()


class SystemAlertResponse(BaseModel):
    """Schema for system alert response."""
    
    alert_id: str = Field(..., description="Alert ID", example="60c72b2f9b1d8e001f8e4cde")
    alert_type: str = Field(..., description="Alert type", example="high_memory_usage")
    severity: str = Field(..., description="Alert severity", example="WARNING")
    message: str = Field(..., description="Alert message", example="Memory usage is above 80%")
    component: Optional[str] = Field(None, description="Component causing the alert", example="system")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional alert metadata")
    created_at: datetime = Field(..., description="Alert creation timestamp")
    status: str = Field(..., description="Alert status", example="active")


class SystemDiagnosticsRequest(BaseModel):
    """Schema for system diagnostics request."""
    
    test_types: List[str] = Field(
        ...,
        description="Types of tests to run",
        example=["database", "weaviate", "api"]
    )
    detailed_report: bool = Field(
        False,
        description="Whether to generate a detailed report",
        example=True
    )
    
    @validator('test_types')
    def validate_test_types(cls, v):
        """Validate test types."""
        if not v:
            raise ValueError('At least one test type is required')
        
        valid_types = ['database', 'weaviate', 'api', 'memory', 'disk', 'cpu', 'network']
        for test_type in v:
            if test_type not in valid_types:
                raise ValueError(f'Invalid test type: {test_type}. Must be one of: {", ".join(valid_types)}')
        
        return v


class SystemDiagnosticsResponse(BaseModel):
    """Schema for system diagnostics response."""
    
    diagnostics_id: str = Field(..., description="Diagnostics run ID", example="60c72b2f9b1d8e001f8e4cde")
    status: SystemStatus = Field(..., description="Overall diagnostics status", example=SystemStatus.HEALTHY)
    duration: float = Field(..., description="Diagnostics duration in seconds", example=45.2)
    tests_run: int = Field(..., description="Number of tests run", example=10)
    tests_passed: int = Field(..., description="Number of tests passed", example=9)
    tests_failed: int = Field(..., description="Number of tests failed", example=1)
    test_results: List[Dict[str, Any]] = Field(..., description="Individual test results", example=[
        {
            "test_name": "database_connection",
            "status": "PASSED",
            "duration": 0.5,
            "details": {"latency": 45.2, "connection_pool": 10}
        }
    ])
    recommendations: List[str] = Field(..., description="System recommendations", example=["Increase database connection pool size"])
    created_at: datetime = Field(..., description="Diagnostics timestamp")
