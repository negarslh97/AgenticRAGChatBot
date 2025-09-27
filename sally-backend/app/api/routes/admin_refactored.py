from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from bson import ObjectId
import openai
import json

# --- وارد کردن مدل‌های دیتابیس ---
from app.domain.entities_refactored import (
    Admin, Customer, Role, KnowledgeBaseArticle, ArticleStatus,
    Ticket, ActivityLog, PermissionDetail, ArticleCategory, ArticleTag, Category, Tag
)
import markdown  # For markdown to HTML conversion
# --- وارد کردن سیستم دسترسی و احراز هویت ---
from app.core.permissions import (
    get_current_admin, get_current_admin_with_permission, Permission
)
from app.core.security import get_password_hash
from app.core.config import settings

router = APIRouter()


# --- مدل‌های Pydantic برای ورودی و خروجی API ---

# --- تابع کمکی برای تولید متادیتای هوش مصنوعی ---
async def _generate_metadata_from_ai(title: str, content: str) -> dict:
    """تولید متادیتای مقاله با استفاده از LangChain"""
    from app.infrastructure.langchain_utils import langchain_service

    try:
        return await langchain_service.generate_metadata(title, content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطای غیرمنتظره در تولید متادیتا: {str(e)}"
        )

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
    role: str  # اضافه کردن نقش برای نمایش در فرانت‌اند
    is_active: bool

class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

# مدل‌های مربوط به مدیریت مقالات دانش‌بنیان
class ArticleCreate(BaseModel):
    title: str
    content_markdown: str
    content_html: Optional[str] = None
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tag_names: List[str] = []

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content_markdown: Optional[str] = None
    content_html: Optional[str] = None
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tag_names: Optional[List[str]] = None

# مدل‌های مربوط به تولید متادیتای هوش مصنوعی
class ArticleContentPayload(BaseModel):
    title: str
    content: str

class GeneratedMetadataResponse(BaseModel):
    summary: str
    tags: List[str]
    suggested_category: str
    suggested_visibility: str


# --- Endpoints مدیریت ادمین‌ها (فقط SuperAdmin) ---

@router.get("/admins", response_model=List[adminUserResponse])
async def get_admins(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    role_name: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_adminS))
):
    """SUPER ADMIN ONLY: Get all admins (VIEW_ADMINS permission)"""
    """Get all admins with pagination and filtering."""
    query = {}

    # Add search filter
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]

    # Add active status filter
    if is_active is not None:
        query["is_active"] = is_active

    # Add role filter
    if role_name:
        query["role_name"] = role_name

    admins = await Admin.find(query).skip(skip).limit(limit).to_list()
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

@router.get("/admins/count", dependencies=[Depends(get_current_admin_with_permission(Permission.VIEW_adminS))])
async def get_admins_count(
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    role_name: Optional[str] = None
):
    """Get total count of admins with filtering."""
    query = {}

    # Add search filter
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]

    # Add active status filter
    if is_active is not None:
        query["is_active"] = is_active

    # Add role filter
    if role_name:
        query["role_name"] = role_name

    count = await Admin.find(query).count()
    return {"count": count}

@router.post("/admins", response_model=adminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    admin_data: adminUserCreate,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.CREATE_adminS))
):
    """SUPER ADMIN ONLY: Create new admin (CREATE_ADMINS permission)"""
    """Create a new admin user (Super admin only)."""
    # 1. بررسی اینکه آیا کاربر از قبل وجود دارد
    if await Admin.find_one(Admin.email == admin_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. بررسی اینکه آیا نقش (Role) معتبر است
    try:
        # role_id ورودی را به ObjectId تبدیل می‌کنیم تا در دیتابیس جستجو کنیم
        role_obj_id = ObjectId(admin_data.role_id)
        role = await Role.get(role_obj_id)
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role ID")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid role ID format")
    
    # 3. ساخت ادمین جدید
    new_admin = Admin(
        email=admin_data.email,
        hashed_password=get_password_hash(admin_data.password),
        full_name=admin_data.full_name,
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

# --- Endpoints مدیریت مشتریان ---

@router.get("/customers", response_model=List[CustomerResponse])
async def get_customers(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_CUSTOMERS))
):
    """Get customers - Admin+ only (VIEW_CUSTOMERS permission)"""
