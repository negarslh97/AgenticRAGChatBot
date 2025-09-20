from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.domain.entities_refactored import KnowledgeBaseArticle, ArticleStatus, Admin, ArticleVisibility, AdminRole
from app.api.dependencies import get_current_admin
from app.core.permissions import get_current_admin_with_permission, Permission

router = APIRouter()

# --- Pydantic Schemas for admin Knowledge Base ---

class ArticleCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tags: List[str] = []

class ArticleUpdate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    category_id: Optional[str] = None
    tags: List[str] = []

class ArticleResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    status: ArticleStatus
    visibility: Optional[ArticleVisibility] = None
    author_id: str
    version: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None

class ArticlePublishRequest(BaseModel):
    visibility: ArticleVisibility


# --- API Endpoints ---

@router.post("/", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article_data: ArticleCreate,
    current_user: Admin = Depends(get_current_admin)
):
    """
    Create a new knowledge base article as a draft.
    Accessible by admin and SuperAdmin.
    """
    new_article = KnowledgeBaseArticle(
        title=article_data.title,
        content=article_data.content,
        summary=article_data.summary,
        category_id=article_data.category_id,
        tags=article_data.tags,
        author_id=str(current_user.id),
        status=ArticleStatus.DRAFT,
        visibility=None  # Visibility set only when published
    )
    await new_article.insert()
    new_article.id = str(new_article.id)
    return new_article

@router.post("/upload", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def upload_kb_file(
    file: UploadFile = File(...),
    current_user: Admin = Depends(get_current_admin_with_permission(Permission.MANAGE_KB_ARTICLES))
):
    """
    Upload a file to create a new knowledge base article as a draft.
    Accessible by SuperAdmin only.
    """
    # Create uploads directory if it doesn't exist
    upload_dir = Path("sally-backend/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file to uploads directory
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Create article with filename as title
    new_article = KnowledgeBaseArticle(
        title=file.filename,
        content=f"Uploaded file: {file.filename}",
        author_id=str(current_user.id),
        status=ArticleStatus.DRAFT,
        visibility=None
    )
    await new_article.insert()
    new_article.id = str(new_article.id)
    return new_article

@router.post("/{article_id}/publish", response_model=ArticleResponse)
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
    article.published_by = str(current_user.id)
    
    await article.save()
    article.id = str(article.id)
    return article

@router.get("/", response_model=List[ArticleResponse])
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
    # Convert ObjectId to string for response
    for article in articles:
        article.id = str(article.id)
    return articles

@router.get("/{article_id}", response_model=ArticleResponse)
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
    article.id = str(article.id)
    return article

@router.put("/{article_id}", response_model=ArticleResponse)
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
        if article.author_id != str(current_user.id) or article.status != ArticleStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own draft articles."
            )

    article.title = article_data.title
    article.content = article_data.content
    article.summary = article_data.summary
    article.category_id = article_data.category_id
    article.tags = article_data.tags
    article.updated_at = datetime.utcnow()
    article.version += 1
    
    await article.save()
    return article

@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
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
    return None
