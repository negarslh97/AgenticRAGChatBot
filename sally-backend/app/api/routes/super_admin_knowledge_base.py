from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from pathlib import Path
import uuid
import openai
import json

from app.domain.entities import KnowledgeBaseArticle, ArticleStatus, Admin, ArticleVisibility, ArticleCategory, ArticleTag, Category, Tag
import markdown  # For markdown to HTML conversion
from app.api.dependencies import get_current_admin
from app.core.permissions import get_current_admin_with_permission, Permission
from app.core.config import settings
from app.services.sync_service import MongoToGitSync
from app.docs_as_code.config import get_default_config
from app.docs_as_code.git_manager import GitManager
from app.docs_as_code.monitoring import get_system_stats
from app.services.knowledge_base_service import knowledge_base_service, get_or_create_tags
from app.utils.text_extraction import (
    extract_text_from_file,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_excel,
    extract_text_from_csv,
    TEXT_EXTRACTION_AVAILABLE
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def generate_metadata_from_ai(title: str, content: str) -> dict:
    """Generate metadata from AI for uploaded file content using LangChain."""
    from app.infrastructure.langchain_utils import langchain_service

    try:
        return await langchain_service.generate_metadata(title, content)
    except Exception as e:
        # Return default metadata if AI fails
        return {
            "summary": f"محتوای استخراج شده از فایل: {title}",
            "tags": ["آپلود شده", "فایل"],
            "suggested_category": "عمومی",
            "suggested_visibility": "internal"
        }

# --- Pydantic Schemas for admin Knowledge Base ---

class ArticleCreate(BaseModel):
    title: str
    content_markdown: str
    content_html: Optional[str] = None
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tag_names: List[str] = []
    status: Optional[ArticleStatus] = ArticleStatus.DRAFT
    visibility: Optional[ArticleVisibility] = None

class ArticleUpdate(BaseModel):
    title: str
    content_markdown: str
    content_html: Optional[str] = None
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tag_names: List[str] = []
    status: Optional[ArticleStatus] = None
    visibility: Optional[ArticleVisibility] = None

class MarkdownNodeResponse(BaseModel):
    id: str
    title: str
    level: int
    content: str
    parent_id: Optional[str]
    path: str
    order: int
    children: List['MarkdownNodeResponse'] = []

class MarkdownTreeResponse(BaseModel):
    article_id: str
    root_nodes: List[MarkdownNodeResponse]

class ArticleResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str
    title: str
    content_markdown: str
    content_html: str
    summary: Optional[str] = None
    status: str  # Use string instead of enum
    visibility: Optional[str] = None  # Use string instead of enum
    author_id: str
    category: Optional[Dict[str, Any]] = None  # Use dict instead of ArticleCategory
    tags: List[Dict[str, Any]] = []  # Use dict instead of ArticleTag
    version: int
    created_at: str  # Use string instead of datetime
    updated_at: str  # Use string instead of datetime
    published_at: Optional[str] = None  # Use string instead of datetime
    markdown_tree: Optional[MarkdownTreeResponse] = None

class ArticlePublishRequest(BaseModel):
    visibility: ArticleVisibility

class ArticleHistoryItem(BaseModel):
    commit_hash: str
    author_name: str
    author_email: str
    message: str
    timestamp: datetime
    changes: List[str] = []

class SyncStatusResponse(BaseModel):
    status: str
    last_sync: Optional[str] = None  # Change to string to handle None values
    pending_operations: int = 0
    health_status: str = "healthy"
    embedder_model: str = "text-embedding-3-small"
    embedder_api_key_set: bool = False

class FileUploadResponse(BaseModel):
    success: bool
    markdown_content: str
    title: str
    summary: str
    suggested_tags: List[str] = []
    suggested_category: Optional[str] = None
    error: Optional[str] = None


# --- API Endpoints ---

@router.post("/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED, tags=["Knowledge Base Management"])
async def create_article(
    article_data: ArticleCreate,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Create a new knowledge base article.
    Accessible by admin and SuperAdmin.
    Only SuperAdmin can create published articles directly.
    """
    try:
        # Use the service to create article
        article = await knowledge_base_service.create_article_from_text(
            title=article_data.title,
            content=article_data.content_markdown,
            author=current_user,
            category_id=article_data.category_id,
            tag_names=article_data.tag_names or [],
            is_markdown=True,
            generate_summary=bool(article_data.summary),  # Generate if not provided
            auto_publish=(article_data.status == ArticleStatus.PUBLISHED)
        )

        # Override status and visibility if explicitly set in request
        if article_data.status and article_data.status != article.status:
            updates = {"status": article_data.status}
            if article_data.visibility:
                updates["visibility"] = article_data.visibility
            article = await knowledge_base_service.repository.update_article(
                str(article.id), updates, str(current_user.id)
            )

        return ArticleResponse(
            id=str(article.id),
            title=article.title,
            content_markdown=article.content_markdown,
            content_html=article.content_html,
            summary=article.summary,
            status=article.status,
            visibility=article.visibility,
            author_id=article.author_id,
            category=article.category.model_dump() if article.category else None,
            tags=[tag.model_dump() for tag in article.tags],
            version=article.version,
            created_at=article.created_at.isoformat() if article.created_at else None,
            updated_at=article.updated_at.isoformat() if article.updated_at else None,
            published_at=article.published_at.isoformat() if article.published_at else None
        )

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        print(f"Error creating article: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating article: {str(e)}")

@router.post("/articles/upload", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED, tags=["Knowledge Base Management"])
async def upload_kb_file(
    file: UploadFile = File(...),
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Upload a file to create a new knowledge base article as a draft with AI-generated metadata.
    Accessible by SuperAdmin only.
    """
    print(f"📁 شروع آپلود فایل: {file.filename}")

    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    file_extension = Path(original_filename).suffix.lower()
    new_filename = f"{file_id}{file_extension}"
    file_path = upload_dir / new_filename

    # Save file to uploads directory
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    print(f"💾 فایل ذخیره شد: {file_path}")

    # Extract text content based on file type
    article_content = ""
    article_title = original_filename

    if file_extension == ".txt":
        # For TXT files, read content directly
        try:
            article_content = file_content.decode("utf-8")
            print(f"📄 فایل TXT خوانده شد، طول: {len(article_content)} کاراکتر")
        except UnicodeDecodeError:
            article_content = "Unable to decode file content"
            print("❌ خطا در دیکد فایل TXT")
    elif file_extension == ".pdf":
        article_content = extract_text_from_pdf(file_path)
        print(f"📄 متن از PDF استخراج شد، طول: {len(article_content)} کاراکتر")
    elif file_extension in [".docx", ".doc"]:
        article_content = extract_text_from_docx(file_path)
        print(f"📄 متن از DOCX استخراج شد، طول: {len(article_content)} کاراکتر")
    elif file_extension in [".xlsx", ".xls"]:
        article_content = extract_text_from_excel(file_path)
        print(f"📄 متن از Excel استخراج شد، طول: {len(article_content)} کاراکتر")
    elif file_extension == ".csv":
        article_content = extract_text_from_csv(file_path)
        print(f"📄 متن از CSV استخراج شد، طول: {len(article_content)} کاراکتر")
    else:
        # For unsupported files, store file path info
        article_content = f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {len(file_content)} bytes\n\nContent extraction not supported for {file_extension} files."
        print(f"⚠️ نوع فایل پشتیبانی نمی‌شود: {file_extension}")

    # Generate AI metadata if content was extracted
    ai_metadata = None
    print(f"🔍 شروع تولید فراداده AI برای فایل: {original_filename}")
    print(f"📄 طول محتوا استخراج شده: {len(article_content) if article_content else 0} کاراکتر")

    if article_content and article_content != f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {len(file_content)} bytes\n\nContent extraction not supported for {file_extension} files.":
        print("🤖 شروع فراخوانی AI برای تولید فراداده...")
        try:
            ai_metadata = await generate_metadata_from_ai(article_title, article_content)
            print(f"✅ AI فراداده تولید کرد: {bool(ai_metadata)}")
        except Exception as e:
            # Continue with default metadata if AI generation fails
            print(f"❌ خطا در تولید فراداده AI: {str(e)}")
            pass
    else:
        print("⚠️ محتوا استخراج نشد یا نامعتبر است - از فراداده پیش‌فرض استفاده می‌شود")

    # Generate HTML from markdown if not provided (for text content)
    content_html = markdown.markdown(article_content) if article_content else ""

    # Handle category from AI metadata
    category = None
    if ai_metadata and ai_metadata.get("suggested_category"):
        # Find category by name (since AI suggests name, not ID)
        cat = await Category.find_one(Category.name == ai_metadata["suggested_category"])
        if cat:
            category = ArticleCategory(id=str(cat.id), name=cat.name, slug=cat.slug)

    # Handle tags from AI metadata
    tag_names = ai_metadata.get("tags", []) if ai_metadata else ["آپلود شده", file_extension[1:]]
    tags = await get_or_create_tags(tag_names)

    # Create article with extracted content and AI-generated metadata
    new_article = KnowledgeBaseArticle(
        title=article_title,
        content_markdown=article_content,
        content_html=content_html,
        summary=ai_metadata.get("summary") if ai_metadata else f"محتوای استخراج شده از فایل: {original_filename}",
        category=category,
        tags=tags,
        author_id=str(current_user.id),
        status=ArticleStatus.DRAFT,
        visibility=None
    )
    await new_article.insert()
    new_article.id = str(new_article.id)

    # Sync to Weaviate فقط برای مقالات منتشر شده
    if new_article.status == ArticleStatus.PUBLISHED:
        try:
            from app.infrastructure.knowledge_base_repository import KnowledgeBaseRepository
            repo = KnowledgeBaseRepository()
            await repo._sync_to_weaviate(new_article, "create")
            print(f"✅ Article {new_article.id} synced to Weaviate (PUBLISHED)")
        except Exception as sync_error:
            print(f"⚠️ خطا در sync با Weaviate: {str(sync_error)}")
    else:
        print(f"ℹ️ Article {new_article.id} is {new_article.status} - not synced to Weaviate")

    # Sync to Git repository (disabled - empty repository)
    print(f"Article {new_article.id} created successfully (Git sync disabled - empty repository)")

    return ArticleResponse(
        id=str(new_article.id),
        title=new_article.title,
        content_markdown=new_article.content_markdown,
        content_html=new_article.content_html,
        summary=new_article.summary,
        status=new_article.status,
        visibility=new_article.visibility,
        author_id=new_article.author_id,
        category=new_article.category.model_dump() if new_article.category else None,
        tags=[tag.model_dump() for tag in new_article.tags],
        version=new_article.version,
        created_at=new_article.created_at.isoformat() if new_article.created_at else None,
        updated_at=new_article.updated_at.isoformat() if new_article.updated_at else None,
        published_at=new_article.published_at.isoformat() if new_article.published_at else None
    )

@router.post("/articles/{article_id}/publish", response_model=ArticleResponse, tags=["Knowledge Base Management"])
async def publish_article(
    article_id: str,
    publish_request: ArticlePublishRequest,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.PUBLISH_ARTICLES))
):
    """
    Publish a draft article with specified visibility.
    Accessible only by SuperAdmin.
    """
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    
    if article.status != ArticleStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft articles can be published"
        )
    
    article.status = ArticleStatus.PUBLISHED
    article.visibility = publish_request.visibility
    article.published_at = datetime.utcnow()
    article.publisher_id = str(current_user.id)

    await article.save()
    article.id = str(article.id)

    # Schedule vectorization job for the published article
    from app.docs_as_code.background_jobs import schedule_vectorize_article
    try:
        job_id = await schedule_vectorize_article(article_id)
        print(f"Article {article_id} published successfully. Vectorization job scheduled: {job_id}")
    except Exception as e:
        print(f"Warning: Failed to schedule vectorization job for article {article_id}: {str(e)}")
        # Don't fail the publish operation if job scheduling fails

    # Sync to Git repository (disabled - empty repository)
    print(f"Article {article_id} published successfully (Git sync disabled - empty repository)")

    return ArticleResponse(
        id=str(article.id),
        title=article.title,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        summary=article.summary,
        status=article.status,
        visibility=article.visibility,
        author_id=article.author_id,
        category=article.category.model_dump() if article.category else None,
        tags=[tag.model_dump() for tag in article.tags],
        version=article.version,
        created_at=article.created_at.isoformat() if article.created_at else None,
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        published_at=article.published_at.isoformat() if article.published_at else None
    )

