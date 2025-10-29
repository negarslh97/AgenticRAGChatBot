from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
import os
import warnings

from app.core.config import settings
from app.infrastructure.database.mongodb import init_db

# Suppress specific deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*general_plain_validator_function.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*with_info_plain_validator_function.*")

# Initialize advanced logging system
from app.core.logging_config import setup_logging, get_logger
setup_logging(
    app_name="sallybot",
    log_level="INFO",
    log_dir="logs",
    enable_json=False,  # Set to True for production
    enable_console=True,
    enable_file=True
)
logger = get_logger(__name__)

# Import middleware
from app.api.middleware.logging_middleware import (
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    ErrorLoggingMiddleware
)
from app.api.middleware.error_handler import ErrorHandlerMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info("🚀 Starting up the application...")
    
    # Initialize connection managers
    from app.infrastructure.connection_manager import startup_connections
    await startup_connections()
    
    # Initialize database
    await init_db()

    # Log existing roles in database for debugging
    from app.domain.entities import Role
    existing_roles = await Role.find_all().to_list()
    logger.info(f"Existing roles in database: {[role.name for role in existing_roles]}")

    # Create default roles
    from app.core.permissions import create_default_roles, SUPER_ADMIN_ROLE_NAME
    await create_default_roles()

    # Log roles after creation
    roles_after = await Role.find_all().to_list()
    logger.info(f"Roles after creation: {[role.name for role in roles_after]}")

    # Create default Super Admin if no admins exist
    from app.domain.entities import Admin
    from app.core.security import get_password_hash

    admin_count = await Admin.find_all().count()
    if admin_count == 0:
        logger.info("No admins found. Creating default super admin...")
        SuperAdmin_role = await Role.find_one(Role.name == SUPER_ADMIN_ROLE_NAME)
        
        if not SuperAdmin_role:
            logger.error(f"CRITICAL ERROR: {SUPER_ADMIN_ROLE_NAME} role not found! Cannot create default admin.")
            raise RuntimeError(f"CRITICAL ERROR: {SUPER_ADMIN_ROLE_NAME} role not found! Cannot create default admin. This indicates a fundamental system setup failure.")
        else:
            default_admin = Admin(
                email=settings.default_SuperAdmin_email,
                hashed_password=get_password_hash(settings.default_SuperAdmin_password),
                full_name="Default Super Admin",
                role_id=str(SuperAdmin_role.id),
                role_name=SUPER_ADMIN_ROLE_NAME
            )
            await default_admin.insert()
            logger.info(f"✅ Created default super admin: {settings.default_SuperAdmin_email}")

    # Start background job processor
    from app.docs_as_code.background_jobs import start_background_jobs
    await start_background_jobs()
    logger.info("✅ Application startup completed!")

    yield  # Application runs here

    # Shutdown code
    logger.info("🛑 Shutting down the application...")
    
    from app.infrastructure.connection_manager import shutdown_connections
    await shutdown_connections()

    from app.infrastructure.database.mongodb import close_mongo_client
    await close_mongo_client()

    from app.docs_as_code.background_jobs import stop_background_jobs
    await stop_background_jobs()
    
    logger.info("✅ Application shutdown completed!")


# Import API routers
from app.api.routes.auth_refactored import router as auth_router
from app.api.routes.chat_refactored import router as chat_router
from app.api.routes.admin_refactored import router as admin_router
from app.api.routes.knowledge_base import router as kb_router
from app.api.routes.super_admin_knowledge_base import router as admin_kb_router
from app.api.routes.upload import router as upload_router
from app.api.routes.categories import router as categories_router
from app.api.routes.system_routes import router as system_router
from app.api.routes.super_admin_reindex import router as reindex_router

