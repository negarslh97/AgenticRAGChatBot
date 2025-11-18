from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from bson import ObjectId
import openai
import json

# --- وارد کردن مدل‌های دیتابیس ---
from app.domain.entities import (
    Admin, Customer, Role, KnowledgeBaseArticle, ArticleStatus,
    ActivityLog, PermissionDetail, ArticleCategory, ArticleTag, Category, Tag,
    Conversation, Message
)
import markdown  # For markdown to HTML conversion
# --- وارد کردن سیستم دسترسی و احراز هویت ---
from app.core.permissions import (
    get_current_admin, get_current_admin_with_permission, Permission
)
from app.core.security import get_password_hash
from app.core.config import settings
from app.services.knowledge_base_service import get_or_create_tags

router = APIRouter()


# --- مدل‌های Pydantic برای ورودی و خروجی API ---

# --- تابع کمکی برای تولید متادیتای هوش مصنوعی ---
async def _generate_metadata_from_ai(title: str, content: str) -> dict:
    """تولید متادیتای مقاله با استفاده از MetadataService"""
    from app.services.metadata_service import metadata_service

    try:
        return await metadata_service.generate_metadata(title, content)
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
    email: str
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

# --- مدل‌های مربوط به آمار لاگ‌ها ---
class ConversationStats(BaseModel):
    totalConversations: int
    totalMessages: int
    averageMessagesPerConversation: float
    activeConversations: int
    completedConversations: int
    conversationsToday: int
    conversationsThisWeek: int
    conversationsThisMonth: int
    topActiveHours: List[dict]
    userParticipationStats: List[dict]

class UserActivity(BaseModel):
    id: str
    name: str
    email: str
    userType: str
    totalConversations: int
    totalMessages: int
    lastActivity: str
    isActive: bool
    averageMessagesPerConversation: float

class RecentConversation(BaseModel):
    id: str
    customerName: str
    customerEmail: str
    adminName: Optional[str]
    startTime: str
    endTime: Optional[str]
    messageCount: int
    status: str
    duration: Optional[str]


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

@router.put("/admins/{admin_id}", response_model=adminUserResponse)
async def update_admin(
    admin_id: str,
    admin_data: adminUserUpdate,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_adminS))
):
    """Update admin information (SuperAdmin only)."""
    admin = await Admin.get(ObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    # Update fields
    update_dict = admin_data.model_dump(exclude_unset=True)
    if update_dict:
        for key, value in update_dict.items():
            if key == "role_id":
                # Verify role exists
                role = await Role.get(ObjectId(value))
                if not role:
                    raise HTTPException(status_code=400, detail="Invalid role ID")
                admin.role_id = str(role.id)
                admin.role_name = role.name
            else:
                setattr(admin, key, value)

        await admin.save()

    # Return updated admin with role info
    role = await admin.get_role()
    return adminUserResponse(
        id=str(admin.id),
        email=admin.email,
        full_name=admin.full_name,
        role=RoleInadminResponse(id=str(role.id), name=role.name) if role else RoleInadminResponse(id="", name="N/A"),
        is_active=admin.is_active
    )


@router.delete("/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(
    admin_id: str,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.DELETE_adminS))
):
    """Delete admin (SuperAdmin only)."""
    admin = await Admin.get(ObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    # Prevent deleting self
    if admin.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    await admin.delete()


@router.get("/activity-logs", response_model=List[dict])
async def get_activity_logs(
    skip: int = 0,
    limit: int = 50,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_ACTIVITY_LOGS))
):
    """Get activity logs (Admin only)."""
    activity_logs = await ActivityLog.find().sort(-ActivityLog.created_at).skip(skip).limit(limit).to_list()

    # Convert to dict for response
    result = []
    for log in activity_logs:
        result.append({
            "id": str(log.id),
            "admin_id": log.admin_id,
            "customer_id": log.customer_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "created_at": log.created_at.isoformat()
        })

    return result


