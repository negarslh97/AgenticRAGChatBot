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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.infrastructure.database_refactored import init_db
import logging

# فایل‌های جدیدی که باید بسازید یا جایگزین کنید
from app.api.routes.auth_refactored import router as auth_router
from app.api.routes.chat_refactored import router as chat_router
from app.api.routes.tickets_refactored import router as tickets_router
from app.api.routes.admin_refactored import router as admin_router
# روترهای موجود که نیازی به تغییر بزرگ ندارند
from app.api.routes.knowledge_base import router as kb_router
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

# Include refactored routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(tickets_router, prefix="/api", tags=["Tickets"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(kb_router, prefix="/api/kb", tags=["Knowledge Base"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])

@app.on_event("startup")
async def startup_event():
    """Initialize database and create default roles/admin on startup."""
    logger.info("Starting up the application...")
    await init_db()
    
    # این تابع نقش‌ها را با حروف بزرگ (SuperAdmin, admin, ...) می‌سازد
    from app.core.permissions import create_default_roles
    await create_default_roles()
    
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

@app.get("/")
async def root():
    return {"message": "Sally Chat Bot API v2.0 - Multi-User System with RBAC"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)