app = FastAPI(
    title="Sally Chat Bot API",
    version="2.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware stack (order matters - error handler first)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(ErrorLoggingMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware)
app.add_middleware(RequestLoggingMiddleware)

logger.info("🚀 Middleware stack configured")
logger.info(f"📊 Logging to: logs/")
logger.info(f"🔧 Environment: {'Production' if not settings.debug else 'Development'}")

# Include routers with consistent prefixes based on RBAC permissions

# ============================================================================
# API ROUTES ORGANIZED BY ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================================================

# --- PUBLIC ROUTES (No authentication required) ---
app.include_router(auth_router, prefix="/api/auth", tags=["🔓 Authentication"])
app.include_router(kb_router, prefix="/api/kb", tags=["🔓 Public Knowledge Base"])

# --- CUSTOMER ROUTES (Customer role permissions) ---
# Permissions: VIEW_PUBLIC_KB
app.include_router(chat_router, prefix="/api", tags=["💬 Chat"])
# Note: /api/kb/customer/articles requires customer authentication
# This endpoint is part of kb_router but requires authentication

# --- ADMIN ROUTES (Admin + SuperAdmin role permissions) ---
# Permissions: VIEW_CUSTOMERS, CREATE_KB_ARTICLES, UPDATE_KB_ARTICLES, VIEW_ACTIVITY_LOGS
app.include_router(admin_router, prefix="/api/admin", tags=["👨‍💼 Admin Management"])

# --- SUPER ADMIN ROUTES (SuperAdmin only - highest privilege) ---
# Permissions: All admin permissions + MANAGE_ADMINS, MANAGE_CUSTOMERS,
# PUBLISH_ARTICLES, DELETE_ARTICLES, MANAGE_SYSTEM_SETTINGS
app.include_router(admin_kb_router, prefix="/api/super-admin/kb", tags=["👑 Super Admin Knowledge Base"])
app.include_router(upload_router, prefix="/api/super-admin", tags=["👑 Super Admin Upload"])
app.include_router(categories_router, prefix="/api/super-admin/categories", tags=["👑 Super Admin Categories"])
app.include_router(reindex_router, prefix="/api/super-admin", tags=["👑 Super Admin Re-indexing"])
app.include_router(system_router, prefix="/api/system", tags=["🔧 System Monitoring"])

# ============================================================================

# Alias for /api/users/me to /api/auth/me
@app.get("/api/users/me")
async def get_current_user_alias(request: Request):
    from app.api.routes.auth_refactored import _get_current_user_info
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = auth_header.split(" ")[1]
    return await _get_current_user_info(token)

# Authentication status check endpoint
@app.get("/api/auth/status")
async def get_auth_status(request: Request):
    """Check authentication status for SPA routing."""
    from app.api.routes.auth_refactored import _get_current_user_info
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return {
            "authenticated": False,
            "user": None,
            "user_type": None
        }

    try:
        token = auth_header.split(" ")[1]
        user_info = await _get_current_user_info(token)
        return {
            "authenticated": True,
            "user": user_info["user"],
            "user_type": user_info["user_type"]
        }
    except HTTPException:
        return {
            "authenticated": False,
            "user": None,
            "user_type": None
        }

# SPA Route handler with authentication check
@app.get("/{path:path}")
async def serve_spa_with_auth(path: str, request: Request):
    """Serve SPA with authentication awareness."""

    # Skip API routes, docs, and static files
    if (path.startswith("api/") or
        path.startswith("docs") or
        path.startswith("redoc") or
        path.startswith("openapi") or
        path.startswith("_next") or
        path.endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2"))):
        raise HTTPException(status_code=404, detail="Not found")

    # Check if this is a protected route
    protected_routes = ["/dashboard", "/chat", "/admin", "/super-admin"]
    is_protected_route = any(path.startswith(route) for route in protected_routes)

    if is_protected_route:
        # Check authentication for protected routes
        from app.api.routes.auth_refactored import _get_current_user_info
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            # Return auth required response for SPA
            return {
                "auth_required": True,
                "redirect_to": "/login",
                "message": "Authentication required"
            }

        try:
            token = auth_header.split(" ")[1]
            user_info = await _get_current_user_info(token)
            # User is authenticated, serve the SPA normally
        except HTTPException:
            # Authentication failed
            return {
                "auth_required": True,
                "redirect_to": "/login",
                "message": "Authentication required"
            }

    # Serve index.html for all other routes (including public routes)
    index_path = "sally-frontend/build/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "Frontend not built. Run 'npm run build' in sally-frontend directory."}


@app.get("/")
async def root():
    return {
        "message": "🎯 Sally Chat Bot API v2.0 - Multi-User System with RBAC",
        "version": "2.0",
        "documentation": "/docs",
        "roles": {
            "SuperAdmin": "👑 Full system access",
            "Admin": "👨‍💼 Customer management",
            "Customer": "👤 Chat access",
            "Guest": "🔓 Public knowledge base only"
        },
        "endpoints": {
            "public": ["/api/auth/*", "/api/kb/articles"],
            "customer": ["/api/chat/*"],
            "admin": ["/api/admin/*"],
            "super_admin": ["/api/super-admin/*"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)