@router.get("/admins/{admin_id}", response_model=adminUserResponse)
async def get_admin(
    admin_id: str,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_adminS))
):
    """Get specific admin by ID (SuperAdmin only)."""
    admin = await Admin.get(ObjectId(admin_id))
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    role = await admin.get_role()
    return adminUserResponse(
        id=str(admin.id),
        email=admin.email,
        full_name=admin.full_name,
        role=RoleInadminResponse(id=str(role.id), name=role.name) if role else RoleInadminResponse(id="", name="N/A"),
        is_active=admin.is_active
    )


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
    is_active: Optional[bool] = None,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_CUSTOMERS))
):
    """Get customers - Admin+ only (VIEW_CUSTOMERS permission)"""
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

        # Tickets removed from system
        open_tickets = in_progress_tickets = resolved_tickets = 0

        # Count knowledge base articles by status
        try:
            from app.domain.entities import KnowledgeBaseArticle, ArticleStatus
            published_articles = await KnowledgeBaseArticle.find(KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED).count()
            draft_articles = await KnowledgeBaseArticle.find(KnowledgeBaseArticle.status == ArticleStatus.DRAFT).count()
        except:
            published_articles = draft_articles = 0

        # Count total activity logs
        try:
            from app.domain.entities import ActivityLog
            total_logs = await ActivityLog.find_all().count()
        except:
            total_logs = 0

        # Count chat conversations and messages
        try:
            from app.domain.entities import Conversation, Message
            total_conversations = await Conversation.find_all().count()
            total_messages = await Message.find_all().count()
        except:
            total_conversations = total_messages = 0

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
            },
            "chat": {
                "conversations": total_conversations,
                "messages": total_messages
            }
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching stats: {str(e)}")


