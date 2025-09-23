from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from pathlib import Path
import sys
import os
import uuid
import openai
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import text extraction libraries
try:
    from PyPDF2 import PdfReader
    from docx import Document
    import openpyxl
    TEXT_EXTRACTION_AVAILABLE = True
except ImportError:
    TEXT_EXTRACTION_AVAILABLE = False

from app.domain.entities_refactored import KnowledgeBaseArticle, ArticleStatus, Admin, ArticleVisibility, AdminRole, ArticleCategory, ArticleTag, Category, Tag
import markdown  # For markdown to HTML conversion
from app.api.dependencies import get_current_admin
from app.core.permissions import get_current_admin_with_permission, Permission
from app.core.config import settings
from app.docs_as_code.sync_service import MongoToGitSync
from app.docs_as_code.git_manager import GitManager
from app.docs_as_code.monitoring import get_system_stats

router = APIRouter()

# --- Helper Functions for Text Extraction and AI Generation ---

def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file."""
    if not TEXT_EXTRACTION_AVAILABLE:
        return "Text extraction libraries not available"

    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"


def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from DOCX file."""
    if not TEXT_EXTRACTION_AVAILABLE:
        return "Text extraction libraries not available"

    try:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting DOCX text: {str(e)}"


def extract_text_from_excel(file_path: Path) -> str:
    """Extract text from Excel file."""
    if not TEXT_EXTRACTION_AVAILABLE:
        return "Text extraction libraries not available"

    try:
        wb = openpyxl.load_workbook(file_path)
        text = ""
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            text += f"Sheet: {sheet_name}\n"
            for row in sheet.iter_rows(values_only=True):
                row_text = "\t".join(str(cell) for cell in row if cell is not None)
                if row_text.strip():
                    text += row_text + "\n"
            text += "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting Excel text: {str(e)}"


def extract_text_from_csv(file_path: Path) -> str:
    """Extract text from CSV file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            return f"Error extracting CSV text: {str(e)}"
    except Exception as e:
        return f"Error extracting CSV text: {str(e)}"


async def generate_metadata_from_ai(title: str, content: str) -> dict:
    """Generate metadata from AI for uploaded file content."""
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(
            api_key=settings.openai_api_key_loaded,
            base_url=settings.openai_base_url_loaded,
        )

        prompt_template = f"""
You are an expert content strategist for a knowledge base. Your task is to analyze the following article and generate structured metadata in Persian (Farsi).

**Instructions:**
1. Generate a concise, professional **summary**.
2. Generate 3 to 5 relevant **tags**.
3. Suggest a **category** from the provided list.
4. Suggest a **visibility** level based on the content.
5. Your output **MUST** be a single, valid JSON object and nothing else.

**Available Options:**
- Categories: ["راهنمای محصول", "مشکلات فنی", "حساب کاربری و صورتحساب", "عمومی"]
- Visibility: ["public", "customer", "internal"]

**Article to Analyze:**
- Title: {title}
- Content: {content}

