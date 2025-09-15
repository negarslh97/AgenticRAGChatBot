from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from bson import ObjectId

# --- وارد کردن مدل‌های دیتابیس ---
from app.domain.entities_refactored import (
    Admin, Customer, Role, KnowledgeBaseArticle, ArticleStatus,
    Ticket, ActivityLog, PermissionDetail
)
# --- وارد کردن سیستم دسترسی و احراز هویت ---
from app.core.permissions import (
    get_current_admin_with_permission, Permission
)
from app.core.security import get_password_hash

router = APIRouter()


# --- مدل‌های Pydantic برای ورودی و خروجی API ---

# مدل‌های مربوط به مدیریت دسترسی‌ها (Permissions)
class PermissionDetailResponse(BaseModel):
    permission_key: str
    description: Optional[str] = None
    resource: str
    action: str

# مدل‌های مربوط به مدیریت نقش‌ها (Roles)
class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    permissions: List[PermissionDetailResponse]
    is_active: bool

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[PermissionDetailResponse]

class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[PermissionDetailResponse]] = None
    is_active: Optional[bool] = None

# مدل‌های مربوط به مدیریت ادمین‌ها
class RoleInadminResponse(BaseModel):
    id: str
    name: str

class adminUserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: RoleInadminResponse
    is_active: bool

class adminUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role_id: str

class adminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[str] = None
    is_active: Optional[bool] = None

# مدل‌های مربوط به مدیریت مشتریان
class CustomerResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool

class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

# مدل‌های مربوط به مدیریت مقالات دانش‌بنیان
class ArticleCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None


# --- Endpoints مدیریت ادمین‌ها (فقط SuperAdmin) ---

@router.get("/admins", response_model=List[adminUserResponse], dependencies=[Depends(get_current_admin_with_permission(Permission.VIEW_adminS))])
async def get_all_admins():
    admins = await admin.find_all().to_list()
    response = []
    for admin in admins:
        role = await admin.get_role()
        response.append(adminUserResponse(
            id=str(admin.id),
            email=admin.email,
            full_name=admin.full_name,
            role=RoleInadminResponse(id=str(role.id), name=role.name) if role else RoleInadminResponse(id="", name="N/A"),
            is_active=admin.is_active
        ))
    return response

@router.post("/admins", response_model=adminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(user_data: adminUserCreate, current_admin: Admin = Depends(get_current_admin_with_permission(Permission.CREATE_adminS))):
    """Create a new admin user (Super admin only)."""
    # 1. بررسی اینکه آیا کاربر از قبل وجود دارد
    if await Admin.find_one(Admin.email == user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. بررسی اینکه آیا نقش (Role) معتبر است
    try:
        # role_id ورودی را به ObjectId تبدیل می‌کنیم تا در دیتابیس جستجو کنیم
        role_obj_id = ObjectId(user_data.role_id)
        role = await Role.get(role_obj_id)
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role ID")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid role ID format")
    
    # 3. ساخت ادمین جدید
    new_admin = Admin(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        # --- اصلاح اصلی: شیء ObjectId را به رشته تبدیل می‌کنیم ---
        role_id=str(role.id),
        # --- بهبود: نام نقش را هم برای خوانایی بهتر ذخیره می‌کنیم ---
        role_name=role.name 
    )
    
    await new_admin.insert()
    
    # 4. لاگ کردن فعالیت
    activity_log = ActivityLog(
        # --- اصلاح دوم: current_admin.id را به رشته تبدیل می‌کنیم ---
        admin_id=str(current_admin.id),
        action="create_admin",
        resource_type="Admin",
        resource_id=str(new_admin.id),
        details={"created_admin_email": new_admin.email, "role": role.name}
    )
    await activity_log.insert()
    
    # 5. آماده‌سازی و بازگرداندن پاسخ
    return adminUserResponse(
        id=str(new_admin.id),
        email=new_admin.email,
        full_name=new_admin.full_name,
        role={
            "id": new_admin.role_id, # این فیلد حالا خودش یک رشته است
            "name": role.name,
            "description": role.description
        },
        is_active=new_admin.is_active,
        created_at=new_admin.created_at
    )

# --- Endpoints مدیریت مقالات دانش‌بنیان (تفکیک شده بر اساس دسترسی) ---

@router.post("/kb/articles", summary="Create a new draft article", status_code=status.HTTP_201_CREATED)
async def create_article(article_data: ArticleCreate, current_admin: Admin = Depends(get_current_admin_with_permission(Permission.CREATE_KB_ARTICLES))):
    """
    ادمین و ادمین ارشد می‌توانند مقاله جدیدی در حالت پیش‌نویس ایجاد کنند.
    """
    article = KnowledgeBaseArticle(
        title=article_data.title,
        content=article_data.content,
        summary=article_data.summary,
        author_id=str(current_admin.id),
        status=ArticleStatus.DRAFT  # همه مقالات به صورت پیش‌نویس شروع می‌شوند
    )
    await article.insert()
    return {"id": str(article.id), "status": "draft", "message": "Article created successfully as a draft."}

@router.put("/kb/articles/{article_id}", summary="Update an article")
async def update_article(article_id: str, article_data: ArticleUpdate, current_admin: Admin = Depends(get_current_admin_with_permission(Permission.UPDATE_KB_ARTICLES))):
    """
    ادمین و ادمین ارشد می‌توانند محتوای یک مقاله را ویرایش کنند.
    وضعیت مقاله (مثلاً انتشار) در اینجا تغییر نمی‌کند.
    """
    try:
        article = await KnowledgeBaseArticle.get(ObjectId(article_id))
        if not article:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Article ID format")
    
    update_data = article_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(article, key, value)
    
    article.updated_at = datetime.utcnow()
    await article.save()
    return {"id": str(article.id), "message": "Article updated successfully."}

@router.post("/kb/articles/{article_id}/publish", summary="Publish an article (SuperAdmin only)")
async def publish_article(article_id: str, current_admin: Admin = Depends(get_current_admin_with_permission(Permission.PUBLISH_ARTICLES))):
    """
    فقط ادمین ارشد می‌تواند یک مقاله را از حالت پیش‌نویس به منتشر شده تغییر دهد.
    """
    try:
        article = await KnowledgeBaseArticle.get(ObjectId(article_id))
        if not article:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Article ID format")
        
    if article.status == ArticleStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Article is already published")

    article.status = ArticleStatus.PUBLISHED
    article.published_at = datetime.utcnow()
    article.published_by = str(current_admin.id)
    await article.save()
    return {"id": str(article.id), "status": "published", "message": "Article published successfully."}

@router.delete("/kb/articles/{article_id}", summary="Delete an article (SuperAdmin only)", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(article_id: str, current_admin: Admin = Depends(get_current_admin_with_permission(Permission.DELETE_ARTICLES))):
    """
    فقط ادمین ارشد می‌تواند یک مقاله را حذف کند.
    """
    try:
        article = await KnowledgeBaseArticle.get(ObjectId(article_id))
        if not article:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Article ID format")

    await article.delete()
    return
