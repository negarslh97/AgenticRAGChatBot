"""
System Routes - مسیرهای مربوط به نظارت بر سیستم
====================================================

این فایل شامل endpointهای نظارتی برای:
- بررسی وضعیت اتصالات
- نظارت بر مصرف منابع
- مشاهده آمار سیستم
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import psutil
import time
import asyncio
from typing import Dict, Any
from app.domain.entities import Admin
from app.core.permissions import get_current_admin
from app.core.logging_config import get_logger
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint for monitoring and deployment validation.
    """
    try:
        # Check database connections
        from app.infrastructure.database.mongodb import mongo_client
        
        # Test MongoDB connection
        await mongo_client.admin.command('ping')
        mongodb_status = "healthy"
    except Exception as e:
        mongodb_status = f"unhealthy: {str(e)}"
        logger.error(f"MongoDB health check failed: {e}")

    try:
        # Test Weaviate connection
        from app.core.config import settings
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.weaviate_url_loaded}/v1/.well-known/ready", timeout=10)
            weaviate_status = "healthy" if response.status_code == 200 else f"unhealthy: {response.status_code}"
    except Exception as e:
        weaviate_status = f"unhealthy: {str(e)}"
        logger.error(f"Weaviate health check failed: {e}")

    # System metrics
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        }
    except Exception as e:
        system_metrics = {"error": f"Could not retrieve system metrics: {str(e)}"}
        logger.error(f"System metrics collection failed: {e}")

    # Overall health status
    is_healthy = (
        mongodb_status == "healthy" and 
        weaviate_status == "healthy" and
        system_metrics.get("cpu_percent", 0) < 90 and
        system_metrics.get("memory_percent", 0) < 90
    )

    health_data = {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": time.time(),
        "services": {
            "mongodb": mongodb_status,
            "weaviate": weaviate_status,
            "backend": "healthy"
        },
        "system": system_metrics,
        "version": "2.0"
    }

    # Return appropriate HTTP status code
    status_code = 200 if is_healthy else 503
    return JSONResponse(content=health_data, status_code=status_code)

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get detailed system and application metrics.
    """
    try:
        # Application uptime (approximate)
        import os
        start_time = os.path.getctime(__file__)  # Using file creation time as proxy
        uptime_seconds = time.time() - start_time
        
        # Process information
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()

        # Network connections
        connections = len(psutil.net_connections())
        
        # Database stats (if available)
        db_stats = {}
        try:
            from app.infrastructure.database.mongodb import mongo_client
            db_stats = {
                "mongodb_connected": True,
                "mongodb_host": str(mongo_client.server_info().get('host', 'unknown'))
            }
        except Exception as e:
            db_stats = {"mongodb_connected": False, "error": str(e)}

        return {
            "timestamp": time.time(),
            "application": {
                "uptime_seconds": round(uptime_seconds, 2),
                "process_memory_mb": round(process_memory.rss / 1024 / 1024, 2),
                "process_cpu_percent": process_cpu,
                "active_connections": connections
            },
            "system": {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                "disk_percent": psutil.disk_usage('/').percent
            },
            "database": db_stats,
            "version": "2.0"
        }
        
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Error collecting metrics: {str(e)}")

@router.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """
    Kubernetes readiness probe endpoint.
    """
    try:
        # Check if essential services are ready
        checks = []
        
        # Database check
        try:
            from app.infrastructure.database.mongodb import mongo_client
            await mongo_client.admin.command('ping')
            checks.append("database:ready")
        except Exception as e:
            checks.append(f"database:not_ready:{str(e)}")
        
        # Weaviate check
        try:
            from app.core.config import settings
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.weaviate_url_loaded}/v1/.well-known/ready", timeout=5)
                if response.status_code == 200:
                    checks.append("weaviate:ready")
                else:
                    checks.append(f"weaviate:not_ready:{response.status_code}")
        except Exception as e:
            checks.append(f"weaviate:not_ready:{str(e)}")
        
        # All checks must pass
        not_ready = [check for check in checks if ":not_ready" in check]
        
        if not_ready:
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "checks": checks,
                    "timestamp": time.time()
                },
                status_code=503
            )
        
        return {
            "status": "ready",
            "checks": checks,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            },
            status_code=503
        )

@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint.
    """
    return {
        "status": "alive",
        "timestamp": time.time(),
        "message": "Application is running"
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


@router.get("/models")
async def get_available_models():
    """
    دریافت لیست مدل‌های موجود (عمومی)
    
    Returns:
        - models: لیست مدل‌های AI موجود با مشخصات کامل
        - categories: دسته‌بندی مدل‌ها
        - default_model: مدل پیش‌فرض
    """
    try:
        from app.infrastructure.model_factory import model_factory
        
        # Get all models from factory
        models_info = model_factory.list_models()
        
        # Enhance with frontend-compatible format
        enhanced_models = []
        for model in models_info:
            config = model.get('config', {})
            enhanced_model = {
                "id": model['name'],
                "name": model['name'].split('/')[-1].replace('-', ' ').title(),
                "provider": model['provider'].title(),
                "description": config.get('metadata', {}).get('description', 'مدل AI'),
                "category": config.get('metadata', {}).get('category', 'other'),
                "speed": config.get('metadata', {}).get('speed_ch_per_s', 'N/A'),
                "empty_chunks": config.get('metadata', {}).get('empty_chunks', 'N/A'),
                "max_tokens": model['max_tokens'],
                "temperature": model['temperature'],
                "supports_streaming": model['streaming'],
                "supports_json": model['json']
            }
            enhanced_models.append(enhanced_model)
        
        # Categorize models for frontend
        categories = {
            "fastest": [m for m in enhanced_models if m['category'] == 'fastest'],
            "free": [m for m in enhanced_models if m['category'] == 'free'],
            "openai": [m for m in enhanced_models if m['category'] == 'openai'],
            "heavy": [m for m in enhanced_models if m['category'] == 'heavy'],
            "ollama": [m for m in enhanced_models if m['category'] == 'ollama'],
            "other": [m for m in enhanced_models if m['category'] not in ['fastest', 'free', 'openai', 'heavy', 'ollama']]
        }
        
        return {
            "status": "success",
            "data": {
                "models": enhanced_models,
                "categories": categories,
                "default_model": "google/gemini-2.5-flash",
                "total_count": len(enhanced_models)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail=str(e))



