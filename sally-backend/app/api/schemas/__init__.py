"""
API Schemas Module
=================

This module contains all Pydantic schemas for input validation across the SallyBot API.
Centralized schemas ensure consistent validation and error handling across all endpoints.
"""

from .auth_schemas import *
from .admin_schemas import *
from .customer_schemas import *
from .chat_schemas import *
from .knowledge_base_schemas import *
from .category_schemas import *
from .system_schemas import *

__all__ = [
    # Auth schemas
    'CustomerRegister',
    'AdminRegister', 
    'CustomerResponse',
    'AdminResponse',
    'Token',
    'UserLoginResponse',
    
    # Admin schemas
    'PermissionDetailResponse',
    'RoleResponse',
    'RoleCreate',
    'RoleUpdate',
    'RoleInadminResponse',
    'adminUserResponse',
    'adminUserCreate',
    'adminUserUpdate',
    
    # Customer schemas
    'CustomerResponse',
    'CustomerUpdate',
    
    # Chat schemas
    'ChatMessage',
    'ChatResponse',
    'ChatHistoryResponse',
    'MessageRating',
    'AdvancedAgenticRequest',
    'AdvancedAgenticResponse',
    
    # Knowledge Base schemas
    'ArticleCreate',
    'ArticleUpdate',
    'ArticleResponse',
    'MarkdownNodeResponse',
    'MarkdownTreeResponse',
    
    # Category schemas
    'CategoryBase',
    'CategoryCreate',
    'CategoryUpdate',
    'CategoryResponse',
    'CategoryTreeNode',
    'CategoryDeleteResult',
    
    # System schemas
    'HealthResponse',
    'ResourceStatsResponse',
    'ConnectionStatsResponse',
    'MemoryUsageResponse',
    'CleanupResponse'
]