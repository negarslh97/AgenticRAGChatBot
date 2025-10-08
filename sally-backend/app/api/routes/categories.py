"""
API Routes برای مدیریت Categories (دسته‌بندی‌های Knowledge Base)

این فایل شامل تمام endpoints مورد نیاز برای CRUD operations روی Categories است.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.domain.entities import Admin, Category
from app.core.permissions import get_current_admin, get_current_admin_with_permission, Permission, get_optional_admin
from app.services.knowledge_base_service import knowledge_base_service
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


# =============== PYDANTIC SCHEMAS ===============

class CategoryBase(BaseModel):
    """Base schema for Category"""
    name: str = Field(..., min_length=1, max_length=200, description="نام دسته‌بندی")
    slug: str = Field(..., min_length=1, max_length=200, description="شناسه URL-friendly")
    description: Optional[str] = Field(None, max_length=1000, description="توضیحات دسته‌بندی")
    parent_id: Optional[str] = Field(None, description="ID دسته‌بندی والد")
    is_public: bool = Field(True, description="آیا برای عموم قابل مشاهده است؟")


class CategoryCreate(CategoryBase):
    """Schema for creating a category"""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    parent_id: Optional[str] = None
    is_public: Optional[bool] = None


class CategoryResponse(BaseModel):
    """Schema for category response"""
    id: str
    name: str
    slug: str
    description: Optional[str]
    parent_id: Optional[str]
    is_public: bool
    created_at: datetime
    updated_at: datetime
    
    # اطلاعات اضافی
    articles_count: Optional[int] = 0
    children_count: Optional[int] = 0


class CategoryTreeNode(BaseModel):
    """Schema for category tree node"""
    id: str
    name: str
    slug: str
    description: Optional[str]
    is_public: bool
    children: List['CategoryTreeNode'] = []


class CategoryDeleteResult(BaseModel):
    """Schema for delete operation result"""
    category_name: str
    children_count: int
    articles_count: int
    deleted_categories: List[str]
    affected_articles: List[Dict[str, Any]]
    moved_children: List[str]
    message: str


# =============== API ENDPOINTS ===============

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    ایجاد دسته‌بندی جدید
    
    **دسترسی:** فقط Super Admin
    """
    try:
        logger.info(f"📝 Creating new category: {category_data.name}")
        
        category = await knowledge_base_service.create_category(
            name=category_data.name,
            slug=category_data.slug,
            description=category_data.description,
            parent_id=category_data.parent_id,
            is_public=category_data.is_public
        )
        
        # شمارش مقالات و زیردسته‌ها
        from app.domain.entities import KnowledgeBaseArticle
        articles_count = await KnowledgeBaseArticle.find({"category.id": str(category.id)}).count()
        children = await Category.find({"parent.$id": category.id}).to_list()
        
        return CategoryResponse(
            id=str(category.id),
            name=category.name,
            slug=category.slug,
            description=category.description,
            parent_id=str(category.parent.ref.id) if category.parent else None,
            is_public=category.is_public,
            created_at=category.created_at,
            updated_at=category.updated_at,
            articles_count=articles_count,
            children_count=len(children)
        )
        
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error creating category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در ایجاد دسته‌بندی: {str(e)}"
        )


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    is_public_only: bool = Query(False, description="فقط دسته‌بندی‌های عمومی"),
    parent_id: Optional[str] = Query(None, description="فیلتر بر اساس والد"),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    دریافت لیست تمام دسته‌بندی‌ها
    
    **دسترسی:** عمومی (برای مهمان‌ها فقط public categories)
    """
    try:
        # اگر کاربر مهمان است، فقط عمومی‌ها را نمایش بده
        if not current_admin:
            is_public_only = True
        
        logger.info(f"📚 Fetching categories (public_only={is_public_only}, parent_id={parent_id})")
        
        categories = await knowledge_base_service.get_all_categories(
            is_public_only=is_public_only,
            parent_id=parent_id
        )
        
        # ساخت response با اطلاعات اضافی
        response = []
        for category in categories:
            from app.domain.entities import KnowledgeBaseArticle
            
            # شمارش مقالات
            articles_count = await KnowledgeBaseArticle.find({"category.id": str(category.id)}).count()
            
            # شمارش زیردسته‌ها
            children = await Category.find({"parent.$id": category.id}).to_list()
            
            response.append(CategoryResponse(
                id=str(category.id),
                name=category.name,
                slug=category.slug,
                description=category.description,
                parent_id=str(category.parent.ref.id) if category.parent else None,
                is_public=category.is_public,
                created_at=category.created_at,
                updated_at=category.updated_at,
                articles_count=articles_count,
                children_count=len(children)
            ))
        
        logger.info(f"✅ Found {len(response)} categories")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت دسته‌بندی‌ها: {str(e)}"
        )


@router.get("/tree", response_model=List[CategoryTreeNode])
async def get_category_tree(
    is_public_only: bool = Query(False, description="فقط دسته‌بندی‌های عمومی"),
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    دریافت درخت سلسله‌مراتبی دسته‌بندی‌ها
    
    **دسترسی:** عمومی (برای مهمان‌ها فقط public categories)
    """
    try:
        # اگر کاربر مهمان است، فقط عمومی‌ها را نمایش بده
        if not current_admin:
            is_public_only = True
        
        logger.info(f"🌳 Fetching category tree (public_only={is_public_only})")
        
        tree = await knowledge_base_service.get_category_tree(is_public_only=is_public_only)
        
        logger.info(f"✅ Built category tree with {len(tree)} root nodes")
        return tree
        
    except Exception as e:
        logger.error(f"❌ Error fetching category tree: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت درخت دسته‌بندی: {str(e)}"
        )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    دریافت یک دسته‌بندی با ID
    
    **دسترسی:** عمومی (برای مهمان‌ها فقط public categories)
    """
    try:
        logger.info(f"🔍 Fetching category: {category_id}")
        
        category = await knowledge_base_service.get_category_by_id(category_id)
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"دسته‌بندی با ID '{category_id}' یافت نشد"
            )
        
        # بررسی دسترسی برای مهمان‌ها
        if not current_admin and not category.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="دسترسی به این دسته‌بندی محدود است"
            )
        
        # شمارش مقالات و زیردسته‌ها
        from app.domain.entities import KnowledgeBaseArticle
        articles_count = await KnowledgeBaseArticle.find({"category.id": str(category.id)}).count()
        children = await Category.find({"parent.$id": category.id}).to_list()
        
        return CategoryResponse(
            id=str(category.id),
            name=category.name,
            slug=category.slug,
            description=category.description,
            parent_id=str(category.parent.ref.id) if category.parent else None,
            is_public=category.is_public,
            created_at=category.created_at,
            updated_at=category.updated_at,
            articles_count=articles_count,
            children_count=len(children)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت دسته‌بندی: {str(e)}"
        )


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category_data: CategoryUpdate,
    update_articles: bool = Query(True, description="به‌روزرسانی خودکار مقالات مرتبط"),
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    به‌روزرسانی دسته‌بندی
    
    **دسترسی:** فقط Super Admin
    
    **نکته:** اگر نام یا slug تغییر کند، تمام مقالات مرتبط نیز به‌روز می‌شوند.
    """
    try:
        logger.info(f"✏️ Updating category: {category_id}")
        
        category = await knowledge_base_service.update_category(
            category_id=category_id,
            name=category_data.name,
            slug=category_data.slug,
            description=category_data.description,
            parent_id=category_data.parent_id,
            is_public=category_data.is_public,
            update_articles=update_articles
        )
        
        # شمارش مقالات و زیردسته‌ها
        from app.domain.entities import KnowledgeBaseArticle
        articles_count = await KnowledgeBaseArticle.find({"category.id": str(category.id)}).count()
        children = await Category.find({"parent.$id": category.id}).to_list()
        
        logger.info(f"✅ Category updated successfully")
        
        return CategoryResponse(
            id=str(category.id),
            name=category.name,
            slug=category.slug,
            description=category.description,
            parent_id=str(category.parent.ref.id) if category.parent else None,
            is_public=category.is_public,
            created_at=category.created_at,
            updated_at=category.updated_at,
            articles_count=articles_count,
            children_count=len(children)
        )
        
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در به‌روزرسانی دسته‌بندی: {str(e)}"
        )