**Required JSON Output:**
{{
  "summary": "...",
  "tags": ["...", "..."],
  "suggested_category": "...",
  "suggested_visibility": "..."
}}
"""

        # Make API call
        response = client.chat.completions.create(
            model=settings.openai_model_loaded or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates metadata for knowledge base articles."},
                {"role": "user", "content": prompt_template}
            ],
            max_tokens=500,
            temperature=0.7,
        )

        # Parse AI response
        ai_response = response.choices[0].message.content.strip()
        metadata = json.loads(ai_response)
        return metadata

    except openai.OpenAIError as e:
        # Return default metadata if AI fails
        return {
            "summary": f"محتوای استخراج شده از فایل: {title}",
            "tags": ["آپلود شده", "فایل"],
            "suggested_category": "عمومی",
            "suggested_visibility": "internal"
        }
    except Exception as e:
        # Return default metadata if parsing fails
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

class ArticleUpdate(BaseModel):
    title: str
    content_markdown: str
    content_html: Optional[str] = None
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tag_names: List[str] = []

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
    last_sync: Optional[datetime] = None
    pending_operations: int = 0
    health_status: str = "healthy"

class FileUploadResponse(BaseModel):
    success: bool
    markdown_content: str
    title: str
    summary: str
    suggested_tags: List[str] = []
    suggested_category: Optional[str] = None
    error: Optional[str] = None


# --- API Endpoints ---

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

@router.post("/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article_data: ArticleCreate,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Create a new knowledge base article as a draft.
    Accessible by admin and SuperAdmin.
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

    new_article = KnowledgeBaseArticle(
        title=article_data.title,
        content_markdown=article_data.content_markdown,
        content_html=content_html,
        summary=article_data.summary,
        category=category,
        tags=tags,
        author=current_user,
        status=ArticleStatus.DRAFT,
        visibility=None  # Visibility set only when published
    )
    await new_article.insert()
    new_article.id = str(new_article.id)

    # Sync to Git repository
    try:
        sync_service = MongoToGitSync()
        author_info = {
            "name": current_user.full_name,
            "email": current_user.email
        }
        await sync_service.sync_article_to_git(str(new_article.id), author_info)
    except Exception as e:
        # Log error but don't fail the request
        print(f"Git sync failed for article {new_article.id}: {str(e)}")

    return ArticleResponse(
        id=str(new_article.id),
        title=new_article.title,
        content_markdown=new_article.content_markdown,
        content_html=new_article.content_html,
        summary=new_article.summary,
        status=new_article.status,
        visibility=new_article.visibility,
        author_id=str(new_article.author.id) if new_article.author else "",
        category=new_article.category,
        tags=new_article.tags,
        version=new_article.version,
        created_at=new_article.created_at,
        updated_at=new_article.updated_at,
        published_at=new_article.published_at
    )

@router.post("/articles/upload", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def upload_kb_file(
    file: UploadFile = File(...),
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Upload a file to create a new knowledge base article as a draft with AI-generated metadata.
    Accessible by SuperAdmin only.
    """
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

    # Extract text content based on file type
    article_content = ""
    article_title = original_filename

    if file_extension == ".txt":
        # For TXT files, read content directly
        try:
            article_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            article_content = "Unable to decode file content"
    elif file_extension == ".pdf":
        article_content = extract_text_from_pdf(file_path)
    elif file_extension in [".docx", ".doc"]:
        article_content = extract_text_from_docx(file_path)
    elif file_extension in [".xlsx", ".xls"]:
        article_content = extract_text_from_excel(file_path)
    elif file_extension == ".csv":
        article_content = extract_text_from_csv(file_path)
    else:
        # For unsupported files, store file path info
        article_content = f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {len(file_content)} bytes\n\nContent extraction not supported for {file_extension} files."

    # Generate AI metadata if content was extracted
    ai_metadata = None
    if article_content and article_content != f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {len(file_content)} bytes\n\nContent extraction not supported for {file_extension} files.":
        try:
            ai_metadata = await generate_metadata_from_ai(article_title, article_content)
        except Exception as e:
            # Continue with default metadata if AI generation fails
            pass

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
        author=current_user,
        status=ArticleStatus.DRAFT,
        visibility=None
    )
    await new_article.insert()
    new_article.id = str(new_article.id)
    
    # Sync to Git repository
    try:
        sync_service = MongoToGitSync()
        author_info = {
            "name": current_user.full_name,
            "email": current_user.email
        }
        await sync_service.sync_article_to_git(str(new_article.id), author_info)
    except Exception as e:
        # Log error but don't fail the request
        print(f"Git sync failed for article {new_article.id}: {str(e)}")

    return ArticleResponse(
        id=str(new_article.id),
        title=new_article.title,
        content_markdown=new_article.content_markdown,
        content_html=new_article.content_html,
        summary=new_article.summary,
        status=new_article.status,
        visibility=new_article.visibility,
        author_id=str(new_article.author.id) if new_article.author else "",
        category=new_article.category,
        tags=new_article.tags,
        version=new_article.version,
        created_at=new_article.created_at,
        updated_at=new_article.updated_at,
        published_at=new_article.published_at
    )

@router.post("/articles/{article_id}/publish", response_model=ArticleResponse)
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
    article.publisher = current_user
    
    await article.save()
    article.id = str(article.id)
    
    # Sync to Git repository
    try:
        sync_service = MongoToGitSync()
        author_info = {
            "name": current_user.full_name,
            "email": current_user.email
        }
        await sync_service.sync_article_to_git(article_id, author_info)
    except Exception as e:
        # Log error but don't fail the request
        print(f"Git sync failed for article {article_id}: {str(e)}")

    return ArticleResponse(
        id=str(article.id),
        title=article.title,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        summary=article.summary,
        status=article.status,
        visibility=article.visibility,
        author_id=str(article.author.id) if article.author else "",
        category=article.category,
        tags=article.tags,
        version=article.version,
        created_at=article.created_at,
        updated_at=article.updated_at,
        published_at=article.published_at
    )

@router.get("/articles", response_model=List[ArticleResponse])
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
        # For Link fields, we need to get the ID from the ref attribute
        author_id = ""
        if article.author:
            # In Beanie Link, the ObjectId is accessible via .ref attribute
            author_id = str(article.author.ref)

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