async def get_all_customers(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """Get all customers with pagination and filtering."""
    query = {}

    # Add search filter
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]

    # Add active status filter
    if is_active is not None:
        query["is_active"] = is_active

    customers = await Customer.find(query).skip(skip).limit(limit).to_list()
    response = []
    for customer in customers:
        # مشتریان معمولاً نقش ندارن، ولی برای نمایش در فرانت‌اند نقش پیش‌فرض می‌ذاریم
        customer_role = getattr(customer, 'role', 'Customer') or 'Customer'
        if not customer_role or customer_role == '':
            customer_role = 'Customer'
            
        response.append(CustomerResponse(
            id=str(customer.id),
            email=customer.email,
            full_name=customer.full_name,
            role=customer_role,
            is_active=customer.is_active
        ))
    return response

@router.get("/customers/count", dependencies=[Depends(get_current_admin_with_permission(Permission.VIEW_CUSTOMERS))])
async def get_customers_count(
    search: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """Get total count of customers with filtering."""
    query = {}

    # Add search filter
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]

    # Add active status filter
    if is_active is not None:
        query["is_active"] = is_active

    count = await Customer.find(query).count()
    return {"count": count}

@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_data: CustomerUpdate,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_CUSTOMERS))
):
    """SUPER ADMIN ONLY: Update customer (MANAGE_CUSTOMERS permission)"""
    """Update a customer."""
    try:
        customer = await Customer.get(ObjectId(customer_id))
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid customer ID")

    update_data = customer_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(customer, key, value)

    customer.updated_at = datetime.utcnow()
    await customer.save()

    # Log activity
    activity_log = ActivityLog(
        admin_id=str(current_admin.id),
        action="update_customer",
        resource_type="Customer",
        resource_id=str(customer.id),
        details={"updated_fields": list(update_data.keys())}
    )
    await activity_log.insert()

    return CustomerResponse(
        id=str(customer.id),
        email=customer.email,
        full_name=customer.full_name,
        is_active=customer.is_active
    )

@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_CUSTOMERS))
):
    """SUPER ADMIN ONLY: Delete customer (MANAGE_CUSTOMERS permission)"""
    """Delete a customer."""
    try:
        customer = await Customer.get(ObjectId(customer_id))
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid customer ID")

    await customer.delete()

    # Log activity
    activity_log = ActivityLog(
        admin_id=str(current_admin.id),
        action="delete_customer",
        resource_type="Customer",
        resource_id=customer_id,
        details={"deleted_customer_email": customer.email}
    )
    await activity_log.insert()

    return

async def get_or_create_tags(tag_names: List[str]) -> List[ArticleTag]:
    """Get or create tags and return ArticleTag objects."""
    article_tags = []
    for tag_name in tag_names:
        # Check if tag exists
        tag = await Tag.find_one(Tag.name == tag_name)
        if not tag:
            # Create new tag
            tag = Tag(name=tag_name)
            await tag.insert()
        article_tags.append(ArticleTag(id=str(tag.id), name=tag.name, color=tag.color))
    return article_tags

# --- Endpoints مدیریت مقالات دانش‌بنیان (تفکیک شده بر اساس دسترسی) ---

