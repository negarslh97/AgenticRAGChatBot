# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from contextlib import asynccontextmanager
# import asyncio

# from app.core.config import settings
# from app.infrastructure.database import init_database, create_default_admin
# from app.api.routes import auth, chat, tickets, admin, knowledge_base, admin_knowledge_base, upload


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     await init_database()
#     await create_default_admin()
#     yield
#     # Shutdown
#     pass


# app = FastAPI(
#     title="Sally - Customer Support Platform",
#     description="AI-powered customer support with RAG capabilities",
#     version="1.0.0",
#     lifespan=lifespan
# )

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
#     expose_headers=["*"],
# )

# # Include routers
# app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# app.include_router(chat.router, prefix="/chat", tags=["Chat"])
# app.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
# app.include_router(knowledge_base.router, prefix="/kb", tags=["Knowledge Base"])
# app.include_router(admin.router, prefix="/admin", tags=["admin"])
# app.include_router(admin_knowledge_base.router, prefix="/admin/kb", tags=["admin: Knowledge Base"])
# app.include_router(upload.router, prefix="/admin/upload", tags=["File Upload"])


# @app.get("/")
# async def root():
#     return {"message": "Sally Customer Support Platform API"}


# @app.get("/health")
# async def health_check():
#     return {"status": "healthy"}


# مسیر: sally-backend/main.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.core.config import settings
from app.infrastructure.database_refactored import init_db
import logging
import os

# فایل‌های جدیدی که باید بسازید یا جایگزین کنید
from app.api.routes.auth_refactored import router as auth_router
from app.api.routes.chat_refactored import router as chat_router
from app.api.routes.tickets_refactored import router as tickets_router
from app.api.routes.admin_refactored import router as admin_router
# روترهای موجود که نیازی به تغییر بزرگ ندارند
from app.api.routes.knowledge_base import router as kb_router
from app.api.routes.admin_knowledge_base import router as admin_kb_router
from app.api.routes.upload import router as upload_router

# تنظیمات لاگ‌گیری برای نمایش بهتر اطلاعات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sally Chat Bot API", version="2.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with consistent prefixes based on RBAC permissions

# ============================================================================
# API ROUTES ORGANIZED BY ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================================================

# --- PUBLIC ROUTES (No authentication required) ---
app.include_router(auth_router, prefix="/api/auth", tags=["🔓 Authentication"])
app.include_router(kb_router, prefix="/api/kb", tags=["🔓 Public Knowledge Base"])

# --- CUSTOMER ROUTES (Customer role permissions) ---
# Permissions: CREATE_TICKETS, REPLY_TICKETS, VIEW_PUBLIC_KB
app.include_router(chat_router, prefix="/api/customer/chat", tags=["👤 Customer Chat"])
app.include_router(tickets_router, prefix="/api/customer/tickets", tags=["👤 Customer Tickets"])
app.include_router(tickets_router, prefix="/api/admin/tickets", tags=["👨‍💼 Admin Tickets"])
# Note: /api/kb/customer/articles requires customer authentication
# This endpoint is part of kb_router but requires authentication

# --- ADMIN ROUTES (Admin + SuperAdmin role permissions) ---
# Permissions: VIEW_CUSTOMERS, VIEW_ALL_TICKETS, REPLY_TICKETS, ASSIGN_TICKETS,
# MANAGE_TICKET_STATUSES, CREATE_KB_ARTICLES, UPDATE_KB_ARTICLES, VIEW_ACTIVITY_LOGS
app.include_router(admin_router, prefix="/api/admin", tags=["👨‍💼 Admin Management"])

# --- SUPER ADMIN ROUTES (SuperAdmin only - highest privilege) ---
# Permissions: All admin permissions + MANAGE_ADMINS, MANAGE_CUSTOMERS,
# PUBLISH_ARTICLES, DELETE_ARTICLES, MANAGE_SYSTEM_SETTINGS
app.include_router(admin_kb_router, prefix="/api/super-admin/kb", tags=["👑 Super Admin Knowledge Base"])
app.include_router(upload_router, prefix="/api/super-admin", tags=["👑 Super Admin Upload"])

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
    protected_routes = ["/dashboard", "/chat", "/tickets", "/admin", "/super-admin"]
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

# Note: SPA route handler with authentication check is defined above

@app.on_event("startup")
async def startup_event():
    """Initialize database and create default roles/admin on startup."""
    logger.info("Starting up the application...")
    await init_db()

    # Log existing roles in database for debugging
    from app.domain.entities_refactored import Role
    existing_roles = await Role.find_all().to_list()
    logger.info(f"DEBUG: Existing roles in database before create_default_roles: {[role.name for role in existing_roles]}")

    # این تابع نقش‌ها را با حروف بزرگ (SuperAdmin, Admin, ...) می‌سازد
    from app.core.permissions import create_default_roles
    await create_default_roles()

    # Log roles after creation
    roles_after = await Role.find_all().to_list()
    logger.info(f"DEBUG: Roles in database after create_default_roles: {[role.name for role in roles_after]}")

    # ساخت ادمین پیش‌فرض در صورتی که هیچ ادمینی وجود نداشته باشد
    from app.domain.entities_refactored import Admin, Role
    from app.core.security import get_password_hash

    admin_count = await Admin.find_all().count()
    if admin_count == 0:
        logger.info("No admins found. Creating default super admin...")

        # --- اصلاح اصلی و کلیدی اینجاست ---
        # حالا به دنبال نقشی با نام "SuperAdmin" (با حرف بزرگ) می‌گردیم
        SuperAdmin_role = await Role.find_one(Role.name == "SuperAdmin")
        # --- پایان اصلاح ---

        if not SuperAdmin_role:
            # این پیام خطا حالا بسیار مهم است، چون نشان می‌دهد حتی نقش با حروف بزرگ هم ساخته نشده
            logger.error("SuperAdmin role not found! Cannot create default admin. Check DEFAULT_ROLES in permissions.py")
            return

        default_admin = Admin(
            email=settings.default_SuperAdmin_email,
            hashed_password=get_password_hash(settings.default_SuperAdmin_password),
            full_name="Default Super Admin",
            # --- بهبود کوچک اما مهم: تبدیل id به رشته ---
            role_id=str(SuperAdmin_role.id),
            # --- بهبود دوم: اضافه کردن role_name ---
            role_name=SuperAdmin_role.name
        )
        await default_admin.insert()
        logger.info(f"Created default super Admin: {settings.default_SuperAdmin_email}")

    # Start background job processor
    from app.docs_as_code.background_jobs import start_background_jobs
    await start_background_jobs()
    logger.info("Background job processor started")

    logger.info("Application startup completed!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("Shutting down the application...")

    # Stop background job processor
    from app.docs_as_code.background_jobs import stop_background_jobs
    await stop_background_jobs()
    logger.info("Background job processor stopped")

    logger.info("Application shutdown completed!")


@app.get("/")
async def root():
    return {
        "message": "🎯 Sally Chat Bot API v2.0 - Multi-User System with RBAC",
        "version": "2.0",
        "documentation": "/docs",
        "roles": {
            "SuperAdmin": "👑 Full system access",
            "Admin": "👨‍💼 Customer & ticket management",
            "Customer": "👤 Ticket creation & chat",
            "Guest": "🔓 Public knowledge base only"
        },
        "endpoints": {
            "public": ["/api/auth/*", "/api/kb/articles"],
            "customer": ["/api/customer/*"],
            "admin": ["/api/admin/*"],
            "super_admin": ["/api/super-admin/*"]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)