@router.get("/articles/{article_id}", response_model=ArticleResponse)
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

    return ArticleResponse(
        id=str(article.id),
        title=article.title,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        summary=article.summary,
        status=article.status,
        visibility=article.visibility,
        author_id=str(article.author.id) if article.author else "",
        category=article.category,
        tags=article.tags,
        version=article.version,
        created_at=article.created_at,
        updated_at=article.updated_at,
        published_at=article.published_at
    )

@router.put("/articles/{article_id}", response_model=ArticleResponse)
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

    if current_user.role_name != "SuperAdmin":
        # Check if the current user is the author (using Link comparison)
        if str(article.author.id) != str(current_user.id) or article.status != ArticleStatus.DRAFT:
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
    
    # Handle tags
    tags = await get_or_create_tags(article_data.tag_names)

    article.title = article_data.title
    article.content_markdown = article_data.content_markdown
    article.content_html = content_html
    article.summary = article_data.summary
    article.category = category
    article.tags = tags
    article.updated_at = datetime.utcnow()
    article.version += 1
    
    await article.save()
    
    # Sync to Git repository
    try:
        sync_service = MongoToGitSync()
        author_info = {
            "name": current_user.full_name,
            "email": current_user.email
        }
        await sync_service.sync_article_to_git(article_id, author_info)
    except Exception as e:
        # Log error but don't fail the request
        print(f"Git sync failed for article {article_id}: {str(e)}")

    return ArticleResponse(
        id=str(article.id),
        title=article.title,
        content_markdown=article.content_markdown,
        content_html=article.content_html,
        summary=article.summary,
        status=article.status,
        visibility=article.visibility,
        author_id=str(article.author.id) if article.author else "",
        category=article.category,
        tags=article.tags,
        version=article.version,
        created_at=article.created_at,
        updated_at=article.updated_at,
        published_at=article.published_at
    )

@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.DELETE_ARTICLES))
):
    """
    Delete an article.
    Accessible only by SuperAdmin.
    """
    article = await KnowledgeBaseArticle.get(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    
    await article.delete()
    
    # Sync deletion to Git repository
    try:
        sync_service = MongoToGitSync()
        author_info = {
            "name": current_user.full_name,
            "email": current_user.email
        }
        # For deletion, we need to handle it differently - remove the Markdown file
        # This would require additional logic in the sync service
        # For now, we'll just log that deletion sync is not fully implemented
        print(f"Article {article_id} deleted - Git sync for deletions not yet implemented")
    except Exception as e:
        # Log error but don't fail the request
        print(f"Git sync failed for article deletion {article_id}: {str(e)}")
    
    return None

@router.get("/articles/{article_id}/history", response_model=List[ArticleHistoryItem])
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

@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    current_user: Admin = Depends(get_current_admin)
):
    """
    Get the current synchronization status between MongoDB and Git repository.
    """
    try:
        stats = await get_system_stats()
        
        return SyncStatusResponse(
            status=stats['health']['status'],
            last_sync=stats['last_sync'],
            pending_operations=stats['pending_operations'],
            health_status=stats['health']['status']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching sync status: {str(e)}"
        )

@router.post("/upload-convert", response_model=FileUploadResponse)
async def upload_and_convert_file(
    file: UploadFile = File(...),
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Upload a file and convert it to Markdown format without creating an article.
    Returns the converted content for the editor.
    """
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

    # Extract text content based on file type
    article_content = ""
    article_title = original_filename

    if file_extension == ".txt":
        # For TXT files, read content directly
        try:
            article_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            article_content = "Unable to decode file content"
    elif file_extension == ".pdf":
        article_content = extract_text_from_pdf(file_path)
    elif file_extension in [".docx", ".doc"]:
        article_content = extract_text_from_docx(file_path)
    elif file_extension in [".xlsx", ".xls"]:
        article_content = extract_text_from_excel(file_path)
    elif file_extension == ".csv":
        article_content = extract_text_from_csv(file_path)
    else:
        # For unsupported files, return error
        return FileUploadResponse(
            success=False,
            markdown_content="",
            title="",
            summary="",
            error=f"Unsupported file type: {file_extension}"
        )

    # Generate AI metadata if content was extracted
    ai_metadata = None
    if article_content and article_content != f"File uploaded: {original_filename}\nFile path: {file_path}\nFile size: {len(file_content)} bytes\n\nContent extraction not supported for {file_extension} files.":
        try:
            ai_metadata = await generate_metadata_from_ai(article_title, article_content)
        except Exception as e:
            # Continue with default metadata if AI generation fails
            pass

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