@router.get("/logs/conversation-stats", response_model=ConversationStats)
async def get_conversation_stats(current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_adminS))):
    """Get detailed conversation statistics"""
    try:
        from datetime import datetime, timedelta
        import calendar

        # Get basic counts
        total_conversations = await Conversation.find_all().count()
        total_messages = await Message.find_all().count()
        average_messages = round(total_messages / total_conversations, 1) if total_conversations > 0 else 0

        # Get today's, week's, and month's conversation counts
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        conversations_today = await Conversation.find({"created_at": {"$gte": today_start}}).count()
        conversations_week = await Conversation.find({"created_at": {"$gte": week_start}}).count()
        conversations_month = await Conversation.find({"created_at": {"$gte": month_start}}).count()

        # For now, we'll assume all conversations are active/completed based on recent activity
        # In a real implementation, you'd track conversation status separately
        active_conversations = await Conversation.find({"updated_at": {"$gte": now - timedelta(hours=24)}}).count()
        completed_conversations = total_conversations - active_conversations

        # Get hourly activity (last 24 hours)
        hourly_activity = []
        for hour in range(24):
            hour_start = now - timedelta(hours=hour+1)
            hour_end = now - timedelta(hours=hour)
            count = await Message.find({"created_at": {"$gte": hour_start, "$lt": hour_end}}).count()
            hourly_activity.append({"hour": hour, "count": count})
        hourly_activity.reverse()  # Show from oldest to newest

        # Calculate top 5 active hours
        sorted_hours = sorted(hourly_activity, key=lambda x: x["count"], reverse=True)[:5]

        # Get user participation stats
        # Count messages by sender type
        customer_messages = await Message.find({"sender_type": "Customer"}).count()
        admin_messages = await Message.find({"sender_type": {"$in": ["Admin", "SuperAdmin"]}}).count()
        ai_messages = await Message.find({"sender_type": "AI"}).count()

        total_user_messages = customer_messages + admin_messages
        customer_percentage = round((customer_messages / total_user_messages * 100), 1) if total_user_messages > 0 else 0
        admin_percentage = round((admin_messages / total_user_messages * 100), 1) if total_user_messages > 0 else 0

        # Return mock data if no real data exists (for development/testing)
        if total_conversations == 0:
            return {
                "totalConversations": 1247,
                "totalMessages": 8934,
                "averageMessagesPerConversation": 7.2,
                "activeConversations": 23,
                "completedConversations": 1224,
                "conversationsToday": 45,
                "conversationsThisWeek": 287,
                "conversationsThisMonth": 1034,
                "topActiveHours": [
                    {"hour": 9, "count": 145},
                    {"hour": 10, "count": 132},
                    {"hour": 14, "count": 128},
                    {"hour": 15, "count": 119},
                    {"hour": 11, "count": 105}
                ],
                "userParticipationStats": [
                    {"userType": "Customers", "count": 856, "percentage": 68.6},
                    {"userType": "Admins", "count": 391, "percentage": 31.4}
                ]
            }

        return {
            "totalConversations": total_conversations,
            "totalMessages": total_messages,
            "averageMessagesPerConversation": average_messages,
            "activeConversations": active_conversations,
            "completedConversations": completed_conversations,
            "conversationsToday": conversations_today,
            "conversationsThisWeek": conversations_week,
            "conversationsThisMonth": conversations_month,
            "topActiveHours": sorted_hours,
            "userParticipationStats": [
                {"userType": "Customers", "count": customer_messages, "percentage": customer_percentage},
                {"userType": "Admins", "count": admin_messages, "percentage": admin_percentage}
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching conversation stats: {str(e)}")


@router.get("/logs/user-activities", response_model=List[UserActivity])
async def get_user_activities(current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_adminS))):
    """Get user activity statistics"""
    try:
        from datetime import timedelta

        user_activities = []
        now = datetime.utcnow()
        recent_threshold = now - timedelta(days=7)  # Active if had activity in last 7 days

        # Get customers with their conversation counts
        customers = await Customer.find_all().to_list()
        for customer in customers:
            customer_conversations = await Conversation.find({"customer_id": str(customer.id)}).to_list()
            total_conversations = len(customer_conversations)

            if total_conversations > 0:
                # Get messages for this customer
                customer_message_count = 0
                last_activity = None

                for conv in customer_conversations:
                    conv_messages = await Message.find(Message.conversation_id == str(conv.id)).to_list()
                    customer_message_count += len(conv_messages)

                    # Update last activity
                    if conv.updated_at and (not last_activity or conv.updated_at > last_activity):
                        last_activity = conv.updated_at

                is_active = last_activity and last_activity >= recent_threshold if last_activity else False
                avg_messages = round(customer_message_count / total_conversations, 1) if total_conversations > 0 else 0

                user_activities.append({
                    "id": str(customer.id),
                    "name": customer.full_name,
                    "email": customer.email,
                    "userType": "Customer",
                    "totalConversations": total_conversations,
                    "totalMessages": customer_message_count,
                    "lastActivity": last_activity.isoformat() if last_activity else now.isoformat(),
                    "isActive": is_active,
                    "averageMessagesPerConversation": avg_messages
                })

        # Get admins with their conversation counts
        admins = await Admin.find_all().to_list()
        for admin in admins:
            # Count conversations where this admin participated
            admin_conversations = await Conversation.find({"admin_id": str(admin.id)}).to_list()
            total_conversations = len(admin_conversations)

            if total_conversations > 0:
                # Get messages from this admin - simplified query
                admin_message_count = 0
                last_activity = None

                for conv in admin_conversations:
                    # Get all messages for this conversation first
                    all_messages = await Message.find(Message.conversation_id == str(conv.id)).to_list()
                    # Filter for admin messages
                    admin_messages = [msg for msg in all_messages
                                    if msg.sender_type in ["Admin", "SuperAdmin"] and msg.sender_id == str(admin.id)]
                    admin_message_count += len(admin_messages)

                    # Update last activity
                    if conv.updated_at and (not last_activity or conv.updated_at > last_activity):
                        last_activity = conv.updated_at

                is_active = last_activity and last_activity >= recent_threshold if last_activity else False
                avg_messages = round(admin_message_count / total_conversations, 1) if total_conversations > 0 else 0

                user_activities.append({
                    "id": str(admin.id),
                    "name": admin.full_name,
                    "email": admin.email,
                    "userType": "Admin",
                    "totalConversations": total_conversations,
                    "totalMessages": admin_message_count,
                    "lastActivity": last_activity.isoformat() if last_activity else now.isoformat(),
                    "isActive": is_active,
                    "averageMessagesPerConversation": avg_messages
                })

        # Sort by total messages (most active first)
        user_activities.sort(key=lambda x: x["totalMessages"], reverse=True)

        # Return mock data if no real data exists (for development/testing)
        if not user_activities:
            return [
                {
                    "id": "1",
                    "name": "علی احمدی",
                    "email": "ali.ahmadi@example.com",
                    "userType": "Customer",
                    "totalConversations": 23,
                    "totalMessages": 156,
                    "lastActivity": "2025-10-26T06:30:00Z",
                    "isActive": True,
                    "averageMessagesPerConversation": 6.8
                },
                {
                    "id": "2",
                    "name": "فاطمه رضایی",
                    "email": "fatemeh.rezaei@example.com",
                    "userType": "Customer",
                    "totalConversations": 15,
                    "totalMessages": 89,
                    "lastActivity": "2025-10-26T05:45:00Z",
                    "isActive": False,
                    "averageMessagesPerConversation": 5.9
                },
                {
                    "id": "3",
                    "name": "محمد کریمی",
                    "email": "mohammad.karimi@example.com",
                    "userType": "Admin",
                    "totalConversations": 156,
                    "totalMessages": 1247,
                    "lastActivity": "2025-10-26T06:52:00Z",
                    "isActive": True,
                    "averageMessagesPerConversation": 8.0
                }
            ]

        return user_activities

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching user activities: {str(e)}")


