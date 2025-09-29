"""
Database infrastructure package.

This package contains all database-related functionality including:
- MongoDB connection and operations
- Weaviate vector database operations
"""

from .mongodb import *
from .weaviate import WeaviateMongoDBConnector

__all__ = [
    # MongoDB functions
    "init_db",
    "close_mongo_client",
    "get_mongo_client",
    "create_default_SuperAdmin",
    "verify_database_setup",
    "get_database_stats",

    # Weaviate connector
    "WeaviateMongoDBConnector",
]