@router.get("/articles", response_model=List[ArticleResponse], tags=["Knowledge Base Management"])
async def list_articles(
    status_filter: Optional[ArticleStatus] = None,
    current_user: Admin = Depends(get_current_admin)
):
    """
    List all knowledge base articles. admins can see all articles.
    Can be filtered by status (e.g., 'draft', 'published').
    """
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    articles = await KnowledgeBaseArticle.find(query).sort(-KnowledgeBaseArticle.updated_at).to_list()

    # Transform to ArticleResponse format
    response_articles = []
    for article in articles:
        # Use author_id directly from the article
        author_id = article.author_id

        response_articles.append(ArticleResponse(
            id=str(article.id),
            title=article.title,
            content_markdown=article.content_markdown,
            content_html=article.content_html,
            summary=article.summary,
            status=article.status.value if hasattr(article.status, 'value') else str(article.status),
            visibility=article.visibility.value if article.visibility and hasattr(article.visibility, 'value') else (str(article.visibility) if article.visibility else None),
            author_id=author_id,
            category=article.category.model_dump() if article.category else None,
            tags=[tag.model_dump() for tag in article.tags] if article.tags else [],
            version=article.version,
            created_at=article.created_at.isoformat() if article.created_at else None,
            updated_at=article.updated_at.isoformat() if article.updated_at else None,
            published_at=article.published_at.isoformat() if article.published_at else None
        ))
    return response_articles