@router.post("/kb/articles", summary="Create a new draft article", status_code=status.HTTP_201_CREATED)
async def create_kb_article(
    article_data: ArticleCreate,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.CREATE_KB_ARTICLES))
):
    """Create KB article - Admin+ only (CREATE_KB_ARTICLES permission)"""
    """
    ادمین و ادمین ارشد می‌توانند مقاله جدیدی در حالت پیش‌نویس ایجاد کنند.
    """
    # Generate HTML from markdown if not provided
    content_html = article_data.content_html
    if not content_html:
        content_html = markdown.markdown(article_data.content_markdown)
    
    # Handle category
    category = None
    if article_data.category_id:
        cat = await Category.get(article_data.category_id)
        if cat:
            category = ArticleCategory(id=str(cat.id), name=cat.name, slug=cat.slug)
    
    # Handle tags
    tags = await get_or_create_tags(article_data.tag_names)
    
    article = KnowledgeBaseArticle(
        title=article_data.title,
        content_markdown=article_data.content_markdown,
        content_html=content_html,
        summary=article_data.summary,
        category=category,
        tags=tags,
        author=current_admin,
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
    
    # Handle content updates
    if 'content_markdown' in update_data:
        article.content_markdown = update_data['content_markdown']
        # Generate HTML if not provided or if markdown changed
        if 'content_html' not in update_data or not update_data['content_html']:
            article.content_html = markdown.markdown(update_data['content_markdown'])
        else:
            article.content_html = update_data['content_html']
    
    # Handle category
    if 'category_id' in update_data:
        category = None
        if update_data['category_id']:
            cat = await Category.get(update_data['category_id'])
            if cat:
                category = ArticleCategory(id=str(cat.id), name=cat.name, slug=cat.slug)
        article.category = category
    
    # Handle tags
    if 'tag_names' in update_data:
        tags = await get_or_create_tags(update_data['tag_names'])
        article.tags = tags
    
    # Handle other fields
    if 'title' in update_data:
        article.title = update_data['title']
    if 'summary' in update_data:
        article.summary = update_data['summary']
    
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
    article.publisher = current_admin
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

@router.post("/articles/generate-metadata", response_model=GeneratedMetadataResponse, summary="Generate AI metadata for article")
async def generate_article_metadata(
    payload: ArticleContentPayload,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.CREATE_KB_ARTICLES))
):
    """
    تولید متادیتای هوش مصنوعی برای مقاله بر اساس عنوان و محتوا.
    فقط ادمین‌های دارای دسترسی ایجاد مقاله می‌توانند از این API استفاده کنند.
    """
    metadata = await _generate_metadata_from_ai(payload.title, payload.content)
    return GeneratedMetadataResponse(**metadata)


# --- Endpoints مدیریت نقش‌ها (Roles) ---
@router.get("/roles", response_model=List[RoleResponse])
async def get_all_roles(
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_adminS))
):
    """SUPER ADMIN ONLY: Get all roles (VIEW_ADMINS permission)"""
    """Get all roles from database."""
    roles = await Role.find_all().to_list()
    response = []
    for role in roles:
        permissions = [PermissionDetailResponse(**perm.dict()) for perm in role.permissions]
        response.append(RoleResponse(
            id=str(role.id),
            name=role.name,
            description=role.description,
            permissions=permissions,
            is_active=role.is_active
        ))
    return response


@router.get("/superadmin/stats", summary="Get dashboard statistics (SuperAdmin only)")
async def get_dashboard_stats(current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_adminS))):
    """SUPER ADMIN ONLY: Get system statistics"""
    """
    دریافت آمار داشبورد برای ادمین ارشد
    """
    try:
        # Count total admins
        total_admins = await Admin.find_all().count()

        # Count total customers
        total_customers = await Customer.find_all().count()

        # Count tickets by status
        from app.domain.entities_refactored import Ticket, TicketStatus
        open_tickets = await Ticket.find(Ticket.status == TicketStatus.OPEN).count()
        in_progress_tickets = await Ticket.find(Ticket.status == TicketStatus.IN_PROGRESS).count()
        resolved_tickets = await Ticket.find(Ticket.status == TicketStatus.RESOLVED).count()

        # Count knowledge base articles by status
        from app.domain.entities_refactored import KnowledgeBaseArticle, ArticleStatus
        published_articles = await KnowledgeBaseArticle.find(KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED).count()
        draft_articles = await KnowledgeBaseArticle.find(KnowledgeBaseArticle.status == ArticleStatus.DRAFT).count()

        # Count total activity logs
        from app.domain.entities_refactored import ActivityLog
        total_logs = await ActivityLog.find_all().count()

        return {
            "users": {
                "totalAdmins": total_admins,
                "totalCustomers": total_customers
            },
            "tickets": {
                "open": open_tickets,
                "awaitingReply": in_progress_tickets,  # Map IN_PROGRESS to awaitingReply
                "resolved": resolved_tickets
            },
            "knowledgeBase": {
                "published": published_articles,
                "drafts": draft_articles
            },
            "activityLogs": {
                "total": total_logs
            }
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching stats: {str(e)}")