@router.get("/logs/recent-conversations", response_model=List[RecentConversation])
async def get_recent_conversations(current_admin: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_adminS))):
    """Get recent conversations"""
    try:
        from datetime import datetime, timedelta

        recent_conversations = []

        # Get last 20 conversations
        conversations = await Conversation.find().sort([("created_at", -1)]).limit(20).to_list()

        for conv in conversations:
            # Get customer info
            customer_name = "ناشناس"
            customer_email = ""
            if conv.customer_id:
                try:
                    customer = await Customer.get(ObjectId(conv.customer_id))
                    if customer:
                        customer_name = customer.full_name
                        customer_email = customer.email
                except:
                    pass

            # Get admin info if assigned
            admin_name = None
            if conv.admin_id:
                try:
                    admin = await Admin.find(ObjectId(conv.admin_id))
                    if admin:
                        admin_name = admin.full_name
                except:
                    pass

            # Get message count for this conversation
            message_count = await Message.find(Message.conversation_id == str(conv.id)).count()

            # Calculate duration if conversation is completed (no recent activity)
            duration = None
            end_time = None
            now = datetime.utcnow()

            # For simplicity, consider conversations older than 1 hour as completed
            if conv.updated_at and (now - conv.updated_at).total_seconds() > 3600:
                end_time = conv.updated_at
                duration_seconds = (end_time - conv.created_at).total_seconds()
                duration_minutes = int(duration_seconds / 60)
                if duration_minutes < 60:
                    duration = f"{duration_minutes} دقیقه"
                else:
                    hours = duration_minutes // 60
                    minutes = duration_minutes % 60
                    duration = f"{hours} ساعت {minutes} دقیقه"

            # Determine status
            status = "completed" if end_time else "active"

            recent_conversations.append({
                "id": str(conv.id),
                "customerName": customer_name,
                "customerEmail": customer_email,
                "adminName": admin_name,
                "startTime": conv.created_at.isoformat(),
                "endTime": end_time.isoformat() if end_time else None,
                "messageCount": message_count,
                "status": status,
                "duration": duration
            })

        # Return mock data if no real data exists (for development/testing)
        if not recent_conversations:
            return [
                {
                    "id": "1",
                    "customerName": "علی احمدی",
                    "customerEmail": "ali.ahmadi@example.com",
                    "adminName": "محمد کریمی",
                    "startTime": "2025-10-26T06:30:00Z",
                    "endTime": "2025-10-26T06:45:00Z",
                    "messageCount": 12,
                    "status": "completed",
                    "duration": "15 دقیقه"
                },
                {
                    "id": "2",
                    "customerName": "فاطمه رضایی",
                    "customerEmail": "fatemeh.rezaei@example.com",
                    "startTime": "2025-10-26T06:50:00Z",
                    "messageCount": 3,
                    "status": "active"
                }
            ]

        return recent_conversations

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching recent conversations: {str(e)}")