@router.get("/articles/{article_id}", response_model=ArticleResponse, tags=["Knowledge Base Management"])
async def get_article(
    article_id: str,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Get a single article by its ID.
    """
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    # دریافت ساختار درختی Markdown اگر وجود داشته باشد
    markdown_tree = None
    try:
        from app.infrastructure.markdown_parser import markdown_parser
        tree = markdown_parser.parse_to_tree(
            article.content_markdown,
            str(article.id),
            article_title=article.title
        )

        if tree.get_all_nodes():
            # تبدیل به response format
            def convert_node(node):
                return MarkdownNodeResponse(
                    id=node.id,
                    title=node.title,
                    level=node.level,
                    content=node.content,
                    parent_id=node.parent_id,
                    path=node.path,
                    order=node.order,
                    children=[convert_node(child) for child in node.children]
                )

            markdown_tree = MarkdownTreeResponse(
                article_id=str(article.id),
                root_nodes=[convert_node(node) for node in tree.root_nodes]
            )
    except Exception as e:
        # در صورت خطا، ساختار درختی خالی برمی‌گردانیم
        pass

    return ArticleResponse(
        id=str(article.id),
        title=article.title,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        summary=article.summary,
        status=article.status,
        visibility=article.visibility,
        author_id=article.author_id,
        category=article.category.model_dump() if article.category else None,
        tags=[tag.model_dump() for tag in article.tags],
        version=article.version,
        created_at=article.created_at.isoformat() if article.created_at else None,
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        published_at=article.published_at.isoformat() if article.published_at else None,
        markdown_tree=markdown_tree
    )

@router.put("/articles/{article_id}", response_model=ArticleResponse, tags=["Knowledge Base Management"])
async def update_article(
    article_id: str,
    article_data: ArticleUpdate,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Update an article.
    - admins can only update their own DRAFT articles.
    - SuperAdmins can update any article.
    """
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    # Check permissions for status and visibility changes
    if article_data.status is not None and article_data.status != article.status:
        # Only SuperAdmin can change status to PUBLISHED
        if article_data.status == ArticleStatus.PUBLISHED and current_user.role_name != "SuperAdmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SuperAdmin can publish articles."
            )

        # Require visibility when publishing
        if article_data.status == ArticleStatus.PUBLISHED and not article_data.visibility:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Visibility is required when publishing an article."
            )

    if current_user.role_name != "SuperAdmin":
        # Check if the current user is the author (using Link comparison)
        if article.author_id != str(current_user.id) or article.status != ArticleStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own draft articles."
            )

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
            logger.info(f"✅ دسته‌بندی '{cat.name}' برای مقاله تنظیم شد")
        else:
            logger.warning(f"⚠️ دسته‌بندی با ID '{article_data.category_id}' یافت نشد")

    # Handle tags
    tags = await get_or_create_tags(article_data.tag_names)

    # Update article fields
    article.title = article_data.title
    article.content_markdown = article_data.content_markdown
    article.content_html = content_html
    article.summary = article_data.summary
    article.category = category
    article.tags = tags

    # Update status and visibility if provided
    if article_data.status is not None:
        article.status = article_data.status
        # Set published timestamp if status changed to PUBLISHED
        if article_data.status == ArticleStatus.PUBLISHED and article.status != ArticleStatus.PUBLISHED:
            article.published_at = datetime.utcnow()
            article.publisher_id = str(current_user.id)

    if article_data.visibility is not None:
        article.visibility = article_data.visibility

    article.updated_at = datetime.utcnow()
    article.version += 1

    await article.save()

    # Sync to Git repository (disabled - empty repository)
    print(f"Article {article_id} updated successfully (Git sync disabled - empty repository)")

    return ArticleResponse(
        id=str(article.id),
        title=article.title,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        summary=article.summary,
        status=article.status,
        visibility=article.visibility,
        author_id=article.author_id,
        category=article.category.model_dump() if article.category else None,
        tags=[tag.model_dump() for tag in article.tags],
        version=article.version,
        created_at=article.created_at.isoformat() if article.created_at else None,
        updated_at=article.updated_at.isoformat() if article.updated_at else None,
        published_at=article.published_at.isoformat() if article.published_at else None
    )

