"""
Common Enums
============

Centralized enumerations for validation across all API schemas.
Replaces string lists with proper enum types for better maintainability.
"""

from enum import Enum


class LogLevel(str, Enum):
    """System log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SystemComponent(str, Enum):
    """System components for logging and monitoring."""
    API = "api"
    DATABASE = "database"
    WEAVIATE = "weaviate"
    AUTH = "auth"
    CHAT = "chat"
    KB = "kb"
    SYSTEM = "system"


class DatabaseType(str, Enum):
    """Supported database types."""
    MONGODB = "mongodb"
    REDIS = "redis"
    WEAVIATE_DB = "weaviate"
    POSTGRES = "postgres"
    MYSQL = "mysql"


class AlertType(str, Enum):
    """System alert types."""
    HIGH_CPU_USAGE = "high_cpu_usage"
    HIGH_MEMORY_USAGE = "high_memory_usage"
    HIGH_DISK_USAGE = "high_disk_usage"
    DATABASE_ERROR = "database_error"
    WEAVIATE_ERROR = "weaviate_error"
    CONNECTION_TIMEOUT = "connection_timeout"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SystemTestType(str, Enum):
    """System diagnostic test types."""
    DATABASE = "database"
    WEAVIATE = "weaviate"
    API = "api"
    MEMORY = "memory"
    DISK = "disk"
    CPU = "cpu"
    NETWORK = "network"


class ConnectionStatus(str, Enum):
    """Connection status types."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TIMEOUT = "timeout"


class SystemStatus(str, Enum):
    """System status types."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class ArticleStatus(str, Enum):
    """Article publication status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    PENDING_REVIEW = "pending_review"


class ArticleVisibility(str, Enum):
    """Article visibility levels."""
    PUBLIC = "public"
    CUSTOMER = "customer"
    PRIVATE = "private"


class ConversationStatus(str, Enum):
    """Conversation status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    PENDING = "pending"


class MessageType(str, Enum):
    """Message types in conversations."""
    USER = "user"
    ADMIN = "admin"
    AI = "ai"
    SYSTEM = "system"


class RAGType(str, Enum):
    """RAG (Retrieval-Augmented Generation) types."""
    SIMPLE = "simple"
    DETAILED = "detailed"
    AGENTIC = "agentic"
    ADVANCED_AGENTIC = "advanced_agentic"


class ModelProvider(str, Enum):
    """AI model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


class RateLimitWindow(str, Enum):
    """Rate limiting time windows."""
    BURST = "burst"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class HTTPMethod(str, Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class ContentType(str, Enum):
    """Content types."""
    APPLICATION_JSON = "application/json"
    TEXT_PLAIN = "text/plain"
    TEXT_HTML = "text/html"
    MULTIPART_FORM_DATA = "multipart/form-data"
    APPLICATION_FORM_URLENCODED = "application/x-www-form-urlencoded"


class PermissionScope(str, Enum):
    """Permission scopes."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class FileType(str, Enum):
    """Supported file types."""
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    IMAGE = "image"


class TimeRange(str, Enum):
    """Time range options for queries."""
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


class NotificationType(str, Enum):
    """Notification types."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class UserType(str, Enum):
    """User types in the system."""
    CUSTOMER = "Customer"
    ADMIN = "Admin"
    SUPER_ADMIN = "SuperAdmin"
    GUEST = "Guest"


class ValidationRule(str, Enum):
    """Common validation rules."""
    REQUIRED = "required"
    OPTIONAL = "optional"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    PATTERN = "pattern"
    CUSTOM = "custom"


class APIErrorType(str, Enum):
    """API error types."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMIT = "RATE_LIMIT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"