@router.delete("/{category_id}", response_model=CategoryDeleteResult)
async def delete_category(
    category_id: str,
    cascade: bool = Query(False, description="حذف زیردسته‌ها و مقالات"),
    move_to_parent: bool = Query(True, description="انتقال زیردسته‌ها به والد"),
    current_admin: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    حذف دسته‌بندی
    
    **دسترسی:** فقط Super Admin
    
    **گزینه‌ها:**
    - `cascade=True`: حذف تمام زیردسته‌ها و مقالات مرتبط
    - `move_to_parent=True`: انتقال زیردسته‌ها به والد (پیش‌فرض)
    - `cascade=False & move_to_parent=False`: خطا اگر زیردسته داشته باشد
    """
    try:
        logger.info(f"🗑️ Deleting category: {category_id} (cascade={cascade}, move_to_parent={move_to_parent})")
        
        result = await knowledge_base_service.delete_category(
            category_id=category_id,
            cascade=cascade,
            move_to_parent=move_to_parent
        )
        
        message = f"دسته‌بندی '{result['category_name']}' با موفقیت حذف شد."
        
        if result['children_count'] > 0:
            if cascade:
                message += f" {len(result['deleted_categories'])} دسته‌بندی (شامل زیردسته‌ها) حذف شدند."
            elif move_to_parent:
                message += f" {len(result['moved_children'])} زیردسته به والد منتقل شدند."
        
        if result['articles_count'] > 0:
            if cascade:
                message += f" {len(result['affected_articles'])} مقاله حذف شدند."
            else:
                message += f" دسته‌بندی از {len(result['affected_articles'])} مقاله حذف شد."
        
        result['message'] = message
        
        logger.info(f"✅ {message}")
        
        return CategoryDeleteResult(**result)
        
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در حذف دسته‌بندی: {str(e)}"
        )


@router.get("/slug/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(
    slug: str,
    current_admin: Optional[Admin] = Depends(get_optional_admin)
):
    """
    دریافت دسته‌بندی با slug
    
    **دسترسی:** عمومی (برای مهمان‌ها فقط public categories)
    """
    try:
        logger.info(f"🔍 Fetching category by slug: {slug}")
        
        category = await knowledge_base_service.get_category_by_slug(slug)
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"دسته‌بندی با slug '{slug}' یافت نشد"
            )
        
        # بررسی دسترسی برای مهمان‌ها
        if not current_admin and not category.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="دسترسی به این دسته‌بندی محدود است"
            )
        
        # شمارش مقالات و زیردسته‌ها
        from app.domain.entities import KnowledgeBaseArticle
        articles_count = await KnowledgeBaseArticle.find({"category.id": str(category.id)}).count()
        children = await Category.find({"parent.$id": category.id}).to_list()
        
        return CategoryResponse(
            id=str(category.id),
            name=category.name,
            slug=category.slug,
            description=category.description,
            parent_id=str(category.parent.ref.id) if category.parent else None,
            is_public=category.is_public,
            created_at=category.created_at,
            updated_at=category.updated_at,
            articles_count=articles_count,
            children_count=len(children)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching category by slug: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در دریافت دسته‌بندی: {str(e)}"
        )