@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Knowledge Base Management"])
async def delete_article(
    article_id: str,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.DELETE_ARTICLES))
):
    """
    Delete an article from both MongoDB and Weaviate.
    Accessible only by SuperAdmin.
    """
    try:
        # استفاده از سرویس برای حذف از هر دو دیتابیس
        success = await knowledge_base_service.delete_article(article_id, current_user)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

        # Sync deletion to Git repository
        try:
            config = get_default_config()
            sync_service = MongoToGitSync(config)
            author_info = {
                "name": current_user.full_name,
                "email": current_user.email
            }
            # For deletion, we need to handle it differently - remove the Markdown file
            # This would require additional logic in the sync service
            # For now, we'll just log that deletion sync is not fully implemented
            print(f"Article {article_id} deleted from both databases - Git sync for deletions not yet implemented")
        except Exception as e:
            # Log error but don't fail the request
            print(f"Git sync failed for article deletion {article_id}: {str(e)}")

        return None

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete article: {str(e)}")

@router.get("/articles/{article_id}/history", response_model=List[ArticleHistoryItem], tags=["Knowledge Base Management"])
async def get_article_history(
    article_id: str,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Get version history for an article from Git repository.
    """
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    
    try:
        git_manager = GitManager()
        
        # Determine the file path for this article
        if article.category:
            file_path = git_manager.repo_path / article.category['slug'] / f"{article.title.lower().replace(' ', '-')}.md"
        else:
            file_path = git_manager.repo_path / f"{article.title.lower().replace(' ', '-')}.md"
        
        # Get commit history for the file
        commits = await git_manager.get_file_history(file_path)
        
        history_items = []
        for commit in commits:
            history_items.append(ArticleHistoryItem(
                commit_hash=commit['hash'],
                author_name=commit['author_name'],
                author_email=commit['author_email'],
                message=commit['message'],
                timestamp=commit['timestamp'],
                changes=commit.get('changes', [])
            ))
        
        return history_items
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching article history: {str(e)}"
        )

@router.get("/sync/status", response_model=SyncStatusResponse, tags=["Knowledge Base Management"])
async def get_sync_status(
    current_user: Admin = Depends(get_current_admin)
):
    """
    Get the current synchronization status between MongoDB and Git repository.
    """
    try:
        stats = await get_system_stats()
        
        # Debug log
        embedder_model = settings.embedder_model_loaded
        embedder_key = settings.embedder_api_key_loaded
        logger.info(f"🔍 Sync Status - Embedder Model: {embedder_model}")
        logger.info(f"🔍 Sync Status - API Key Set: {bool(embedder_key)}")
        if embedder_key:
            logger.info(f"🔍 API Key Preview: {embedder_key[:10]}...")
        
        return SyncStatusResponse(
            status=stats['health']['status'],
            last_sync=stats['last_sync'],
            pending_operations=stats['pending_operations'],
            health_status=stats['health']['status'],
            embedder_model=embedder_model,
            embedder_api_key_set=bool(embedder_key)
        )
        
    except Exception as e:
        logger.error(f"Error fetching sync status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching sync status: {str(e)}"
        )

@router.get("/sync/check-articles", tags=["Knowledge Base Management"])
async def check_articles_sync_status(
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Check which published articles are not synced to Weaviate.
    🔥 بهینه‌سازی شده: از یک connection واحد برای بررسی همه مقالات استفاده می‌کند
    """
    try:
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository
        
        # Get all published articles
        published_articles = await KnowledgeBaseArticle.find(
            KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED
        ).to_list()
        
        total_published = len(published_articles)
        
        if total_published == 0:
            return {
                "total_published": 0,
                "synced": 0,
                "not_synced": 0,
                "not_synced_articles": [],
                "sync_percentage": 100
            }
        
        # 🔥 استفاده از متد بهینه‌سازی شده که یک connection واحد استفاده می‌کند
        article_ids = [str(article.id) for article in published_articles]
        sync_status = await knowledge_base_repository.check_multiple_articles_in_weaviate(article_ids)
        
        # محاسبه تعداد همگام‌سازی شده و لیست مقالات همگام نشده
        synced_count = 0
        not_synced = []
        
        for article in published_articles:
            article_id = str(article.id)
            if sync_status.get(article_id, False):
                synced_count += 1
            else:
                not_synced.append({
                    "id": article_id,
                    "title": article.title,
                    "published_at": article.published_at.isoformat() if article.published_at else None
                })
        
        return {
            "total_published": total_published,
            "synced": synced_count,
            "not_synced": len(not_synced),
            "not_synced_articles": not_synced,
            "sync_percentage": (synced_count / total_published * 100) if total_published > 0 else 100
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking sync status: {str(e)}"
        )

@router.get("/sync/detailed-status", tags=["Knowledge Base Management"])
async def get_detailed_sync_status(
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Get detailed sync status including:
    - New articles (never synced)
    - Modified articles (updated after last sync)
    - Archived articles (in Weaviate but archived in MongoDB)
    """
    try:
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository
        
        # Get all published articles
        published_articles = await KnowledgeBaseArticle.find(
            KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED
        ).to_list()
        
        # Get all archived articles
        archived_articles = await KnowledgeBaseArticle.find(
            KnowledgeBaseArticle.status == ArticleStatus.ARCHIVED
        ).to_list()
        
        # Check sync status
        all_article_ids = [str(article.id) for article in published_articles]
        archived_ids = [str(article.id) for article in archived_articles]
        sync_status = await knowledge_base_repository.check_multiple_articles_in_weaviate(all_article_ids + archived_ids)
        
        new_articles = []
        modified_articles = []
        synced_articles = []
        archived_in_weaviate = []
        
        # Check published articles
        for article in published_articles:
            article_id = str(article.id)
            is_in_weaviate = sync_status.get(article_id, False)
            
            if not is_in_weaviate:
                # Article never synced
                new_articles.append({
                    "id": article_id,
                    "title": article.title,
                    "created_at": article.created_at.isoformat() if article.created_at else None,
                    "published_at": article.published_at.isoformat() if article.published_at else None
                })
            else:
                # Check if article was modified after last sync
                last_updated = article.updated_at or article.published_at
                last_synced_at = article.last_synced_at if hasattr(article, 'last_synced_at') else None
                
                if last_synced_at and last_updated and last_updated > last_synced_at:
                    modified_articles.append({
                        "id": article_id,
                        "title": article.title,
                        "updated_at": last_updated.isoformat(),
                        "last_synced_at": last_synced_at.isoformat()
                    })
                else:
                    synced_articles.append({
                        "id": article_id,
                        "title": article.title
                    })
        
        # Check archived articles that are still in Weaviate
        for article in archived_articles:
            article_id = str(article.id)
            if sync_status.get(article_id, False):
                archived_in_weaviate.append({
                    "id": article_id,
                    "title": article.title,
                    "archived_at": article.updated_at.isoformat() if article.updated_at else None
                })
        
        return {
            "total_published": len(published_articles),
            "new_articles": {
                "count": len(new_articles),
                "articles": new_articles[:10]  # Show first 10
            },
            "modified_articles": {
                "count": len(modified_articles),
                "articles": modified_articles[:10]  # Show first 10
            },
            "synced_articles": {
                "count": len(synced_articles)
            },
            "archived_in_weaviate": {
                "count": len(archived_in_weaviate),
                "articles": archived_in_weaviate[:10]  # Show first 10
            },
            "needs_action": len(new_articles) + len(modified_articles) + len(archived_in_weaviate) > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting detailed sync status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting detailed sync status: {str(e)}"
        )

@router.post("/sync/remove-archived", tags=["Knowledge Base Management"])
async def remove_archived_from_weaviate(
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Remove archived articles from Weaviate
    """
    try:
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository
        
        # Get all archived articles
        archived_articles = await KnowledgeBaseArticle.find(
            KnowledgeBaseArticle.status == ArticleStatus.ARCHIVED
        ).to_list()
        
        if not archived_articles:
            return {
                "success": True,
                "removed_count": 0,
                "message": "هیچ مقاله آرشیو شده‌ای یافت نشد"
            }
        
        # Check which ones are in Weaviate
        archived_ids = [str(article.id) for article in archived_articles]
        sync_status = await knowledge_base_repository.check_multiple_articles_in_weaviate(archived_ids)
        
        removed_count = 0
        errors = []
        
        for article in archived_articles:
            article_id = str(article.id)
            if sync_status.get(article_id, False):
                try:
                    await knowledge_base_repository.delete_article_from_weaviate(article_id)
                    removed_count += 1
                    logger.info(f"✅ مقاله آرشیو شده '{article.title}' از Weaviate حذف شد")
                except Exception as e:
                    errors.append(f"{article.title}: {str(e)}")
                    logger.error(f"❌ خطا در حذف مقاله '{article.title}': {e}")
        
        return {
            "success": True,
            "removed_count": removed_count,
            "total_archived": len(archived_articles),
            "errors": errors if errors else None,
            "message": f"{removed_count} مقاله آرشیو شده از Weaviate حذف شد"
        }
        
    except Exception as e:
        logger.error(f"Error removing archived articles: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing archived articles: {str(e)}"
        )

@router.post("/sync/sync-all-articles", tags=["Knowledge Base Management"])
async def sync_all_articles_to_weaviate(
    force: bool = False,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.PUBLISH_ARTICLES))
):
    """
    Sync all published articles to Weaviate.
    
    Args:
        force: If True, re-sync all articles even if already synced. Default is False (only sync missing articles).
    """
    try:
        from app.docs_as_code.background_jobs import schedule_vectorize_article
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository
        
        # Get all published articles
        published_articles = await KnowledgeBaseArticle.find(
            KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED
        ).to_list()
        
        job_ids = []
        skipped_count = 0
        
        for article in published_articles:
            try:
                article_id = str(article.id)
                
                # Check if article already exists in Weaviate (unless force=True)
                if not force:
                    is_synced = await knowledge_base_repository.check_article_in_weaviate(article_id)
                    if is_synced:
                        logger.info(f"⏭️ مقاله '{article.title}' قبلاً sync شده، رد می‌شود")
                        skipped_count += 1
                        continue
                
                # Schedule the job
                job_id = await schedule_vectorize_article(article_id)
                job_ids.append(job_id)
                logger.info(f"✅ Job برای مقاله '{article.title}' ایجاد شد: {job_id}")
                
            except Exception as e:
                logger.error(f"Failed to schedule job for article {article.id}: {str(e)}")
        
        return {
            "success": True,
            "total_articles": len(published_articles),
            "jobs_scheduled": len(job_ids),
            "skipped": skipped_count,
            "job_ids": job_ids,
            "message": f"Scheduled {len(job_ids)} vectorization jobs, skipped {skipped_count} already synced articles"
        }
        
    except Exception as e:
        logger.error(f"Error in sync_all_articles: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scheduling sync jobs: {str(e)}"
        )

