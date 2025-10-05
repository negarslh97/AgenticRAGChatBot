"""
System Routes - مسیرهای مربوط به نظارت بر سیستم
====================================================

این فایل شامل endpointهای نظارتی برای:
- بررسی وضعیت اتصالات
- نظارت بر مصرف منابع
- مشاهده آمار سیستم
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.domain.entities import Admin
from app.core.permissions import get_current_admin
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    بررسی سلامت سیستم (عمومی - بدون authentication)
    """
    return {
        "status": "healthy",
        "service": "SallyBot API",
        "version": "1.0.0"
    }


@router.get("/resources")
async def get_resource_stats(
    current_admin: Admin = Depends(get_current_admin)
):
    """
    دریافت آمار منابع سیستم (فقط Admin)
    
    Returns:
        - connection_stats: آمار اتصالات به دیتابیس‌ها
        - memory_usage: مصرف حافظه
        - warnings: هشدارها (اگر وجود داشته باشد)
    """
    try:
        from app.infrastructure.connection_manager import ResourceMonitor
        
        stats = ResourceMonitor.get_connection_stats()
        warnings = ResourceMonitor.check_thresholds()
        
        return {
            "status": "success",
            "data": {
                "connection_stats": stats,
                "warnings": warnings,
                "has_warnings": len(warnings) > 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting resource stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/weaviate")
async def get_weaviate_stats(
    current_admin: Admin = Depends(get_current_admin)
):
    """
    دریافت آمار اتصالات Weaviate (فقط Admin)
    """
    try:
        from app.infrastructure.connection_manager import WeaviateConnectionManager
        
        manager = WeaviateConnectionManager()
        stats = manager.get_stats()
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting Weaviate stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/mongodb")
async def get_mongodb_stats(
    current_admin: Admin = Depends(get_current_admin)
):
    """
    دریافت آمار اتصالات MongoDB (فقط Admin)
    """
    try:
        from app.infrastructure.connection_manager import MongoDBConnectionManager
        
        manager = MongoDBConnectionManager()
        stats = manager.get_stats()
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting MongoDB stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory")
async def get_memory_usage(
    current_admin: Admin = Depends(get_current_admin)
):
    """
    دریافت اطلاعات مصرف حافظه (فقط Admin)
    
    Requires: tracemalloc to be enabled
    """
    try:
        from app.infrastructure.connection_manager import ResourceMonitor
        
        memory_stats = ResourceMonitor.get_memory_usage()
        
        return {
            "status": "success",
            "data": memory_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting memory usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_connections(
    current_admin: Admin = Depends(get_current_admin)
):
    """
    پاک‌سازی دستی اتصالات (فقط Admin)
    
    ⚠️ Warning: این عملیات همه اتصالات فعال را می‌بندد
    """
    try:
        from app.infrastructure.connection_manager import cleanup_all_connections
        
        logger.warning(f"Manual cleanup initiated by admin: {current_admin.email}")
        cleanup_all_connections()
        
        return {
            "status": "success",
            "message": "All connections cleaned up successfully"
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))