@router.get("/weaviate/node/{node_uuid}", tags=["Knowledge Base Management"])
async def get_weaviate_node_details(
    node_uuid: str,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Get detailed information about a specific Weaviate node including vector.
    """
    try:
        from app.infrastructure.database.weaviate_connector import WeaviateMongoDBConnector
        from app.core.weaviate_utils import get_weaviate_collection_name
        import uuid as uuid_lib

        # Create connector instance and connect
        weaviate_connector = WeaviateMongoDBConnector()
        weaviate_connector.connect_weaviate()

        if not weaviate_connector.weaviate_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot connect to Weaviate"
            )

        # Get collection using dynamic name
        collection_name = get_weaviate_collection_name()
        collection = weaviate_connector.weaviate_client.collections.get(collection_name)
        
        # Get specific object with UUID
        try:
            obj = collection.query.fetch_object_by_id(uuid_lib.UUID(node_uuid), include_vector=True)
            
            if not obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Node with UUID {node_uuid} not found"
                )
            
            # Prepare detailed response
            return {
                "uuid": str(obj.uuid),
                "properties": obj.properties,
                "vector": obj.vector.get("default") if obj.vector else None,
                "vector_length": len(obj.vector.get("default")) if obj.vector and obj.vector.get("default") else 0,
                "metadata": {
                    "creation_time": obj.metadata.creation_time.isoformat() if obj.metadata and obj.metadata.creation_time else None,
                    "last_update_time": obj.metadata.last_update_time.isoformat() if obj.metadata and obj.metadata.last_update_time else None,
                }
            }
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid UUID format: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ خطا در دریافت جزئیات گره: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching node details: {str(e)}"
        )

@router.get("/weaviate/contents", tags=["Knowledge Base Management"])
async def get_weaviate_contents(
    limit: int = 100,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Get all contents stored in Weaviate for inspection.
    """
    try:
        from app.infrastructure.database.weaviate_connector import WeaviateMongoDBConnector
        from app.core.weaviate_utils import get_weaviate_collection_name

        # Create connector instance and connect
        weaviate_connector = WeaviateMongoDBConnector()
        weaviate_connector.connect_weaviate()

        if not weaviate_connector.weaviate_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cannot connect to Weaviate"
            )

        # Get collection using dynamic name
        collection_name = get_weaviate_collection_name()

        # Check if collection exists
        if not weaviate_connector.weaviate_client.collections.exists(collection_name):
            return {
                "total_nodes": 0,
                "returned_nodes": 0,
                "articles_count": 0,
                "articles": [],
                "nodes": [],
                "error": f"Collection '{collection_name}' does not exist. Please create it first."
            }

        collection = weaviate_connector.weaviate_client.collections.get(collection_name)

        # Query all objects with limit
        response = collection.query.fetch_objects(limit=limit)
        
        items = []
        for obj in response.objects:
            items.append({
                "uuid": str(obj.uuid),
                "article_id": obj.properties.get("article_id"),
                "title": obj.properties.get("title"),
                "level": obj.properties.get("level"),
                "content": obj.properties.get("content", "")[:200] + "..." if len(obj.properties.get("content", "")) > 200 else obj.properties.get("content", ""),
                "path": obj.properties.get("path"),
                "order": obj.properties.get("order")
            })
        
        # Get total count
        total_response = collection.aggregate.over_all(total_count=True)
        total_count = total_response.total_count
        
        # Group by article_id
        articles_dict = {}
        for item in items:
            article_id = item.get("article_id")
            if article_id:
                if article_id not in articles_dict:
                    articles_dict[article_id] = {
                        "article_id": article_id,
                        "nodes_count": 0,
                        "titles": []
                    }
                articles_dict[article_id]["nodes_count"] += 1
                if item.get("level") == 0:  # Root node
                    articles_dict[article_id]["titles"].append(item.get("title"))
        
        logger.info(f"✅ دریافت {len(items)} گره از Weaviate (کل: {total_count})")
        
        return {
            "total_nodes": total_count,
            "returned_nodes": len(items),
            "articles_count": len(articles_dict),
            "articles": list(articles_dict.values()),
            "nodes": items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ خطا در دریافت محتویات Weaviate: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching Weaviate contents: {str(e)}"
        )

@router.post("/upload-convert", response_model=FileUploadResponse, tags=["Knowledge Base Management"])
async def upload_and_convert_file(
    file: UploadFile = File(...),
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Upload a file and convert it to Markdown format without creating an article.
    Returns the converted content for the editor.
    """
    print(f"🔄 شروع آپلود و تبدیل فایل: {file.filename}")

    # Create uploads directory if it doesn't exist
    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    file_extension = Path(original_filename).suffix.lower()
    new_filename = f"{file_id}{file_extension}"
    file_path = upload_dir / new_filename

    # Save file to uploads directory
    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    print(f"💾 فایل ذخیره شد برای تبدیل: {file_path}")

    # Extract text content based on file type
    article_content = ""
    article_title = original_filename

    if file_extension == ".txt":
        # For TXT files, read content directly
        try:
            article_content = file_content.decode("utf-8")
            print(f"📄 فایل TXT برای تبدیل خوانده شد، طول: {len(article_content)} کاراکتر")
        except UnicodeDecodeError:
            article_content = "Unable to decode file content"
            print("❌ خطا در دیکد فایل TXT برای تبدیل")
    elif file_extension == ".pdf":
        article_content = extract_text_from_pdf(file_path)
        print(f"📄 متن از PDF برای تبدیل استخراج شد، طول: {len(article_content)} کاراکتر")
    elif file_extension in [".docx", ".doc"]:
        article_content = extract_text_from_docx(file_path)
        print(f"📄 متن از DOCX برای تبدیل استخراج شد، طول: {len(article_content)} کاراکتر")
    elif file_extension in [".xlsx", ".xls"]:
        article_content = extract_text_from_excel(file_path)
        print(f"📄 متن از Excel برای تبدیل استخراج شد، طول: {len(article_content)} کاراکتر")
    elif file_extension == ".csv":
        article_content = extract_text_from_csv(file_path)
        print(f"📄 متن از CSV برای تبدیل استخراج شد، طول: {len(article_content)} کاراکتر")
    else:
        # For unsupported files, return error
        print(f"⚠️ نوع فایل پشتیبانی نمی‌شود برای تبدیل: {file_extension}")
        return FileUploadResponse(
            success=False,
            markdown_content="",
            title="",
            summary="",
            error=f"Unsupported file type: {file_extension}"
        )

    # Generate AI metadata if content was extracted
    ai_metadata = None
    print(f"🔍 شروع تولید فراداده AI برای تبدیل فایل: {original_filename}")
    print(f"📄 طول محتوا استخراج شده برای تبدیل: {len(article_content) if article_content else 0} کاراکتر")

    if article_content and article_content != f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {len(file_content)} bytes\n\nContent extraction not supported for {file_extension} files.":
        print("🤖 شروع فراخوانی AI برای تولید فراداده تبدیل...")
        try:
            ai_metadata = await generate_metadata_from_ai(article_title, article_content)
            print(f"✅ AI برای تبدیل فراداده تولید کرد: {bool(ai_metadata)}")
        except Exception as e:
            # Continue with default metadata if AI generation fails
            print(f"❌ خطا در تولید فراداده AI برای تبدیل: {str(e)}")
            pass
    else:
        print("⚠️ محتوا استخراج نشد یا نامعتبر است برای تبدیل - از فراداده پیش‌فرض استفاده می‌شود")

    # Clean up the uploaded file
    try:
        file_path.unlink()
    except:
        pass

    return FileUploadResponse(
        success=True,
        markdown_content=article_content,
        title=article_title,
        summary=ai_metadata.get("summary") if ai_metadata else f"محتوای استخراج شده از فایل: {original_filename}",
        suggested_tags=ai_metadata.get("tags", []) if ai_metadata else ["آپلود شده", file_extension[1:]],
        suggested_category=ai_metadata.get("suggested_category") if ai_metadata else None
    )


@router.post("/convert-to-markdown", tags=["Knowledge Base Management"])
async def convert_text_to_markdown(
    request: dict,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Convert plain text to structured Markdown using AI.
    Accessible by SuperAdmin and Admin with KB management permission.
    """
    try:
        title = request.get("title", "")
        content = request.get("content", "")

        if not content:
            raise HTTPException(status_code=400, detail="محتوا نمی‌تواند خالی باشد")

        print(f"🔄 شروع تبدیل متن به Markdown - عنوان: {title[:50]}...")
        print(f"📊 طول محتوا: {len(content)} کاراکتر")

        # Use LangChain service to convert text to markdown
        from app.infrastructure.langchain_utils import langchain_service

        markdown_content = await langchain_service.convert_text_to_markdown(title, content)

        print(f"✅ تبدیل به Markdown کامل شد - طول خروجی: {len(markdown_content)} کاراکتر")

        return {
            "success": True,
            "markdown_content": markdown_content,
            "original_length": len(content),
            "markdown_length": len(markdown_content)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ خطا در تبدیل متن به Markdown: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"خطا در تبدیل متن به Markdown: {str(e)}"
        )


@router.get("/articles/structure/{article_id}", tags=["Knowledge Base Management"])
async def get_article_structure(
    article_id: str,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_PUBLIC_KB))
):
    """
    استخراج ساختار درختی از محتوای Markdown مقاله برای پیمایش

    Args:
        article_id: شناسه مقاله

    Returns:
        ساختار درختی شامل هدرها و لینک‌ها
    """
    try:
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository

        structure = await knowledge_base_repository.extract_markdown_structure(article_id)

        if "error" in structure:
            raise HTTPException(status_code=404, detail=structure["error"])

        return {
            "success": True,
            "structure": structure
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ خطا در دریافت ساختار مقاله {article_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"خطا در دریافت ساختار مقاله: {str(e)}"
        )


@router.get("/articles/structures", tags=["Knowledge Base Management"])
async def get_articles_with_structures(
    limit: int = 50,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.VIEW_PUBLIC_KB))
):
    """
    دریافت لیست مقالات با ساختار درختی آن‌ها

    Args:
        limit: حداکثر تعداد مقالات

    Returns:
        لیست مقالات با ساختار درختی
    """
    try:
        from app.infrastructure.knowledge_base_repository import knowledge_base_repository

        articles_with_structure = await knowledge_base_repository.get_articles_with_structure(limit)

        return {
            "success": True,
            "articles": articles_with_structure,
            "total": len(articles_with_structure)
        }

    except Exception as e:
        logger.error(f"❌ خطا در دریافت مقالات با ساختار: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"خطا در دریافت مقالات با ساختار: {str(e)}"
        )
